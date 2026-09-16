import AsyncStorage from '@react-native-async-storage/async-storage';

export const API_URL_STORAGE_KEY = '@agrisaathi_api_url';
export const AUTH_TOKEN_STORAGE_KEY = '@agrisaathi_auth_token';
export const DEFAULT_API_URL = 'https://agrisaathi-6dg1.onrender.com';

export async function getBackendBaseUrl(): Promise<string> {
  try {
    const savedUrl = await AsyncStorage.getItem(API_URL_STORAGE_KEY);
    if (savedUrl && savedUrl.trim().length > 0) return savedUrl.trim().replace(/\/+$/, '');
  } catch (e) {
    console.warn('Failed to load saved API URL:', e);
  }
  return DEFAULT_API_URL;
}

export async function setBackendBaseUrl(newUrl: string): Promise<void> {
  await AsyncStorage.setItem(API_URL_STORAGE_KEY, newUrl.trim().replace(/\/+$/, ''));
}

export async function getAuthToken(): Promise<string | null> {
  try { return await AsyncStorage.getItem(AUTH_TOKEN_STORAGE_KEY); } catch { return null; }
}

export async function setAuthToken(token: string | null): Promise<void> {
  if (token) await AsyncStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  else await AsyncStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

class BaseApiClient {
  async fetchApi(endpoint: string, options: RequestInit = {}): Promise<any> {
    const baseUrl = await getBackendBaseUrl();
    const token = await getAuthToken();
    const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = `Bearer ${token}`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(url, { ...options, headers, signal: controller.signal });
      const text = await response.text();
      let payload: any = null;
      try { payload = text ? JSON.parse(text) : null; } catch { payload = { raw: text }; }
      if (!response.ok) {
        const detail = payload?.detail || payload?.message || response.statusText || 'Request failed';
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }
      return payload;
    } finally {
      clearTimeout(timeout);
    }
  }
}

export class AgentClient extends BaseApiClient {
  async sendChat(query: string, context?: { crop?: string; stage?: string; fieldId?: string; lat?: number; lon?: number }) {
    return this.fetchApi('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: query,
        ...(context?.crop ? { crop: context.crop } : {}),
        ...(context?.stage ? { stage: context.stage } : {}),
        ...(context?.fieldId ? { field_id: context.fieldId } : {}),
        ...(context?.lat != null ? { lat: context.lat } : {}),
        ...(context?.lon != null ? { lon: context.lon } : {}),
      }),
    });
  }
}

export class VisionClient extends BaseApiClient {
  async diagnoseLeafImage(base64Image: string, cropName?: string, growthStage?: string) {
    if (!base64Image || base64Image.length < 100) throw new Error('No valid image data supplied.');
    return this.fetchApi('/api/vision-diagnose', {
      method: 'POST',
      body: JSON.stringify({
        image_base64: base64Image,
        ...(cropName ? { crop_type: cropName } : {}),
        ...(growthStage ? { growth_stage: growthStage } : {}),
      }),
    });
  }
}

export class SensorClient extends BaseApiClient {
  async getTelemetry(deviceId: string, limit: number = 20) {
    if (!deviceId) throw new Error('deviceId is required.');
    return this.fetchApi(`/telemetry?device_id=${encodeURIComponent(deviceId)}&limit=${limit}`, { method: 'GET' });
  }
  async getHistoricalTelemetry(deviceId: string, limit: number = 20) {
    return this.getTelemetry(deviceId, limit);
  }
}

export class PumpClient extends BaseApiClient {
  async dispatchCommand(payload: {
    deviceId: string;
    commandType: 'PUMP_ON' | 'PUMP_OFF' | 'MISTER_ON' | 'MISTER_OFF';
    durationSec?: number;
    reason?: string;
    activeRain?: boolean;
    rainProbabilityPct?: number;
    rainForecastMm?: number;
    manualOverride?: boolean;
  }) {
    if (!payload.deviceId) throw new Error('deviceId is required.');
    return this.fetchApi('/pump/command', {
      method: 'POST',
      body: JSON.stringify({
        device_id: payload.deviceId,
        command_type: payload.commandType,
        ...(payload.durationSec != null ? { duration_sec: payload.durationSec } : {}),
        ...(payload.reason ? { reason: payload.reason } : {}),
        ...(payload.activeRain != null ? { active_rain: payload.activeRain } : {}),
        ...(payload.rainProbabilityPct != null ? { rain_probability_pct: payload.rainProbabilityPct } : {}),
        ...(payload.rainForecastMm != null ? { rain_forecast_mm: payload.rainForecastMm } : {}),
        ...(payload.manualOverride != null ? { manual_override: payload.manualOverride } : {}),
      }),
    });
  }
  async getCommands(deviceId: string) {
    if (!deviceId) throw new Error('deviceId is required.');
    return this.fetchApi(`/pump/commands?device_id=${encodeURIComponent(deviceId)}`, { method: 'GET' });
  }
  async getPumpState(deviceId: string) {
    if (!deviceId) throw new Error('deviceId is required.');
    return this.fetchApi(`/pump/state?device_id=${encodeURIComponent(deviceId)}`, { method: 'GET' });
  }
}

export class CropRecommendationClient extends BaseApiClient {
  async recommendCrop(features: {
    N: number; P: number; K: number; temperature: number; humidity: number; ph: number; rainfall: number;
  }) {
    return this.fetchApi('/api/recommend', { method: 'POST', body: JSON.stringify(features) });
  }
}

export class NotificationClient extends BaseApiClient {
  async getNotifications(params?: { user_id?: string; severity?: string; unread_only?: boolean; limit?: number }) {
    const q = new URLSearchParams();
    if (params?.user_id) q.append('user_id', params.user_id);
    if (params?.severity) q.append('severity', params.severity);
    if (params?.unread_only) q.append('unread_only', 'true');
    if (params?.limit) q.append('limit', String(params.limit));
    return this.fetchApi(`/notifications${q.toString() ? '?' + q.toString() : ''}`, { method: 'GET' });
  }
  async markRead(id: string) { return this.fetchApi(`/notifications/${encodeURIComponent(id)}/read`, { method: 'PATCH' }); }
  async markResolved(id: string) { return this.fetchApi(`/notifications/${encodeURIComponent(id)}/resolve`, { method: 'PATCH' }); }
  async syncBatch(events: any[], userId: string) {
    if (!userId) throw new Error('userId is required.');
    return this.fetchApi('/notifications/sync', { method: 'POST', body: JSON.stringify({ user_id: userId, events }) });
  }
  async getSyncStatus() { return this.fetchApi('/notifications/sync/status', { method: 'GET' }); }
}

export class FarmMetadataClient extends BaseApiClient {
  async getFarms() { return this.fetchApi('/farms', { method: 'GET' }); }
  async getZones(farmId?: string) { return this.fetchApi(`/zones${farmId ? '?farm_id=' + encodeURIComponent(farmId) : ''}`, { method: 'GET' }); }
  async getDevices(farmId?: string) { return this.fetchApi(`/devices${farmId ? '?farm_id=' + encodeURIComponent(farmId) : ''}`, { method: 'GET' }); }
}

export class WeatherClient extends BaseApiClient {
  async getWeatherAdvice(lat: number, lon: number, crop?: string) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error('A valid farm location is required for weather.');
    return this.fetchApi('/api/weather-advice', {
      method: 'POST',
      body: JSON.stringify({ lat, lon, ...(crop ? { crop } : {}) }),
    });
  }
}

export class DeviceClient extends BaseApiClient {
  async registerDevice(deviceData: {
    deviceId: string; farmId: string; fieldId: string; deviceName: string; firmwareVersion?: string; communicationType?: string;
  }) { return this.fetchApi('/api/device-register', { method: 'POST', body: JSON.stringify(deviceData) }); }
  async getLifecycle(deviceId: string) {
    if (!deviceId) throw new Error('deviceId is required.');
    return this.fetchApi(`/api/devices/${encodeURIComponent(deviceId)}/lifecycle`, { method: 'GET' });
  }
}

export class AIClient extends BaseApiClient {
  async getHealth() { return this.fetchApi('/api/ai/health', { method: 'GET' }); }
  async getStatus() { return this.fetchApi('/api/ai/status', { method: 'GET' }); }
  async getModels() { return this.fetchApi('/api/ai/models', { method: 'GET' }); }
  async chat(payload: {
    message?: string; question?: string; context?: string; language?: string; farm_id?: string; zone_id?: string;
    include_sensor_context?: boolean; include_weather_context?: boolean; top_k?: number; model?: string;
  }) {
    const q = payload.message || payload.question || '';
    if (!q.trim()) throw new Error('AI message is required.');
    return this.fetchApi('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: q,
        question: q,
        ...(payload.context ? { context: payload.context } : {}),
        language: payload.language || 'en',
        ...(payload.farm_id ? { farm_id: payload.farm_id } : {}),
        ...(payload.zone_id ? { zone_id: payload.zone_id } : {}),
        include_sensor_context: payload.include_sensor_context ?? false,
        include_weather_context: payload.include_weather_context ?? false,
        top_k: payload.top_k ?? 3,
        ...(payload.model ? { model: payload.model } : {}),
      }),
    });
  }
  async queryRAG(question: string, language: string = 'en', top_k: number = 3) {
    return this.fetchApi('/api/ai/rag/query', { method: 'POST', body: JSON.stringify({ question, language, top_k }) });
  }
  async getSources() { return this.fetchApi('/api/ai/rag/sources', { method: 'GET' }); }
  async getEvaluation() { return this.fetchApi('/api/ai/evaluation', { method: 'GET' }); }
}

export class IrrigationClient extends BaseApiClient {
  async assessIrrigation(payload: {
    crop: string; growth_stage: string; soil_moisture: number | null; temperature_c?: number | null;
    humidity_pct?: number | null; rain_probability_pct?: number | null; rain_forecast_mm?: number | null;
  }) {
    return this.fetchApi('/api/irrigation/assess', { method: 'POST', body: JSON.stringify(payload) });
  }
}

export const ApiClient = {
  ai: new AIClient(),
  agent: new AgentClient(),
  vision: new VisionClient(),
  sensor: new SensorClient(),
  pump: new PumpClient(),
  irrigation: new IrrigationClient(),
  crop: new CropRecommendationClient(),
  notifications: new NotificationClient(),
  farm: new FarmMetadataClient(),
  device: new DeviceClient(),
  weather: new WeatherClient(),
};
