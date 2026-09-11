import AsyncStorage from '@react-native-async-storage/async-storage';

export const API_URL_STORAGE_KEY = '@agrisaathi_api_url';
export const AUTH_TOKEN_STORAGE_KEY = '@agrisaathi_auth_token';
export const DEFAULT_API_URL = 'http://10.0.2.2:8000'; // Android emulator localhost alias or local LAN

export async function getBackendBaseUrl(): Promise<string> {
  try {
    const savedUrl = await AsyncStorage.getItem(API_URL_STORAGE_KEY);
    if (savedUrl && savedUrl.trim().length > 0) {
      return savedUrl.trim().replace(/\/+$/, '');
    }
  } catch (e) {
    console.warn('Failed to load saved API URL, falling back to default:', e);
  }
  return DEFAULT_API_URL;
}

export async function setBackendBaseUrl(newUrl: string): Promise<void> {
  const formatted = newUrl.trim().replace(/\/+$/, '');
  await AsyncStorage.setItem(API_URL_STORAGE_KEY, formatted);
}

export async function getAuthToken(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch (e) {
    return null;
  }
}

export async function setAuthToken(token: string | null): Promise<void> {
  if (token) {
    await AsyncStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } else {
    await AsyncStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
}

class BaseApiClient {
  async fetchApi(endpoint: string, options: RequestInit = {}): Promise<any> {
    const baseUrl = await getBackendBaseUrl();
    const token = await getAuthToken();
    const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
      }

      return await response.json();
    } catch (err: any) {
      console.error(`ApiClient error calling [${endpoint}]:`, err.message);
      throw err;
    }
  }
}

export class AgentClient extends BaseApiClient {
  async sendChat(query: string, context?: { crop?: string; stage?: string; fieldId?: string }) {
    return this.fetchApi('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: query,
        crop: context?.crop || 'Rice',
        stage: context?.stage || 'Vegetative',
        field_id: context?.fieldId || 'zone-1-north-field',
      }),
    });
  }
}

export class VisionClient extends BaseApiClient {
  async diagnoseLeafImage(base64Image: string, cropName: string = 'Rice', growthStage: string = 'Vegetative') {
    return this.fetchApi('/api/vision-diagnose', {
      method: 'POST',
      body: JSON.stringify({
        image: base64Image,
        crop_type: cropName,
        growth_stage: growthStage,
      }),
    });
  }
}

export class SensorClient extends BaseApiClient {
  async getTelemetry(deviceId: string = 'ESP32_NODE_01', limit: number = 20) {
    return this.fetchApi(`/telemetry?device_id=${encodeURIComponent(deviceId)}&limit=${limit}`, {
      method: 'GET',
    });
  }

  async getHistoricalTelemetry(deviceId: string = 'ESP32_NODE_01', limit: number = 20) {
    return this.fetchApi(`/telemetry?device_id=${encodeURIComponent(deviceId)}&limit=${limit}`, {
      method: 'GET',
    });
  }
}

export class PumpClient extends BaseApiClient {
  async dispatchCommand(payload: {
    deviceId?: string;
    commandType: 'PUMP_ON' | 'PUMP_OFF' | 'MISTER_ON' | 'MISTER_OFF';
    durationSec?: number;
    reason?: string;
    activeRain?: boolean;
    rainProbabilityPct?: number;
    rainForecastMm?: number;
    manualOverride?: boolean;
  }) {
    return this.fetchApi('/pump/command', {
      method: 'POST',
      body: JSON.stringify({
        device_id: payload.deviceId || 'ESP32_NODE_01',
        command_type: payload.commandType,
        duration_sec: payload.durationSec ?? 300,
        reason: payload.reason || 'Farmer actuation from AgriSaathi Android App',
        active_rain: payload.activeRain ?? false,
        rain_probability_pct: payload.rainProbabilityPct ?? 0.0,
        rain_forecast_mm: payload.rainForecastMm ?? 0.0,
        manual_override: payload.manualOverride ?? false,
      }),
    });
  }

  async getCommands(deviceId: string = 'ESP32_NODE_01') {
    return this.fetchApi(`/pump/commands?device_id=${encodeURIComponent(deviceId)}`, {
      method: 'GET',
    });
  }

  async getPumpState(deviceId: string = 'ESP32_NODE_01') {
    return this.fetchApi(`/pump/state?device_id=${encodeURIComponent(deviceId)}`, {
      method: 'GET',
    });
  }
}


export class CropRecommendationClient extends BaseApiClient {
  async recommendCrop(features: {
    N: number;
    P: number;
    K: number;
    temperature: number;
    humidity: number;
    ph: number;
    rainfall: number;
  }) {
    return this.fetchApi('/api/recommend', {
      method: 'POST',
      body: JSON.stringify(features),
    });
  }
}

export class NotificationClient extends BaseApiClient {
  async getNotifications(params?: {
    user_id?: string;
    severity?: string;
    unread_only?: boolean;
    limit?: number;
  }) {
    const q = new URLSearchParams();
    if (params?.user_id) q.append('user_id', params.user_id);
    if (params?.severity) q.append('severity', params.severity);
    if (params?.unread_only) q.append('unread_only', 'true');
    if (params?.limit) q.append('limit', String(params.limit));
    const qs = q.toString();
    return this.fetchApi(`/notifications${qs ? '?' + qs : ''}`, { method: 'GET' });
  }

  async markRead(id: string) {
    return this.fetchApi(`/notifications/${encodeURIComponent(id)}/read`, { method: 'PATCH' });
  }

  async markResolved(id: string) {
    return this.fetchApi(`/notifications/${encodeURIComponent(id)}/resolve`, { method: 'PATCH' });
  }

  async syncBatch(events: any[], userId: string = '00000000-0000-0000-0000-000000000001') {
    return this.fetchApi('/notifications/sync', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, events }),
    });
  }

  async getSyncStatus() {
    return this.fetchApi('/notifications/sync/status', { method: 'GET' });
  }
}

export class FarmMetadataClient extends BaseApiClient {
  async getFarms() {
    return this.fetchApi('/farms', { method: 'GET' });
  }

  async getZones(farmId?: string) {
    return this.fetchApi(`/zones${farmId ? '?farm_id=' + encodeURIComponent(farmId) : ''}`, { method: 'GET' });
  }

  async getDevices() {
    return this.fetchApi('/devices', { method: 'GET' });
  }
}

export class WeatherClient extends BaseApiClient {
  async getWeatherAdvice(lat: number = 30.9010, lon: number = 75.8573, crop: string = 'Rice') {
    return this.fetchApi('/api/weather-advice', {
      method: 'POST',
      body: JSON.stringify({ lat, lon, crop }),
    });
  }
}

export class DeviceClient extends BaseApiClient {
  async registerDevice(deviceData: {
    deviceId: string;
    farmId: string;
    fieldId: string;
    deviceName: string;
    firmwareVersion?: string;
    communicationType?: string;
  }) {
    return this.fetchApi('/api/device-register', {
      method: 'POST',
      body: JSON.stringify(deviceData),
    });
  }

  async getLifecycle(deviceId: string = 'ESP32_NODE_01') {
    return this.fetchApi(`/api/devices/${encodeURIComponent(deviceId)}/lifecycle`, {
      method: 'GET',
    });
  }
}

export class AIClient extends BaseApiClient {
  async getStatus() {
    return this.fetchApi('/api/ai/status', { method: 'GET' });
  }

  async getModels() {
    return this.fetchApi('/api/ai/models', { method: 'GET' });
  }

  async chat(payload: {
    question: string;
    language?: string;
    farm_id?: string;
    zone_id?: string;
    include_sensor_context?: boolean;
    include_weather_context?: boolean;
    top_k?: number;
    model?: string;
  }) {
    return this.fetchApi('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({
        question: payload.question,
        language: payload.language || 'en',
        farm_id: payload.farm_id || 'farm-alpha',
        zone_id: payload.zone_id || 'zone-1',
        include_sensor_context: payload.include_sensor_context ?? true,
        include_weather_context: payload.include_weather_context ?? true,
        top_k: payload.top_k ?? 3,
        model: payload.model,
      }),
    });
  }

  async queryRAG(question: string, language: string = 'en', top_k: number = 3) {
    return this.fetchApi('/api/ai/rag/query', {
      method: 'POST',
      body: JSON.stringify({
        question,
        language,
        top_k,
      }),
    });
  }

  async getSources() {
    return this.fetchApi('/api/ai/rag/sources', { method: 'GET' });
  }

  async getEvaluation() {
    return this.fetchApi('/api/ai/evaluation', { method: 'GET' });
  }
}

// Export Unified Singleton ApiClient
export const ApiClient = {
  ai: new AIClient(),
  agent: new AgentClient(),
  vision: new VisionClient(),
  sensor: new SensorClient(),
  pump: new PumpClient(),
  crop: new CropRecommendationClient(),
  notifications: new NotificationClient(),
  farm: new FarmMetadataClient(),
  device: new DeviceClient(),
  weather: new WeatherClient(),
};

