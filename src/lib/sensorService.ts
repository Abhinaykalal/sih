/**
 * AGRISENTINEL - CANONICAL SENSOR GATEWAY SERVICE (Phase 5 Remediation)
 * 
 * ✓ FIXED: Remove HTTP direct path to ESP32 (/sensors endpoint)
 * ✓ FIXED: Remove synthetic defaults (soil_moisture ?? 40, temperature ?? 28, etc.)
 * ✓ FIXED: Use only canonical /api/telemetry/latest from backend
 * 
 * Key principle: REAL DATA OR DATA_UNAVAILABLE, never fabricated values.
 * 
 * Single data source: Backend → MQTT → /api/telemetry/latest
 * No fallback defaults allowed at frontend level.
 */

export interface NpkData {
  n: number | null;
  p: number | null;
  k: number | null;
}

export interface SensorReading {
  dht_ok: boolean;
  soil_moisture: number | null;  // Now nullable — no synthetic default
  temperature: number | null;    // Now nullable — no synthetic default
  humidity: number | null;       // Now nullable — no synthetic default
  light: number | null;          // Now nullable — no synthetic default
  hasNpkSensor: boolean;
  hasRainSensor: boolean;
  npk?: NpkData;
  rain?: number | null;
  timestamp: number;
  pump_relay?: boolean;
  data_quality?: {
    status: "LIVE" | "STALE" | "OFFLINE" | "UNAVAILABLE";
    age_seconds?: number;
    reason?: string;
  };
  message?: string;
}

export interface SensorError {
  code: "TIMEOUT" | "NETWORK_ERROR" | "PARSE_ERROR" | "MALFORMED_DATA" | "NO_DATA_AVAILABLE";
  message: string;
}

export type SensorReadingResult = 
  | { success: true; data: SensorReading }
  | { success: false; error: SensorError };

const CACHE_KEY = "agri_last_sensor_reading";
const BACKEND_TELEMETRY_URL = "/api/telemetry/latest";  // Canonical endpoint

/**
 * Phase 5: Fetch sensor data from CANONICAL BACKEND ONLY
 * 
 * ✓ REMOVED: Direct HTTP /sensors endpoint to ESP32 (was main.py issue)
 * ✓ FIXED: Use only /api/telemetry/latest which enforces real data only
 * ✓ FIXED: Preserve nulls — do NOT inject synthetic defaults
 * 
 * Query: /api/telemetry/latest?device_id=ESP32_NODE_01
 */
export async function fetchSensorData(deviceId: string = "ESP32_NODE_01", retries = 2): Promise<SensorReadingResult> {
  const url = `${BACKEND_TELEMETRY_URL}?device_id=${deviceId}`;

  let attempt = 0;
  const backoffDelays = [500, 1000];

  while (attempt <= retries) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3-second strict timeout

      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!res.ok) {
        if (res.status === 404) {
          return {
            success: false,
            error: {
              code: "NO_DATA_AVAILABLE",
              message: `No telemetry received yet for device ${deviceId}. Device state: REGISTERED.`
            }
          };
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const json = await res.json();
      
      // Validate canonical response structure
      if (!json.success || !json.data) {
        return {
          success: false,
          error: {
            code: "PARSE_ERROR",
            message: json.message || "Invalid telemetry response structure"
          }
        };
      }

      const canonical = json.data;

      // ✓ FIXED: Preserve null values — do NOT use ?? defaults
      const soil_moisture = canonical.soil_moisture_pct ?? null;
      const temperature = canonical.temperature_c ?? null;
      const humidity = canonical.humidity_pct ?? null;
      const light = null;  // Not provided by canonical telemetry

      // Capability flags (only if sensors reported real data)
      const hasNpkSensor = (canonical.nitrogen !== null && canonical.phosphorus !== null && canonical.potassium !== null);
      const hasRainSensor = false;  // Not in canonical telemetry

      let npk: NpkData | undefined = undefined;
      if (hasNpkSensor) {
        npk = {
          n: canonical.nitrogen,
          p: canonical.phosphorus,
          k: canonical.potassium
        };
      }

      const reading: SensorReading = {
        dht_ok: true,  // Assume OK if we got data
        soil_moisture,      // null if unavailable (no synthetic 40)
        temperature,        // null if unavailable (no synthetic 28)
        humidity,           // null if unavailable (no synthetic 65)
        light,              // null (not available)
        hasNpkSensor,
        hasRainSensor,
        npk,
        rain: null,
        timestamp: canonical.age_seconds ? (Date.now() - (canonical.age_seconds * 1000)) : Date.now(),
        pump_relay: canonical.pump_active ?? undefined,
        data_quality: canonical.data_quality || {
          status: "UNAVAILABLE",
          reason: "Unable to determine freshness"
        },
        message: json.message
      };

      // Save to localStorage cache for offline safety
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify(reading));
        } catch (e) {
          // Silent localstorage error
        }
      }

      return { success: true, data: reading };

    } catch (err: any) {
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, backoffDelays[attempt] || 1000));
        attempt++;
      } else {
        const isTimeout = err.name === "AbortError";
        return {
          success: false,
          error: {
            code: isTimeout ? "TIMEOUT" : "NETWORK_ERROR",
            message: isTimeout 
              ? "Backend telemetry request timed out after 3000ms" 
              : (err.message || "Failed to reach backend /api/telemetry/latest")
          }
        };
      }
    }
  }

  return {
    success: false,
    error: { code: "NETWORK_ERROR", message: "Failed to connect after retries" }
  };
}

/**
 * Retrieve cached reading from localStorage when offline.
 * Cache is stale — shows "OFFLINE" status
 */
export function getCachedSensorReading(): SensorReading | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cached = JSON.parse(raw) as SensorReading;
    // Mark cache as OFFLINE (old data)
    if (cached.data_quality) {
      cached.data_quality.status = "OFFLINE";
      cached.data_quality.reason = "Using cached data — device may be offline";
    }
    return cached;
  } catch {
    return null;
  }
}
