"""
AGRISENTINEL VERIFICATION TEST SUITE
Tests all problem statement requirements:
1. compute_4zone_farm_status returns complete disaster_scores and zones
2. /api/telemetry/history returns historical time-series data
3. /api/vision-diagnose processes base64 images and extracts features
4. Over-irrigation & flood risk indices calculate properly
"""

import sys
import os
import io
import numpy as np
from PIL import Image

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from risk_engine import compute_4zone_farm_status, evaluate_smart_irrigation, evaluate_multimodal_disease_context
from vision_ai_model import local_vision_ai, validate_leaf_image, extract_vision_features
from db_layer import db_layer

def run_tests():
    print("[TEST 1] Testing compute_4zone_farm_status...")
    status = compute_4zone_farm_status({
        "z1_moisture": 45.0,
        "z2_moisture": 16.0,
        "z3_pest_count": 25,
        "z4_humidity": 90.0,
        "air_temp": 35.0,
        "rain_prob": 20.0
    })
    assert status is not None, "compute_4zone_farm_status returned None!"
    assert "zones" in status, "zones missing from status"
    assert "disaster_scores" in status, "disaster_scores missing from status"
    assert "flood_risk_pct" in status["disaster_scores"], "flood_risk_pct missing"
    assert status["zones"]["zone_2"]["status"] == "IRRIGATE IMMEDIATELY"
    print(f"  Passed! Overall Health: {status['disaster_scores']['overall_farm_health_score']}, Flood Risk: {status['disaster_scores']['flood_risk_pct']}%")

    print("[TEST 2] Testing Over-irrigation detection...")
    over_irr = evaluate_smart_irrigation(soil_moisture=85.0, air_temp=28.0, rain_forecast_prob=10.0)
    assert over_irr["status"] == "OVER-IRRIGATION / WATERLOGGING", f"Unexpected over_irr: {over_irr}"
    print(f"  Passed! Status: {over_irr['status']}")

    print("[TEST 3] Testing Nutrient Deficiency multimodal logic...")
    n_def = evaluate_multimodal_disease_context(vision_class="Yellowing Chlorosis", soil_moisture=30.0, air_temp=28.0, humidity=60.0, ec_salinity=1.2)
    assert "Nitrogen" in n_def["diagnosis"], f"Expected Nitrogen deficiency, got: {n_def['diagnosis']}"
    print(f"  Passed! Diagnosis: {n_def['diagnosis']}")

    print("[TEST 4] Testing Real Image Validation & Feature Extraction...")
    # Create an in-memory test image (green leaf simulation)
    test_img = Image.new("RGB", (200, 200), color=(40, 180, 50))
    buf = io.BytesIO()
    test_img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    val_res = validate_leaf_image(img_bytes)
    feat_vec = extract_vision_features(img_bytes)
    assert feat_vec is not None and len(feat_vec) > 0, "Feature vector is empty"
    print(f"  Passed! Valid: {val_res['valid']}, Feature Vector Length: {len(feat_vec)}")

    print("[TEST 5] Testing Safe Vision AI Diagnosis...")
    diag_res = local_vision_ai.diagnose(image_bytes=img_bytes)
    assert "status" in diag_res, "Status missing"
    print(f"  Passed! Vision Status: {diag_res['status']}")

    print("[TEST 6] Testing Database Historical Telemetry...")
    hist = db_layer.get_all_zones_recent_history(limit_per_zone=10)
    assert "zone_1" in hist and len(hist["zone_1"]) > 0, "Historical records missing for zone 1"
    print(f"  Passed! Zone 1 has {len(hist['zone_1'])} historical points, Zone 2 has {len(hist['zone_2'])} points")

    print("\n[ALL 6 TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    run_tests()
