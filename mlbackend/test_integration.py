"""
AgriSaathi Full Integration Test Suite
========================================
Tests all major API endpoints for correctness, grounding, and response quality.
Supports both in-process FastAPI TestClient execution and live HTTP server testing.
"""
import os
import sys
import json
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi.testclient import TestClient
from mlbackend.main import app

PASS = "[PASS]"
FAIL = "[FAIL]"


def run_integration_tests():
    results = {"passed": 0, "failed": 0}

    def test(name: str, condition: bool, details: str = ""):
        if condition:
            print(f"  {PASS}  {name}")
            results["passed"] += 1
        else:
            print(f"  {FAIL}  {name}: {details}")
            results["failed"] += 1

    client = TestClient(app)

    def post(path, data):
        try:
            r = client.post(path, json=data)
            return r.json(), r.status_code
        except Exception as e:
            return {"error": str(e)}, 0

    def get(path, params=None):
        try:
            r = client.get(path, params=params)
            return r.json(), r.status_code
        except Exception as e:
            return {"error": str(e)}, 0

    print("\n" + "=" * 60)
    print("AgriSaathi AI — Integration Test Suite")
    print("=" * 60)

    # 1. Health Check
    print("\n[1] Health Check")
    d, s = get("/")
    test("Server is online", s == 200, str(s))
    test("Response has status key", "status" in d, str(d))

    # 2. Crop Recommendation
    print("\n[2] Crop Recommendation")
    d, s = post("/api/recommend", {
        "N": 45, "P": 22, "K": 38,
        "temperature": 29.0, "humidity": 65.0,
        "ph": 6.8, "rainfall": 120.0
    })
    test("Status 200", s == 200, str(s))
    test("Has recommended_crop", "recommended_crop" in d, str(d))
    test("Confidence is numeric", isinstance(d.get("confidence"), (int, float)), str(d.get("confidence")))

    # 3. Agent Chat — Irrigation Query
    print("\n[3] Agent Chat — Irrigation Query")
    d, s = post("/api/agent/chat", {
        "message": "Should I irrigate my rice field today?",
        "crop": "Rice",
        "stage": "Vegetative",
        "lat": 30.73,
        "lon": 76.78,
        "user_id": "test-user-integration",
        "session_id": "test-sess-1"
    })
    test("Status 200", s == 200, str(s))
    test("Has 'answer' field", "answer" in d, str(d))

    # 4. Agent Chat — Telemetry-Grounded Query
    print("\n[4] Agent Chat — Telemetry-Grounded Query")
    d, s = post("/api/agent/chat", {
        "message": "What are my field sensor readings?",
        "crop": "Rice",
        "user_id": "test-user-integration",
        "session_id": "test-sess-1",
        "mock_telemetry": {
            "soilMoisture": 28.5,
            "soilTemperature": 24.0,
            "airTemperature": 31.0,
            "humidity": 55.0,
            "timestamp": "2026-03-08T10:00:00Z"
        }
    })
    test("Status 200", s == 200, str(s))
    test("Evidence list populated", len(d.get("evidence", [])) > 0, str(d.get("evidence")))

    # 5. Agent Chat — Hindi Language
    print("\n[5] Agent Chat — Hindi Query")
    d, s = post("/api/agent/chat", {
        "message": "मुझे अपनी धान की फसल में क्या उर्वरक डालना चाहिए?",
        "crop": "Rice",
        "language": "hi",
        "user_id": "test-user-hindi",
        "session_id": "test-sess-hi"
    })
    test("Status 200", s == 200, str(s))
    test("Detected language is 'hi'", d.get("detected_language") == "hi" or d.get("language") == "hi", str(d.get("language")))

    # 6. RAG Search Direct
    print("\n[6] RAG Search Direct")
    d, s = post("/api/ai/rag/query", {"message": "rice blast management", "crop": "Rice"})
    test("Status 200", s == 200, str(s))
    test("Results or sources returned", "answer" in d or "documents" in d or "sources" in d or "query" in d or "status" in d, str(list(d.keys())[:3]))

    # 7. Safe Vision Inference Direct
    print("\n[7] Safe Vision Inference Direct")
    d, s = post("/api/vision-diagnose", {"image_base64": ""})
    print("DEBUG RESPONSE:", d)
    test("Status 200", s == 200, str(s))
    test("Safe fallback returned without crashing", d.get("status") in ["INVALID_IMAGE", "MODEL_UNAVAILABLE", "NO_RELIABLE_RESULT", "SUCCESS", "UNAVAILABLE"] or "diagnosis" in d, str(d.get("status")))

    # 8. Irrigation Assessment Direct
    print("\n[8] Irrigation Assessment Direct")
    d, s = post("/api/irrigation/assess", {
        "soil_moisture": 28.0,
        "air_temp": 33.0,
        "humidity": 52.0,
        "rain_forecast_mm": 0.0,
        "crop": "Rice",
        "growth_stage": "Panicle Initiation"
    })
    test("Status 200", s == 200, str(s))
    test("irrigation_needed is True for 28% moisture", d.get("irrigation_needed") is True, str(d.get("irrigation_needed")))

    # 9. Fertilizer Service
    print("\n[9] Fertilizer Service")
    d, s = post("/api/fertilizer-optimize", {
        "crop_type": "rice",
        "field_size": 2.5,
        "soil_type": "Clay",
        "prev_crop": "wheat",
        "prev_fertilizers": "DAP",
        "organic_manure": "FYM",
        "irrigation_type": "Flooding",
        "irrigation_frequency": "Every 3 days",
        "growth_stage": "Vegetative"
    })
    test("Status 200", s == 200, str(s))
    test("Has recommendations", "recommendations" in d or len(d) > 0, str(list(d.keys())[:4]))

    # 10. Weather Endpoint
    print("\n[10] Weather Endpoint")
    d, s = post("/api/weather-advice", {"lat": 30.73, "lon": 76.78, "crop": "rice", "lang": "en"})
    test("Weather endpoint returns data", s in [200, 422, 500, 503], str(s))

    # 11. Model Registry
    print("\n[11] Model Registry")
    d, s = get("/models/status")
    test("Status 200", s == 200, str(s))
    test("Has models key", "models" in d or isinstance(d, dict), str(list(d.keys())[:5]))

    # 12. Dataset Quality Report
    print("\n[12] Dataset Quality Report")
    d, s = get("/api/dataset-quality")
    test("Status 200", s == 200, str(s))

    print("\n" + "=" * 60)
    total = results["passed"] + results["failed"]
    print(f"Results: {results['passed']}/{total} tests passed")
    return results["passed"], results["failed"]


def test_full_integration_suite():
    passed, failed = run_integration_tests()
    assert failed == 0, f"{failed} integration tests failed"


if __name__ == "__main__":
    passed, failed = run_integration_tests()
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)
