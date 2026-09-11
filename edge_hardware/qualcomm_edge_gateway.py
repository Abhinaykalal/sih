"""
AGRISENTINEL EDGE GATEWAY DAEMON (QUALCOMM HARDWARE / RASPBERRY PI)
-------------------------------------------------------------------
Reads Serial / USB / LoRa telemetry streams from physical ESP32 sensor nodes 
and forwards readings to the AgriSaathi Risk Engine.
"""

import time
import requests
import json
import random

GATEWAY_URL = "http://127.0.0.1:8000/api/sensor-data"

def run_edge_gateway():
    print("=" * 60)
    print("AGRISENTINEL QUALCOMM EDGE GATEWAY DAEMON")
    print("=" * 60)
    print(f"Connecting to Local Edge Engine: {GATEWAY_URL}")
    print("Press Ctrl+C to terminate gateway telemetry loop.\n")

    while True:
        try:
            # Simulate reading hardware serial stream from ESP32 / Qualcomm NPU pins
            telemetry = {
                "zone_id": 2,
                "z1_moisture": round(random.uniform(40.0, 50.0), 1),
                "z2_moisture": round(random.uniform(14.0, 18.0), 1), # Simulated Water Stress
                "z3_pest_count": random.randint(22, 28),             # Simulated Pest Spike
                "z4_humidity": round(random.uniform(88.0, 94.0), 1), # Simulated Fungal Saturation
                "air_temp": round(random.uniform(32.0, 36.0), 1),
                "ec_salinity": round(random.uniform(1.0, 1.4), 1),
                "wind_speed": 8.0
            }

            response = requests.post(GATEWAY_URL, json=telemetry, timeout=3)
            if response.status_code == 200:
                data = response.json()
                print(f"[{time.strftime('%H:%M:%S')}] 📡 Telemetry Pushed -> Zone 2 Moisture: {telemetry['z2_moisture']}% | Overall Risk Index: {data['farm_status']['disaster_scores']['overall_farm_health_score']}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Gateway Push Error: HTTP {response.status_code}")

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 🔴 Edge Gateway Offline / Retrying: {e}")

        time.sleep(5)

if __name__ == "__main__":
    run_edge_gateway()
