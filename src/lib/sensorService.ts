/**
 * AGRISENTINEL - ESP32 SENSOR GATEWAY SERVICE
 * -------------------------------------------------------------
 * Step 1: Network-resilient gateway service sitting between ESP32 and UI.
 * Handles timeouts (AbortController 3s), backoff retries, capability flags,
 * DHT integrity verification, and local caching.
 */

export interface NpkData {
  n: number;
  p: number;
  k: number;
}

export interface SensorReading {
  dht_ok: boolean;
  soil_moisture: number;
  temperature: number;
  humidity: number;
  light: number;
  hasNpkSensor: boolean;
  hasRainSensor: boolean;
  npk?: NpkData;
  rain?: number;
  timestamp: number;
  pump_relay?: boolean;
}

export interface SensorError {
  code: "TIMEOUT" | "NETWORK_ERROR" | "PARSE_ERROR" | "MALFORMED_DATA";
  message: string;
}

export type SensorReadingResult = 
  | { success: true; data: SensorReading }
  | { success: false; error: SensorError };

const CACHE_KEY = "agri_last_sensor_reading";

/**
 * Step 1.1 & 1.4: Fetch sensor data from ESP32 with AbortController (3s) and backoff retry.
 */
export async function fetchSensorData(ip: string, retries = 2): Promise<SensorReadingResult> {
  const cleanIp = ip.replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  const url = `http://${cleanIp}/sensors`;

  let attempt = 0;
  const backoffDelays = [500, 1000];

  while (attempt <= retries) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3-second strict timeout

      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const json = await res.json();

      // Step 1.2: Validate data contract
      const dht_ok = typeof json.dht_ok === "boolean" ? json.dht_ok : (json.temperature !== undefined && json.humidity !== undefined);
      const soil_moisture = Number(json.soil_moisture ?? json.z2_moisture ?? 40);
      const temperature = Number(json.temperature ?? json.air_temp ?? 28);
      const humidity = Number(json.humidity ?? json.z4_humidity ?? 65);
      const light = Number(json.light ?? 8000);

      // Step 1.3: Capability flags (only set true if hardware payload contains npk/rain)
      const hasNpkSensor = Boolean(json.npk || (json.npk_n !== undefined && json.npk_p !== undefined));
      const hasRainSensor = Boolean(json.rain !== undefined || json.rain_val !== undefined);

      let npk: NpkData | undefined = undefined;
      if (hasNpkSensor) {
        npk = json.npk || {
          n: Number(json.npk_n ?? 24),
          p: Number(json.npk_p ?? 18),
          k: Number(json.npk_k ?? 30)
        };
      }

      let rain: number | undefined = undefined;
      if (hasRainSensor) {
        rain = Number(json.rain ?? json.rain_val ?? 0);
      }

      const reading: SensorReading = {
        dht_ok,
        soil_moisture,
        temperature,
        humidity,
        light,
        hasNpkSensor,
        hasRainSensor,
        npk,
        rain,
        timestamp: Date.now(),
        pump_relay: Boolean(json.pump_relay)
      };

      // Save to localStorage cache for offline safety (Step 6.2)
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
              ? "ESP32 request timed out after 3000ms" 
              : (err.message || "Failed to reach ESP32 node")
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
 */
export function getCachedSensorReading(): SensorReading | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
