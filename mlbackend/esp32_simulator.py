"""
AgriSaathi ESP32 Telemetry Simulator
=====================================
Generates realistic time-series sensor data with:
- Diurnal temperature/humidity patterns
- Gradual soil moisture changes  
- Irrigation events affecting moisture
- Rainfall events
- Sensor noise (not completely random)
- Occasional missing readings
- Battery/signal variation

All simulated data is clearly marked with: "data_source": "SIMULATED"
"""
import math
import random
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class ESP32TelemetrySimulator:
    """Realistic field ESP32 sensor simulator with time-series physics."""
    
    def __init__(
        self,
        device_id: str = "ESP32-SIM-001",
        farm_id: str = "farm-001",
        field_id: str = "field-rice-sim",
        crop: str = "Rice",
        growth_stage: str = "Vegetative",
        latitude: float = 30.73,
        longitude: float = 76.78
    ):
        self.device_id = device_id
        self.farm_id = farm_id
        self.field_id = field_id
        self.crop = crop
        self.growth_stage = growth_stage
        self.latitude = latitude
        self.longitude = longitude
        
        # Persistent simulator state
        self._sequence = 0
        self._base_moisture = 45.0  # Starting soil moisture %
        self._battery_v = 4.2       # Fully charged
        self._last_irrigation_ts = None
        self._rain_active = False
        self._rain_mm_remaining = 0.0

    def _diurnal_temp(self, hour_of_day: float, base_temp: float = 28.0) -> float:
        """Realistic daily temperature curve: cool at 5am, peak at 2pm."""
        # Cosine curve scaled around base temperature
        delta = 6.0 * math.cos(2 * math.pi * (hour_of_day - 14) / 24)
        noise = random.gauss(0, 0.3)
        return round(base_temp + delta + noise, 1)
    
    def _diurnal_humidity(self, air_temp: float) -> float:
        """Humidity inversely correlated with temperature + noise."""
        base_humidity = max(30, 95 - (air_temp - 15) * 1.8)
        noise = random.gauss(0, 1.5)
        return round(min(99.0, max(20.0, base_humidity + noise)), 1)
    
    def _update_moisture(self, air_temp: float, humidity: float, rain_event: bool) -> float:
        """Soil moisture follows ET0 loss + rain/irrigation gain."""
        # Evapotranspiration loss (simplified ET0 hourly)
        et0_hourly = 0.0023 * (air_temp + 17.8) * math.sqrt(max(air_temp - 10, 1)) * 4.5 / 24.0
        loss = et0_hourly * (1 + random.gauss(0, 0.05))
        
        # Rain gains
        rain_gain = 0.0
        if rain_event and self._rain_mm_remaining > 0:
            rain_gain = min(self._rain_mm_remaining, 1.5)
            self._rain_mm_remaining -= rain_gain
            if self._rain_mm_remaining <= 0:
                self._rain_active = False
        
        self._base_moisture = max(15.0, min(95.0, self._base_moisture - loss + rain_gain))
        # Add slight sensor noise
        sensor_noise = random.gauss(0, 0.2)
        return round(self._base_moisture + sensor_noise, 1)

    def simulate_irrigation_event(self, water_mm: float = 15.0):
        """Simulate irrigation pump activation."""
        self._base_moisture = min(80.0, self._base_moisture + water_mm * 0.6)
        self._last_irrigation_ts = time.time()

    def simulate_rain_event(self, rain_mm: float = 12.0):
        """Simulate rainfall event."""
        self._rain_active = True
        self._rain_mm_remaining = rain_mm

    def _update_battery(self) -> float:
        """Battery drains slowly with occasional comms bursts."""
        drain = 0.0002 + random.uniform(0, 0.0001)
        self._battery_v = max(3.3, self._battery_v - drain)
        return round(self._battery_v, 2)

    def generate_telemetry(self) -> Dict[str, Any]:
        """Generate one realistic telemetry reading."""
        self._sequence += 1
        now = datetime.now(timezone.utc)
        hour_of_day = now.hour + now.minute / 60.0

        # Determine if we're in a simulated rain event
        if random.random() < 0.003:  # ~0.3% chance each reading of starting rain
            self.simulate_rain_event(rain_mm=random.uniform(5.0, 25.0))

        air_temp = self._diurnal_temp(hour_of_day)
        humidity = self._diurnal_humidity(air_temp)
        soil_temp = round(air_temp - random.uniform(3.0, 6.0), 1)  # Soil slightly cooler
        soil_moisture = self._update_moisture(air_temp, humidity, self._rain_active)
        battery_v = self._update_battery()
        rssi = random.randint(-80, -45)  # Realistic Wi-Fi RSSI values
        
        # Simulate occasional missing readings (5% chance)
        ph_reading = round(random.gauss(6.8, 0.15), 2) if random.random() > 0.05 else None
        ec_reading = round(random.gauss(1.15, 0.08), 2) if random.random() > 0.05 else None

        # NPK - simulated sensor values (realistic ranges for paddy)
        npk = {
            "N": round(random.gauss(45.0, 5.0), 1),
            "P": round(random.gauss(22.0, 3.0), 1),
            "K": round(random.gauss(38.0, 4.0), 1)
        }

        return {
            "schemaVersion": 1,
            "messageId": f"{self.device_id}-{self._sequence}-{int(time.time())}",
            "deviceId": self.device_id,
            "farmId": self.farm_id,
            "fieldId": self.field_id,
            "crop": self.crop,
            "growthStage": self.growth_stage,
            "sequence": self._sequence,
            "timestamp": now.isoformat(),
            "data_source": "SIMULATED",  # CRITICAL: marks this as non-production data
            "readings": {
                "soil_moisture_pct": soil_moisture,
                "soil_temperature_c": soil_temp,
                "soil_ph": ph_reading,
                "soil_ec_ds_m": ec_reading,
                "air_temperature_c": air_temp,
                "air_humidity_pct": humidity,
                "rain_detected": self._rain_active,
                "NPK_ppm": npk
            },
            "device": {
                "battery_v": battery_v,
                "rssi_dbm": rssi,
                "firmware": "0.1.0-SIM",
                "uptime_s": self._sequence * 10
            },
            "sensor_health": self._assess_sensor_health(soil_moisture, air_temp, humidity, battery_v, rssi)
        }

    def _assess_sensor_health(
        self,
        moisture: float,
        temp: float,
        humidity: float,
        battery_v: float,
        rssi: int
    ) -> Dict[str, Any]:
        """Evaluate sensor health and flag impossible/suspect readings."""
        issues = []
        
        if moisture < 0 or moisture > 100:
            issues.append("IMPOSSIBLE_MOISTURE")
        if temp < -10 or temp > 60:
            issues.append("TEMPERATURE_OUT_OF_RANGE")
        if humidity < 0 or humidity > 100:
            issues.append("IMPOSSIBLE_HUMIDITY")
        if battery_v < 3.5:
            issues.append("LOW_BATTERY")
        if rssi < -85:
            issues.append("POOR_SIGNAL")
        
        status = "HEALTHY" if not issues else ("DEGRADED" if len(issues) <= 2 else "CRITICAL")
        return {"status": status, "issues": issues, "battery_level_pct": round((battery_v - 3.3) / (4.2 - 3.3) * 100, 0)}


# Singleton simulator instance
esp32_simulator = ESP32TelemetrySimulator()
