"""
AgriSaathi AI — Dedicated Ollama LLM Service Provider
=====================================================
Provider-independent, resilient Ollama service supporting local LLM inference
with strict timeouts, latency tracking, health probe, and honest error states.
"""

import os
import time
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("agrisaathi.ollama")

# Configuration via environment variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

class OllamaModelInfo(BaseModel):
    name: str
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None
    status: str = "AVAILABLE" # AVAILABLE | UNAVAILABLE | DEGRADED

class OllamaServiceStatus(BaseModel):
    status: str # AVAILABLE | UNAVAILABLE | DEGRADED | EXPERIMENTAL
    base_url: str
    active_model: str
    available_models: List[str]
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

class OllamaInferenceResponse(BaseModel):
    text: str
    model_name: str
    status: str # AVAILABLE | UNAVAILABLE | DEGRADED
    generation_time_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_error: Optional[str] = None

class OllamaService:
    """Encapsulates all communication with local Ollama daemon."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        default_model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT_SECONDS
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def check_health(self) -> OllamaServiceStatus:
        """Probes the Ollama daemon and checks whether active model is pulled."""
        start_t = time.perf_counter()
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name") for m in payload.get("models", []) if "name" in m]
                    latency = round((time.perf_counter() - start_t) * 1000, 2)
                    
                    has_active = any(self.default_model in m for m in models)
                    status = "AVAILABLE" if has_active else ("DEGRADED" if models else "UNAVAILABLE")
                    
                    return OllamaServiceStatus(
                        status=status,
                        base_url=self.base_url,
                        active_model=self.default_model,
                        available_models=models,
                        latency_ms=latency,
                        error_message=None if has_active else f"Model '{self.default_model}' not found in installed models: {models}"
                    )
                else:
                    return OllamaServiceStatus(
                        status="DEGRADED",
                        base_url=self.base_url,
                        active_model=self.default_model,
                        available_models=[],
                        error_message=f"HTTP {response.status}"
                    )
        except Exception as e:
            logger.warning(f"Ollama health probe failed: {e}")
            return OllamaServiceStatus(
                status="UNAVAILABLE",
                base_url=self.base_url,
                active_model=self.default_model,
                available_models=[],
                latency_ms=None,
                error_message=str(e)
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 1024
    ) -> OllamaInferenceResponse:
        """Executes prompt generation with strict timeout, metrics logging, and error safety."""
        target_model = model or self.default_model
        start_t = time.perf_counter()
        
        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        url = f"{self.base_url}/api/generate"
        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
                if res.status == 200:
                    resp_obj = json.loads(res.read().decode("utf-8"))
                    text = resp_obj.get("response", "").strip()
                    logger.info(f"Ollama generation succeeded in {elapsed_ms} ms using {target_model}")
                    return OllamaInferenceResponse(
                        text=text,
                        model_name=target_model,
                        status="AVAILABLE",
                        generation_time_ms=elapsed_ms,
                        prompt_tokens=resp_obj.get("prompt_eval_count"),
                        completion_tokens=resp_obj.get("eval_count")
                    )
                else:
                    return OllamaInferenceResponse(
                        text="",
                        model_name=target_model,
                        status="DEGRADED",
                        generation_time_ms=elapsed_ms,
                        raw_error=f"HTTP status {res.status}"
                    )
        except urllib.error.URLError as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            logger.error(f"Ollama connection error: {e}")
            return OllamaInferenceResponse(
                text="",
                model_name=target_model,
                status="UNAVAILABLE",
                generation_time_ms=elapsed_ms,
                raw_error=f"URLError: {e.reason if hasattr(e, 'reason') else str(e)}"
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            logger.error(f"Ollama generation unexpected error: {e}")
            return OllamaInferenceResponse(
                text="",
                model_name=target_model,
                status="UNAVAILABLE",
                generation_time_ms=elapsed_ms,
                raw_error=str(e)
            )

# Singleton service instance
ollama_service = OllamaService()
