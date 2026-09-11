import AsyncStorage from '@react-native-async-storage/async-storage';
import { getBackendBaseUrl } from './ApiClient';

const SENSOR_CACHE_KEY = '@agrisaathi_sensor_cache';
const CHAT_CACHE_KEY = '@agrisaathi_chat_cache';
const OFFLINE_QUEUE_KEY = '@agrisaathi_offline_queue';

export interface QueuedOfflineAction {
  id: string;
  type: 'CHAT' | 'DIAGNOSIS' | 'DEVICE_REGISTER';
  payload: any;
  timestamp: string;
}

export class OfflineStore {
  static async cacheSensorTelemetry(data: any): Promise<void> {
    try {
      await AsyncStorage.setItem(SENSOR_CACHE_KEY, JSON.stringify({
        data,
        cachedAt: new Date().toISOString()
      }));
    } catch (e) {
      console.warn('Failed to cache sensor telemetry:', e);
    }
  }

  static async getCachedSensorTelemetry(): Promise<{ data: any; cachedAt: string } | null> {
    try {
      const raw = await AsyncStorage.getItem(SENSOR_CACHE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn('Failed to read cached sensor telemetry:', e);
    }
    return null;
  }

  static async cacheChatMessages(messages: any[]): Promise<void> {
    try {
      await AsyncStorage.setItem(CHAT_CACHE_KEY, JSON.stringify(messages));
    } catch (e) {
      console.warn('Failed to cache chat messages:', e);
    }
  }

  static async getCachedChatMessages(): Promise<any[]> {
    try {
      const raw = await AsyncStorage.getItem(CHAT_CACHE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn('Failed to read cached chat messages:', e);
    }
    return [];
  }

  static async enqueueAction(type: QueuedOfflineAction['type'], payload: any): Promise<void> {
    try {
      const existing = await this.getQueuedActions();
      const newAction: QueuedOfflineAction = {
        id: `act_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
        type,
        payload,
        timestamp: new Date().toISOString()
      };
      existing.push(newAction);
      await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(existing));
    } catch (e) {
      console.warn('Failed to enqueue offline action:', e);
    }
  }

  static async getQueuedActions(): Promise<QueuedOfflineAction[]> {
    try {
      const raw = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn('Failed to read offline queue:', e);
    }
    return [];
  }

  static async syncOfflineQueue(): Promise<{ synced: number; error?: string }> {
    try {
      const actions = await this.getQueuedActions();
      if (actions.length === 0) return { synced: 0 };

      const baseUrl = await getBackendBaseUrl();
      const response = await fetch(`${baseUrl}/api/offline-sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          queuedActions: actions,
          deviceId: 'ANDROID_PHONE_01'
        })
      });

      if (response.ok) {
        await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify([]));
        return { synced: actions.length };
      } else {
        return { synced: 0, error: `HTTP ${response.status}` };
      }
    } catch (e: any) {
      return { synced: 0, error: e.message };
    }
  }
}
