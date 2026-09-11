"""
AgriSaathi AI — Dedicated Ollama LLM Service Provider
=====================================================
Clean, production-grade Ollama API integration layer with:
- Connection & model reachability probes
- Model existence validation
- Structured error handling & codes (OLLAMA_UNREACHABLE, MODEL_NOT_FOUND, MODEL_TIMEOUT, etc.)
- Strict timeouts and latency tracking
- Zero hardcoded fallback / mock outputs
- RAG compatibility interface (generate_response with context)
"""

import os
import time
import json
import logging
import urllib.request
import urllib.error
import socket
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("agrisaathi.ollama")


class OllamaErrorCode:
    OLLAMA_UNREACHABLE = "OLLAMA_UNREACHABLE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_GENERATION_FAILED = "MODEL_GENERATION_FAILED"
    AI_CONFIGURATION_MISSING = "AI_CONFIGURATION_MISSING"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_REQUEST = "INVALID_REQUEST"


class OllamaServiceException(Exception):
    """Structured exception representing an Ollama communication or generation error."""
    def __init__(self, error_code: str, message: str, status_code: int = 503, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class OllamaModelInfo(BaseModel):
    name: str
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None
    status: str = "AVAILABLE"


class OllamaServiceStatus(BaseModel):
    status: str  # HEALTHY | MODEL_UNAVAILABLE | OLLAMA_UNREACHABLE
    provider: str = "ollama"
    model: str
    ollama_reachable: bool
    model_available: bool
    available_models: List[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None


class OllamaInferenceResponse(BaseModel):
    text: str
    model_name: str
    provider: str = "ollama"
    status: str  # GENERATED | UNAVAILABLE | DEGRADED
    generation_time_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_error: Optional[str] = None
    error_code: Optional[str] = None


class OllamaService:
    """Encapsulates all direct communication with the local or remote Ollama daemon."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self._custom_base_url = base_url
        self._custom_default_model = default_model
        self._custom_timeout = timeout

    @property
    def base_url(self) -> str:
        url = self._custom_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return url.rstrip("/")

    @property
    def default_model(self) -> str:
        return self._custom_default_model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

    @property
    def timeout(self) -> int:
        if self._custom_timeout is not None:
            return self._custom_timeout
        try:
            return int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
        except (ValueError, TypeError):
            return 60

    def check_health(self) -> OllamaServiceStatus:
        """
        Probes the Ollama daemon:
        1. Tests connection reachability.
        2. Retrieves installed models list from /api/tags.
        3. Verifies if configured model is present.
        """
        start_t = time.perf_counter()
        url = f"{self.base_url}/api/tags"
        target_model = self.default_model

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                latency = round((time.perf_counter() - start_t) * 1000, 2)
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    models = [
                        m.get("name") for m in payload.get("models", [])
                        if isinstance(m, dict) and "name" in m
                    ]
                    # Check if target_model is an exact match or tag match
                    has_model = any(
                        target_model == m or target_model == m.split(":")[0] or m.startswith(f"{target_model}:")
                        for m in models
                    )
                    
                    status = "HEALTHY" if has_model else "MODEL_UNAVAILABLE"
                    error_msg = None if has_model else f"Model '{target_model}' not found in Ollama models list: {models}"

                    logger.info(
                        "Ollama health check completed",
                        extra={
                            "ollama_reachable": True,
                            "model_available": has_model,
                            "model": target_model,
                            "latency_ms": latency
                        }
                    )

                    return OllamaServiceStatus(
                        status=status,
                        provider="ollama",
                        model=target_model,
                        ollama_reachable=True,
                        model_available=has_model,
                        available_models=models,
                        latency_ms=latency,
                        error_message=error_msg
                    )
                else:
                    return OllamaServiceStatus(
                        status="MODEL_UNAVAILABLE",
                        provider="ollama",
                        model=target_model,
                        ollama_reachable=True,
                        model_available=False,
                        available_models=[],
                        latency_ms=latency,
                        error_message=f"HTTP {response.status} from Ollama tags endpoint"
                    )
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            latency = round((time.perf_counter() - start_t) * 1000, 2)
            err_reason = str(e.reason) if hasattr(e, "reason") else str(e)
            logger.warning(f"Ollama unreachable at {self.base_url}: {err_reason}")
            return OllamaServiceStatus(
                status="MODEL_UNAVAILABLE",
                provider="ollama",
                model=target_model,
                ollama_reachable=False,
                model_available=False,
                available_models=[],
                latency_ms=latency,
                error_message=f"Ollama unreachable: {err_reason}"
            )
        except Exception as e:
            latency = round((time.perf_counter() - start_t) * 1000, 2)
            logger.error(f"Unexpected error probing Ollama: {e}")
            return OllamaServiceStatus(
                status="MODEL_UNAVAILABLE",
                provider="ollama",
                model=target_model,
                ollama_reachable=False,
                model_available=False,
                available_models=[],
                latency_ms=latency,
                error_message=str(e)
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 1024,
        raise_on_error: bool = False
    ) -> OllamaInferenceResponse:
        """
        Executes prompt generation via Ollama /api/generate.
        Handles timeout, network errors, and model missing states truthfully without fake outputs.
        """
        target_model = model or self.default_model
        if not target_model:
            if raise_on_error:
                raise OllamaServiceException(
                    error_code=OllamaErrorCode.AI_CONFIGURATION_MISSING,
                    message="No Ollama model configured.",
                    status_code=500
                )
            return OllamaInferenceResponse(
                text="",
                model_name="N/A",
                status="UNAVAILABLE",
                generation_time_ms=0.0,
                raw_error="No Ollama model configured.",
                error_code=OllamaErrorCode.AI_CONFIGURATION_MISSING
            )

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
                    logger.info(
                        f"Ollama generation succeeded with {target_model}",
                        extra={
                            "model": target_model,
                            "latency_ms": elapsed_ms,
                            "prompt_tokens": resp_obj.get("prompt_eval_count"),
                            "completion_tokens": resp_obj.get("eval_count")
                        }
                    )
                    return OllamaInferenceResponse(
                        text=text,
                        model_name=target_model,
                        provider="ollama",
                        status="GENERATED",
                        generation_time_ms=elapsed_ms,
                        prompt_tokens=resp_obj.get("prompt_eval_count"),
                        completion_tokens=resp_obj.get("eval_count")
                    )
                else:
                    err_msg = f"Ollama returned HTTP status {res.status}"
                    if raise_on_error:
                        raise OllamaServiceException(
                            error_code=OllamaErrorCode.MODEL_GENERATION_FAILED,
                            message=err_msg,
                            status_code=502
                        )
                    return OllamaInferenceResponse(
                        text="",
                        model_name=target_model,
                        status="UNAVAILABLE",
                        generation_time_ms=elapsed_ms,
                        raw_error=err_msg,
                        error_code=OllamaErrorCode.MODEL_GENERATION_FAILED
                    )
        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            
            # Ollama returns 404 when model is not pulled
            if e.code == 404 or "model" in error_body.lower() and "not found" in error_body.lower():
                code = OllamaErrorCode.MODEL_NOT_FOUND
                msg = f"Model '{target_model}' not found in Ollama runtime."
                status_code = 404
            else:
                code = OllamaErrorCode.MODEL_GENERATION_FAILED
                msg = f"Ollama HTTP error {e.code}: {error_body or e.reason}"
                status_code = 502

            logger.error(f"Ollama HTTP error ({code}): {msg}")
            if raise_on_error:
                raise OllamaServiceException(
                    error_code=code,
                    message=msg,
                    status_code=status_code,
                    details={"http_code": e.code, "error_body": error_body}
                )
            return OllamaInferenceResponse(
                text="",
                model_name=target_model,
                status="UNAVAILABLE",
                generation_time_ms=elapsed_ms,
                raw_error=msg,
                error_code=code
            )
        except (socket.timeout, TimeoutError) as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            msg = f"Ollama generation timed out after {self.timeout}s."
            logger.error(f"Ollama generation timeout: {msg}")
            if raise_on_error:
                raise OllamaServiceException(
                    error_code=OllamaErrorCode.MODEL_TIMEOUT,
                    message=msg,
                    status_code=504
                )
            return OllamaInferenceResponse(
                text="",
                model_name=target_model,
                status="UNAVAILABLE",
                generation_time_ms=elapsed_ms,
                raw_error=msg,
                error_code=OllamaErrorCode.MODEL_TIMEOUT
            )
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            err_reason = str(e.reason) if hasattr(e, "reason") else str(e)
            # Check if this URLError wraps a timeout
            if "timed out" in err_reason.lower():
                code = OllamaErrorCode.MODEL_TIMEOUT
                msg = f"Ollama request timed out after {self.timeout}s."
                status_code = 504
            else:
                code = OllamaErrorCode.OLLAMA_UNREACHABLE
                msg = f"Cannot reach Ollama at {self.base_url}: {err_reason}"
                status_code = 503

            logger.error(f"Ollama connection failure: {msg}")
            if raise_on_error:
                raise OllamaServiceException(
                    error_code=code,
                    message=msg,
                    status_code=status_code
                )
            return OllamaInferenceResponse(
                text="",
                model_name=target_model,
                status="UNAVAILABLE",
                generation_time_ms=elapsed_ms,
                raw_error=msg,
                error_code=code
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            msg = f"Unexpected generation error: {str(e)}"
            logger.error(f"Ollama unexpected error: {msg}")
            if raise_on_error:
                raise OllamaServiceException(
                    error_code=OllamaErrorCode.MODEL_GENERATION_FAILED,
                    message=msg,
                    status_code=500
                )
            return OllamaInferenceResponse(
                text="",
                model_name=target_model,
                status="UNAVAILABLE",
                generation_time_ms=elapsed_ms,
                raw_error=msg,
                error_code=OllamaErrorCode.MODEL_GENERATION_FAILED
            )

    def generate_response(
        self,
        user_message: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 1024,
        raise_on_error: bool = True
    ) -> OllamaInferenceResponse:
        """
        Clean interface for downstream applications & RAG integration.
        Combines retrieved verified context with user query into a clean prompt.
        """
        system = system_prompt or (
            "You are AgriSaathi AI, an expert agricultural advisor. "
            "Provide concise, practical, factual farming guidance. "
            "Base your response strictly on any verified context provided."
        )

        prompt_parts = []
        if context and context.strip():
            prompt_parts.append(f"Verified Agricultural Context:\n{context.strip()}\n")
        prompt_parts.append(f"Farmer Query: {user_message.strip()}\n\nAdvisory Response:")

        full_prompt = "\n".join(prompt_parts)

        return self.generate(
            prompt=full_prompt,
            system_prompt=system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            raise_on_error=raise_on_error
        )


# Global singleton instance
ollama_service = OllamaService()
