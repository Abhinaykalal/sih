"""
AgriSaathi AI — Hybrid LLM Provider
====================================
Implements a unified provider interface supporting:
  - OLLAMA   : local Ollama (qwen2.5:7b-instruct) — used in development
  - GROQ     : cloud Groq API (llama-3.1-8b-instant) — used on Render
  - RAG_ONLY : no LLM synthesis; return raw RAG excerpts with citations
  - UNAVAILABLE : all providers failed

Selection priority (auto-detected at startup):
  1. Ollama if running locally and OLLAMA_BASE_URL reachable
  2. Groq if GROQ_API_KEY env var is set
  3. RAG_ONLY (honest fallback)

Security:
  - API keys are NEVER returned in API responses
  - API keys are NEVER logged
  - All keys loaded exclusively from environment variables
"""

import os
import time
import uuid
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("agrisaathi.llm_provider")


class LLMProviderName(str, Enum):
    OLLAMA = "OLLAMA"
    GROQ = "GROQ"
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"
    RAG_ONLY = "RAG_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class LLMProviderStatus:
    provider: str
    model_name: str
    status: str          # AVAILABLE | UNAVAILABLE | RAG_ONLY
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class LLMInferenceResponse:
    answer: str
    provider: str
    model_name: str
    status: str                         # AVAILABLE | UNAVAILABLE | RAG_ONLY
    provenance: str                     # SOURCE_BACKED_KNOWLEDGE | RAG_ONLY | UNAVAILABLE
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    latency_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    warnings: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ollama sub-provider (reuses existing OllamaService if available)
# ---------------------------------------------------------------------------

def _try_ollama(prompt: str, system: str, timeout: int = 60) -> Optional[LLMInferenceResponse]:
    """Call local Ollama. Returns None on any failure."""
    try:
        import httpx
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        t0 = time.time()
        resp = httpx.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": f"{system}\n\n{prompt}", "stream": False},
            timeout=timeout,
        )
        latency = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("response", "").strip()
            if answer:
                return LLMInferenceResponse(
                    answer=answer,
                    provider=LLMProviderName.OLLAMA,
                    model_name=model,
                    status="AVAILABLE",
                    provenance="SOURCE_BACKED_KNOWLEDGE",
                    latency_ms=round(latency, 1),
                    prompt_tokens=data.get("prompt_eval_count"),
                    completion_tokens=data.get("eval_count"),
                )
    except Exception as e:
        logger.debug(f"Ollama unavailable: {e}")
    return None


def _check_ollama_health() -> bool:
    """Quick Ollama health check — does NOT log the model list."""
    try:
        import httpx
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        r = httpx.get(f"{base_url}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Groq sub-provider
# ---------------------------------------------------------------------------

def _try_groq(prompt: str, system: str, timeout: int = 30) -> Optional[LLMInferenceResponse]:
    """Call Groq Cloud API. Returns None if key not set or call fails."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return None
    try:
        import httpx
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        t0 = time.time()
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 512,
                "temperature": 0.2,
            },
            timeout=timeout,
        )
        latency = (time.time() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            if answer:
                return LLMInferenceResponse(
                    answer=answer,
                    provider=LLMProviderName.GROQ,
                    model_name=model,
                    status="AVAILABLE",
                    provenance="SOURCE_BACKED_KNOWLEDGE",
                    latency_ms=round(latency, 1),
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                )
        else:
            logger.warning(f"Groq API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Groq call failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Unified Hybrid Provider
# ---------------------------------------------------------------------------

class HybridLLMProvider:
    """
    Auto-selects LLM provider based on environment:
      - Ollama first (if health check passes)
      - Groq second (if GROQ_API_KEY set)
      - RAG_ONLY honest fallback
    """

    def __init__(self):
        self._active_provider: Optional[str] = None
        self._model_name: str = "none"
        self._last_health_check: float = 0
        self._health_cache_ttl: float = 30  # seconds

    def _detect_provider(self) -> str:
        now = time.time()
        if now - self._last_health_check < self._health_cache_ttl and self._active_provider:
            return self._active_provider

        self._last_health_check = now

        # Priority 1: local Ollama
        if _check_ollama_health():
            self._active_provider = LLMProviderName.OLLAMA
            self._model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
            return LLMProviderName.OLLAMA

        # Priority 2: Groq cloud
        if os.getenv("GROQ_API_KEY", ""):
            self._active_provider = LLMProviderName.GROQ
            self._model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            return LLMProviderName.GROQ

        # Priority 3: RAG_ONLY
        self._active_provider = LLMProviderName.RAG_ONLY
        self._model_name = "rag-only"
        return LLMProviderName.RAG_ONLY

    def get_status(self) -> LLMProviderStatus:
        provider = self._detect_provider()
        return LLMProviderStatus(
            provider=provider,
            model_name=self._model_name,
            status="AVAILABLE" if provider not in (LLMProviderName.RAG_ONLY, LLMProviderName.UNAVAILABLE) else provider,
        )

    def generate(
        self,
        prompt: str,
        system: str = "You are an expert agricultural advisor. Answer concisely and accurately.",
        rag_excerpt: str = "",
        timeout: int = 60,
    ) -> LLMInferenceResponse:
        """
        Generate a response. If no LLM is available, returns honest RAG_ONLY response.
        The API key is NEVER included in the response object.
        """
        provider = self._detect_provider()
        req_id = str(uuid.uuid4())[:12]

        if provider == LLMProviderName.OLLAMA:
            result = _try_ollama(prompt, system, timeout)
            if result:
                result.request_id = req_id
                return result
            # Ollama failed mid-request — try Groq
            logger.warning("Ollama failed during generate, attempting Groq fallback")
            if os.getenv("GROQ_API_KEY", ""):
                result = _try_groq(prompt, system, timeout=30)
                if result:
                    result.request_id = req_id
                    result.warnings.append("Ollama failed; fell back to Groq cloud provider.")
                    return result

        elif provider == LLMProviderName.GROQ:
            result = _try_groq(prompt, system, timeout=30)
            if result:
                result.request_id = req_id
                return result
            logger.warning("Groq failed during generate")

        # All LLMs unavailable — honest RAG_ONLY fallback
        fallback_text = (
            rag_excerpt
            if rag_excerpt
            else "No source-backed excerpts available for this query."
        )
        label = "LLM synthesis unavailable — showing source-backed excerpts."
        return LLMInferenceResponse(
            answer=f"{label}\n\n{fallback_text}",
            provider=LLMProviderName.RAG_ONLY,
            model_name="rag-only",
            status="RAG_ONLY",
            provenance="RAG_ONLY",
            request_id=req_id,
            warnings=[
                "No LLM provider is available (Ollama offline, no GROQ_API_KEY configured).",
                "Displaying raw RAG source excerpts with full citations.",
            ],
        )


# Module-level singleton
hybrid_provider = HybridLLMProvider()
