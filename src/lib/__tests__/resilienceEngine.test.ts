/**
 * AGRISENTINEL - RESILIENCE ENGINE UNIT TESTS
 * -------------------------------------------------------------
 * Step 3.5 & 7.2: Edge boundary tests for evaluateResilienceAlerts.
 * Tests 20% moisture boundary, 19.9%, 20.1%, and DHT hardware faults.
 */

import { evaluateResilienceAlerts } from "../resilienceEngine";
import { SensorReading } from "../sensorService";

const baseReading: SensorReading = {
  dht_ok: true,
  soil_moisture: 45,
  temperature: 28,
  humidity: 60,
  light: 8000,
  hasNpkSensor: false,
  hasRainSensor: false,
  timestamp: Date.now(),
};

export function runResilienceEngineTests(): { passed: boolean; logs: string[] } {
  const logs: string[] = [];
  let passed = true;

  function assert(condition: boolean, msg: string) {
    if (condition) {
      logs.push(`✅ PASS: ${msg}`);
    } else {
      logs.push(`❌ FAIL: ${msg}`);
      passed = false;
    }
  }

  // Test 1: Optimal readings -> 0 alerts
  const res1 = evaluateResilienceAlerts(baseReading, []);
  assert(res1.length === 0, "Optimal readings produce 0 alerts");

  // Test 2: Boundary test at 20.1% -> 0 alerts
  const r20_1: SensorReading = { ...baseReading, soil_moisture: 20.1 };
  const res2 = evaluateResilienceAlerts(r20_1, []);
  assert(res2.length === 0, "Moisture at 20.1% produces no drought alert");

  // Test 3: Boundary test at 19.9% (Single reading) -> 1 WARNING alert
  const r19_9: SensorReading = { ...baseReading, soil_moisture: 19.9 };
  const res3 = evaluateResilienceAlerts(r19_9, []);
  assert(res3.length === 1 && res3[0].severity === "WARNING", "Moisture at 19.9% (single) produces WARNING alert");

  // Test 4: Consecutive 3 readings < 20% -> 1 CRITICAL drought alert
  const res4 = evaluateResilienceAlerts(r19_9, [r19_9, r19_9]);
  assert(res4.length === 1 && res4[0].severity === "CRITICAL", "3 consecutive readings < 20% produce CRITICAL drought alert");

  // Test 5: DHT sensor fault -> 1 dht_fault alert
  const rDhtFault: SensorReading = { ...baseReading, dht_ok: false };
  const res5 = evaluateResilienceAlerts(rDhtFault, []);
  assert(res5.some((a) => a.type === "dht_fault"), "dht_ok = false produces dht_fault alert");

  return { passed, logs };
}
