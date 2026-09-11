"""
AgriSaathi AI — Ollama FastAPI API Integration Test Suite
=========================================================
Covers all 10 required test specifications:
1. Ollama reachable (health probe returns true)
2. Ollama unreachable (returns MODEL_UNAVAILABLE / OLLAMA_UNREACHABLE)
3. Model available (tags match configured model)
4. Model unavailable (tags list misses configured model)
5. Successful generation (Ollama /api/generate returns real tokens & response)
6. Timeout handling (socket/HTTP timeout triggers 504 MODEL_TIMEOUT)
7. Invalid request handling (empty message/question triggers 400 INVALID_REQUEST)
8. Authentication failure handling (JWT enforcement triggers 401 UNAUTHORIZED)
9. No hardcoded response (verifies dynamic LLM output is preserved unmodified)
10. API response schema validation (/api/ai/health and /api/ai/chat)
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import urllib.error
import socket

from fastapi.testclient import TestClient
from mlbackend.main import app, settings
from mlbackend.ollama_service import OllamaService, OllamaErrorCode, OllamaServiceException


class MockHttpResponse:
    def __init__(self, data: dict, status: int = 200):
        self._raw = json.dumps(data).encode("utf-8")
        self.status = status

    def read(self):
        return self._raw

    def decode(self, encoding="utf-8"):
        return self._raw.decode(encoding)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestOllamaFastAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        settings.ENFORCE_JWT_AUTH = False

    # ------------------------------------------------------------------------
    # Test 1: Ollama Reachable
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_01_ollama_reachable(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse({
            "models": [{"name": "qwen2.5:7b-instruct:latest"}]
        })
        resp = self.client.get("/api/ai/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ollama_reachable"])
        self.assertTrue(data["model_available"])
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["provider"], "ollama")

    # ------------------------------------------------------------------------
    # Test 2: Ollama Unreachable
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_02_ollama_unreachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason="Connection refused")
        resp = self.client.get("/api/ai/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ollama_reachable"])
        self.assertFalse(data["model_available"])
        self.assertEqual(data["status"], "MODEL_UNAVAILABLE")

    # ------------------------------------------------------------------------
    # Test 3: Model Available
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_03_model_available(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse({
            "models": [
                {"name": "qwen2.5:7b-instruct"},
                {"name": "llama3:latest"}
            ]
        })
        resp = self.client.get("/api/ai/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["model_available"])
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["model"], os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"))

    # ------------------------------------------------------------------------
    # Test 4: Model Unavailable
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_04_model_unavailable(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse({
            "models": [
                {"name": "mistral:7b"},
                {"name": "phi3:latest"}
            ]
        })
        resp = self.client.get("/api/ai/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ollama_reachable"])
        self.assertFalse(data["model_available"])
        self.assertEqual(data["status"], "MODEL_UNAVAILABLE")

    # ------------------------------------------------------------------------
    # Test 5: Successful Generation
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_05_successful_generation(self, mock_urlopen):
        expected_text = "To improve soil health in paddy cultivation, implement Alternate Wetting and Drying (AWD) and add organic green manure."
        mock_urlopen.return_value = MockHttpResponse({
            "response": expected_text,
            "prompt_eval_count": 42,
            "eval_count": 128
        })
        resp = self.client.post("/api/ai/chat", json={
            "message": "How can I improve soil health?"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["response"], expected_text)
        self.assertEqual(data["status"], "GENERATED")
        self.assertEqual(data["provider"], "ollama")
        self.assertIn("latency_ms", data)
        self.assertEqual(data["prompt_tokens"], 42)
        self.assertEqual(data["completion_tokens"], 128)

    # ------------------------------------------------------------------------
    # Test 6: Timeout Handling
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_06_timeout_handling(self, mock_urlopen):
        mock_urlopen.side_effect = socket.timeout("timed out")
        resp = self.client.post("/api/ai/chat", json={
            "message": "What is the optimal fertilizer dosage for cotton?"
        })
        self.assertEqual(resp.status_code, 504)
        data = resp.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"]["error_code"], "MODEL_TIMEOUT")

    # ------------------------------------------------------------------------
    # Test 7: Invalid Request (Empty Query)
    # ------------------------------------------------------------------------
    def test_07_invalid_request_empty(self):
        resp = self.client.post("/api/ai/chat", json={
            "message": "   "
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["detail"]["error_code"], "INVALID_REQUEST")

    # ------------------------------------------------------------------------
    # Test 8: Authentication Failure
    # ------------------------------------------------------------------------
    def test_08_authentication_failure(self):
        settings.ENFORCE_JWT_AUTH = True
        try:
            resp = self.client.post("/api/ai/chat", json={
                "message": "Explain drip irrigation advantages."
            })
            self.assertEqual(resp.status_code, 401)
            data = resp.json()
            self.assertIn("detail", data)
            self.assertEqual(data["detail"]["error_code"], "UNAUTHORIZED")
        finally:
            settings.ENFORCE_JWT_AUTH = False

    # ------------------------------------------------------------------------
    # Test 9: No Hardcoded Response (Dynamic Model Output Verification)
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_09_no_hardcoded_response(self, mock_urlopen):
        dynamic_answers = [
            "Dynamic response 1: Verified nitrogen recommendation for wheat.",
            "Dynamic response 2: Phosphorous management for soybean crops.",
            "Dynamic response 3: Potassium application during flowering stage."
        ]
        for query_idx, expected_answer in enumerate(dynamic_answers):
            mock_urlopen.return_value = MockHttpResponse({
                "response": expected_answer,
                "prompt_eval_count": 10 * (query_idx + 1),
                "eval_count": 25 * (query_idx + 1)
            })
            resp = self.client.post("/api/ai/chat", json={
                "message": f"Query variation {query_idx}"
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            # Assert exact dynamic return from Ollama, zero hardcoded fallback substitution
            self.assertEqual(data["response"], expected_answer)
            self.assertNotIn("sample answer", data["response"].lower())
            self.assertNotIn("simulated", data["response"].lower())

    # ------------------------------------------------------------------------
    # Test 10: API Response Schema Validation
    # ------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_10_api_response_schema(self, mock_urlopen):
        # 10a. Health Schema
        mock_urlopen.return_value = MockHttpResponse({
            "models": [{"name": "qwen2.5:7b-instruct"}]
        })
        health_resp = self.client.get("/api/ai/health")
        self.assertEqual(health_resp.status_code, 200)
        h_json = health_resp.json()
        for field_name in ["status", "provider", "model", "ollama_reachable", "model_available"]:
            self.assertIn(field_name, h_json, f"Missing field '{field_name}' in /api/ai/health schema")

        # 10b. Chat Schema
        mock_urlopen.return_value = MockHttpResponse({
            "response": "Schema validation dynamic response.",
            "prompt_eval_count": 15,
            "eval_count": 30
        })
        chat_resp = self.client.post("/api/ai/chat", json={
            "message": "Verify response schema completeness."
        })
        self.assertEqual(chat_resp.status_code, 200)
        c_json = chat_resp.json()
        for field_name in ["response", "model", "provider", "status", "request_id", "generated_at"]:
            self.assertIn(field_name, c_json, f"Missing field '{field_name}' in /api/ai/chat schema")
        self.assertEqual(c_json["provider"], "ollama")
        self.assertEqual(c_json["status"], "GENERATED")


if __name__ == "__main__":
    unittest.main()
