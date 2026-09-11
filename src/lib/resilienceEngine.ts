/**
 * AGRISENTINEL - RESILIENCE ALERT ENGINE
 * -------------------------------------------------------------
 * Step 3: Pure function resilience alert engine with zero side-effects.
 * Evaluates multi-reading consecutive trends across history to prevent false alarms.
 */

import { SensorReading } from "./sensorService";

export interface ResilienceAlert {
  id: string;
  type: "drought" | "heatwave" | "flood" | "nutrient" | "dht_fault";
  severity: "WARNING" | "CRITICAL";
  title: string;
  message: string;
  recommendation: string;
  triggeredAt: number;
}

/**
 * Step 3.1 & 3.2: Pure function evaluating resilience alerts based on current reading and historical trend.
 */
export function evaluateResilienceAlerts(
  reading: SensorReading,
  history: SensorReading[] = []
): ResilienceAlert[] {
  const alerts: ResilienceAlert[] = [];
  const now = Date.now();

  // Combine current reading with history for consecutive trend analysis
  const fullSequence = [reading, ...history];

  // 1. Step 1.2 / Step 7.3: Check DHT Sensor Hardware Integrity Flag
  if (!reading.dht_ok) {
    alerts.push({
      id: `dht_fault_${now}`,
      type: "dht_fault",
      severity: "CRITICAL",
      title: "⚠️ DHT Sensor Hardware Fault",
      message: "DHT22 sensor hardware reported invalid or unreadable data.",
      recommendation: "Inspect physical DHT22 sensor wiring on GPIO pin 4 of ESP32 board.",
      triggeredAt: now,
    });
  }

  // 2. Step 3.2: Drought Resilience Alert (Requires 3 consecutive readings < 20% soil moisture)
  const recent3 = fullSequence.slice(0, 3);
  const isConsecutiveDrought = recent3.length >= 3 && recent3.every((r) => r.soil_moisture < 20);

  if (isConsecutiveDrought) {
    alerts.push({
      id: `drought_${now}`,
      type: "drought",
      severity: "CRITICAL",
      title: "🚨 Prolonged Dryness Alert (Drought Risk)",
      message: `Soil moisture has remained critically low (${reading.soil_moisture}%) across consecutive samples.`,
      recommendation: "Schedule immediate Zone 2 Drip Irrigation pump cycle.",
      triggeredAt: now,
    });
  } else if (reading.soil_moisture < 20) {
    alerts.push({
      id: `drought_warn_${now}`,
      type: "drought",
      severity: "WARNING",
      title: "⚠️ Low Soil Moisture Alert",
      message: `Soil moisture dropped to ${reading.soil_moisture}%. Monitoring trend...`,
      recommendation: "Prepare irrigation pump if moisture continues dropping.",
      triggeredAt: now,
    });
  }

  // 3. Heatwave Resilience Alert (Temperature > 36°C)
  const recentHeat = fullSequence.slice(0, 2);
  const isConsecutiveHeat = recentHeat.length >= 2 && recentHeat.every((r) => r.temperature >= 36);

  if (isConsecutiveHeat) {
    alerts.push({
      id: `heatwave_${now}`,
      type: "heatwave",
      severity: "WARNING",
      title: "☀️ Heat Wave Stress Alert",
      message: `Ambient temperature elevated at ${reading.temperature}°C across consecutive samples.`,
      recommendation: "Activate micro-mister relay and increase shade coverage to reduce transpiration.",
      triggeredAt: now,
    });
  }

  // 4. Step 3.4: Flood Saturation Alert (ONLY evaluate if real rain sensor exists)
  if (reading.hasRainSensor && reading.rain !== undefined && reading.rain > 50) {
    alerts.push({
      id: `flood_${now}`,
      type: "flood",
      severity: "WARNING",
      title: "🌊 Heavy Rainfall & Flood Risk",
      message: `Rainfall sensor detected heavy precipitation (${reading.rain} mm/h).`,
      recommendation: "Clear field drainage channels to avoid root hypoxia.",
      triggeredAt: now,
    });
  }

  // 5. Nutrient Imbalance Alert (ONLY evaluate if real NPK sensor exists)
  if (reading.hasNpkSensor && reading.npk && reading.npk.n < 15) {
    alerts.push({
      id: `nutrient_${now}`,
      type: "nutrient",
      severity: "WARNING",
      title: "🧪 Nitrogen (N) Deficiency Alert",
      message: `NPK sensor ground-truth shows low Nitrogen level (${reading.npk.n} ppm).`,
      recommendation: "Apply Neem-coated Urea or organic liquid bio-nitrogen spray.",
      triggeredAt: now,
    });
  }

  return alerts;
}
