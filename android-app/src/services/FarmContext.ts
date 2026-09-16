import AsyncStorage from '@react-native-async-storage/async-storage';
import { ApiClient } from './ApiClient';

const FARM_CONTEXT_KEY = '@agrisaathi_farm_context';

export interface FarmZone {
  id: string;
  name: string;
  crop?: string;
  growth_stage?: string;
}

export interface FarmDevice {
  device_id: string;
  device_name: string;
  zone_id?: string;
  firmware_version?: string;
  communication_type?: string;
  status?: string;
}

export interface FarmProfile {
  farm_id: string;
  farm_name: string;
  location_name: string;
  lat: number;
  lon: number;
  area_acres?: number;
  owner_name?: string;
  owner_role?: string;
  zones: FarmZone[];
  devices: FarmDevice[];
  active_crop: string;
  active_growth_stage: string;
  primary_device_id: string;
}

const DEFAULT_FARM_PROFILE: FarmProfile = {
  farm_id: '',
  farm_name: 'AgriSaathi Farm',
  location_name: 'Location not configured',
  lat: 0,
  lon: 0,
  area_acres: undefined,
  owner_name: undefined,
  owner_role: undefined,
  zones: [],
  devices: [],
  active_crop: '',
  active_growth_stage: '',
  primary_device_id: 'ESP32_NODE_01',
};

let _cachedProfile: FarmProfile | null = null;

/**
 * Load farm context from backend APIs, falling back to AsyncStorage cache.
 * All screens should use this instead of hardcoding farm metadata.
 */
export async function loadFarmContext(): Promise<FarmProfile> {
  try {
    // 1. Try fetching from backend
    const [farmsRes, zonesRes, devicesRes] = await Promise.allSettled([
      ApiClient.farm.getFarms(),
      ApiClient.farm.getZones(),
      ApiClient.farm.getDevices(),
    ]);

    const farms = farmsRes.status === 'fulfilled' && farmsRes.value ? farmsRes.value : null;
    const zonesData = zonesRes.status === 'fulfilled' && zonesRes.value ? zonesRes.value : null;
    const devicesData = devicesRes.status === 'fulfilled' && devicesRes.value ? devicesRes.value : null;

    const farmList = Array.isArray(farms) ? farms : (farms?.farms || []);
    const zoneList = Array.isArray(zonesData) ? zonesData : (zonesData?.zones || []);
    const deviceList = Array.isArray(devicesData) ? devicesData : (devicesData?.devices || []);

    const primaryFarm = farmList[0] || {};

    const zones: FarmZone[] = zoneList.map((z: any) => ({
      id: z.zone_id || z.id || '',
      name: z.zone_name || z.name || 'Unnamed Zone',
      crop: z.crop || z.active_crop || undefined,
      growth_stage: z.growth_stage || undefined,
    }));

    const devices: FarmDevice[] = deviceList.map((d: any) => ({
      device_id: d.device_id || d.id || '',
      device_name: d.device_name || d.name || 'Unknown Device',
      zone_id: d.zone_id || undefined,
      firmware_version: d.firmware_version || undefined,
      communication_type: d.communication_type || undefined,
      status: d.status || 'unknown',
    }));

    // Derive active crop from first zone with a crop set
    const activeZone = zones.find(z => z.crop) || zones[0];

    const profile: FarmProfile = {
      farm_id: primaryFarm.farm_id || primaryFarm.id || '',
      farm_name: primaryFarm.farm_name || primaryFarm.name || DEFAULT_FARM_PROFILE.farm_name,
      location_name: primaryFarm.location || primaryFarm.location_name || DEFAULT_FARM_PROFILE.location_name,
      lat: primaryFarm.latitude || primaryFarm.lat || 0,
      lon: primaryFarm.longitude || primaryFarm.lon || 0,
      area_acres: primaryFarm.area_acres || primaryFarm.area || undefined,
      owner_name: primaryFarm.owner_name || primaryFarm.owner || undefined,
      owner_role: primaryFarm.owner_role || undefined,
      zones,
      devices,
      active_crop: activeZone?.crop || '',
      active_growth_stage: activeZone?.growth_stage || '',
      primary_device_id: devices[0]?.device_id || DEFAULT_FARM_PROFILE.primary_device_id,
    };

    _cachedProfile = profile;
    await AsyncStorage.setItem(FARM_CONTEXT_KEY, JSON.stringify(profile));
    return profile;
  } catch (e) {
    // 2. Fallback to cached context
    console.warn('FarmContext: Could not load from backend, using cache:', e);
    return getCachedFarmContext();
  }
}

/**
 * Get cached farm context from AsyncStorage (for offline use).
 */
export async function getCachedFarmContext(): Promise<FarmProfile> {
  if (_cachedProfile) return _cachedProfile;

  try {
    const cached = await AsyncStorage.getItem(FARM_CONTEXT_KEY);
    if (cached) {
      _cachedProfile = JSON.parse(cached);
      return _cachedProfile!;
    }
  } catch (e) {
    console.warn('FarmContext: Failed to read cache:', e);
  }

  return { ...DEFAULT_FARM_PROFILE };
}

/**
 * Get the currently loaded profile synchronously (returns default if not loaded yet).
 */
export function getFarmContextSync(): FarmProfile {
  return _cachedProfile || { ...DEFAULT_FARM_PROFILE };
}

/**
 * Get zone names for display. Falls back to a default if none are loaded.
 */
export function getZoneNames(profile: FarmProfile): string[] {
  if (profile.zones.length > 0) {
    return profile.zones.map(z => z.name);
  }
  return ['Default Zone'];
}
