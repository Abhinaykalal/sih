import { useState, useEffect, useCallback } from 'react';
import { ApiClient } from '../services/ApiClient';
import { OfflineStore } from '../services/OfflineStore';
import { loadFarmContext, getFarmContextSync, getZoneNames, FarmProfile } from '../services/FarmContext';

export interface TelemetryData {
  soil_moisture?: number | null;
  soil_moisture_pct?: number | null;
  temperature?: number | null;
  temperature_c?: number | null;
  humidity?: number | null;
  humidity_pct?: number | null;
  soil_n?: number | null;
  soil_p?: number | null;
  soil_k?: number | null;
  soil_ph?: number | null;
  battery_level?: number | null;
  wifi_rssi?: number | null;
  pump_state?: string | null;
  rain_detected?: boolean | null;
  rain_probability_pct?: number | null;
  rain_forecast_mm?: number | null;
  lockout_active?: boolean | null;
  timestamp?: string | null;
  provenance?: string;
  source?: string;
}

export function useFarmTelemetry() {
  const [farmProfile, setFarmProfile] = useState<FarmProfile>(getFarmContextSync());
  const [selectedZone, setSelectedZone] = useState('');
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [weatherData, setWeatherData] = useState<any>(null);
  const [pumpStatus, setPumpStatus] = useState<string>('OFF');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date>(new Date());
  const [liveAlerts, setLiveAlerts] = useState<any[]>([]);

  const initFarmContext = useCallback(async () => {
    try {
      const profile = await loadFarmContext();
      setFarmProfile(profile);
      const zones = getZoneNames(profile);
      if (zones.length > 0 && !selectedZone) setSelectedZone(zones[0]);
    } catch {
      const zones = getZoneNames(farmProfile);
      if (zones.length > 0 && !selectedZone) setSelectedZone(zones[0]);
    }
  }, [selectedZone, farmProfile]);

  const loadDashboardData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const deviceId = farmProfile.primary_device_id || 'ESP32_NODE_01';
      const telRes = await ApiClient.sensor.getTelemetry(deviceId, 1);
      const latest = Array.isArray(telRes)
        ? telRes[0]
        : (telRes?.history && telRes.history.length > 0
            ? telRes.history[0]
            : (telRes?.readings?.[0] || telRes?.latest || telRes));

      let currentPump = 'OFF';
      try {
        const pRes = await ApiClient.pump.getPumpState(deviceId);
        if (pRes?.state?.reported_state) {
          currentPump = pRes.state.reported_state;
        }
      } catch {
        if (latest?.pump_active != null) {
          currentPump = latest.pump_active ? 'ON' : 'OFF';
        }
      }
      setPumpStatus(currentPump);

      let liveWeather: any = null;
      try {
        if (farmProfile.lat && farmProfile.lon) {
          const wRes = await ApiClient.weather.getWeatherAdvice(
            farmProfile.lat, farmProfile.lon, farmProfile.active_crop || undefined
          );
          if (wRes) {
            liveWeather = wRes;
            setWeatherData(wRes);
          }
        }
      } catch (wErr) {}

      try {
        const alertsRes = await ApiClient.notifications.getNotifications({ limit: 3, unread_only: true });
        if (alertsRes?.notifications) {
          setLiveAlerts(alertsRes.notifications.slice(0, 3));
        }
      } catch {}

      if (latest && (latest.soil_moisture_pct !== undefined || latest.soil_moisture !== undefined || latest.temperature_c !== undefined)) {
        const rainProb = latest.rain_probability_pct ?? liveWeather?.rain_probability_pct ?? null;
        const rainMm = latest.rain_forecast_mm ?? liveWeather?.rainfall_mm ?? null;
        setTelemetry({
          soil_moisture_pct: latest.soil_moisture_pct ?? latest.soil_moisture ?? null,
          temperature_c: latest.temperature_c ?? latest.temperature ?? null,
          humidity_pct: latest.humidity_pct ?? latest.humidity ?? null,
          soil_n: latest.nitrogen ?? latest.soil_n ?? null,
          soil_p: latest.phosphorus ?? latest.soil_p ?? null,
          soil_k: latest.potassium ?? latest.soil_k ?? null,
          soil_ph: latest.ph ?? latest.soil_ph ?? null,
          battery_level: latest.battery_level ?? null,
          wifi_rssi: latest.wifi_rssi ?? null,
          pump_state: currentPump,
          rain_detected: latest.rain_detected ?? null,
          rain_probability_pct: rainProb,
          rain_forecast_mm: rainMm,
          lockout_active: rainProb != null ? rainProb >= 50 : false,
          timestamp: latest.received_at || latest.timestamp || new Date().toISOString(),
          provenance: latest.data_source || (latest.is_simulated ? 'SIMULATED' : 'LIVE_SENSOR'),
        });
        setIsOffline(false);
        setLastSyncTime(new Date());
        await OfflineStore.cacheSensorTelemetry(latest);
      } else {
        throw new Error('No telemetry packet returned by server');
      }
    } catch (e: any) {
      const cached = await OfflineStore.getCachedSensorTelemetry();
      if (cached?.data) {
        setTelemetry(cached.data);
        setIsOffline(true);
      } else {
        setTelemetry({
          soil_moisture_pct: null,
          temperature_c: null,
          humidity_pct: null,
          soil_n: null,
          soil_p: null,
          soil_k: null,
          soil_ph: null,
          battery_level: null,
          wifi_rssi: null,
          pump_state: 'UNKNOWN',
          rain_detected: null,
          rain_probability_pct: null,
          rain_forecast_mm: null,
          lockout_active: false,
          timestamp: null,
          provenance: 'UNAVAILABLE',
        });
        setIsOffline(true);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [farmProfile]);

  const refresh = () => loadDashboardData(true);

  useEffect(() => {
    initFarmContext();
  }, [initFarmContext]);

  useEffect(() => {
    if (selectedZone || farmProfile.farm_id) loadDashboardData();
  }, [selectedZone, loadDashboardData]);

  return {
    farmProfile,
    selectedZone,
    setSelectedZone,
    telemetry,
    weatherData,
    pumpStatus,
    loading,
    refreshing,
    isOffline,
    lastSyncTime,
    liveAlerts,
    refresh,
  };
}
