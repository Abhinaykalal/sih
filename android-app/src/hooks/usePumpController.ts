import { useState, useEffect, useCallback } from 'react';
import { Alert } from 'react-native';
import { ApiClient } from '../services/ApiClient';
import { loadFarmContext, getFarmContextSync, FarmProfile } from '../services/FarmContext';

export type LifecycleStage = 'IDLE' | 'REQUESTED' | 'PUBLISHED' | 'ACKNOWLEDGED' | 'ACTUATION_ACCEPTED' | 'BLOCKED' | 'REJECTED' | 'FAILED';

export function usePumpController() {
  const [farmProfile, setFarmProfile] = useState<FarmProfile>(getFarmContextSync());
  const [pumpStateData, setPumpStateData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [currentLifecycleStage, setCurrentLifecycleStage] = useState<LifecycleStage>('IDLE');
  const [commandHistory, setCommandHistory] = useState<any[]>([]);
  const [liveRainProb, setLiveRainProb] = useState<number | null>(null);

  const initAndLoad = useCallback(async () => {
    try {
      const profile = await loadFarmContext();
      setFarmProfile(profile);
    } catch {}
    loadPumpState();
  }, []);

  const loadPumpState = useCallback(async () => {
    const deviceId = farmProfile.primary_device_id || 'ESP32_NODE_01';
    try {
      const res = await ApiClient.pump.getPumpState(deviceId);
      if (res && res.state) {
        setPumpStateData(res.state);
        if (res.state.command_state === 'ACTUATION_ACCEPTED' && res.state.reported_state === 'ON') {
          setCurrentLifecycleStage('ACTUATION_ACCEPTED');
        } else if (res.state.command_state?.startsWith('REJECTED')) {
          setCurrentLifecycleStage('REJECTED');
        }
      }
      const histRes = await ApiClient.pump.getCommands(deviceId);
      if (histRes && histRes.history) {
        setCommandHistory(histRes.history);
      }
    } catch (e: any) {
      console.warn('Could not load live pump state:', e.message);
    }
  }, [farmProfile]);

  useEffect(() => {
    initAndLoad();
  }, [initAndLoad]);

  const dispatchPump = async (
    durationSec: number,
    manualOverrideActive: boolean,
    overrideReason: string,
    onBlocked: (reason: string, rainProb: number) => void
  ) => {
    setLoading(true);
    setCurrentLifecycleStage('REQUESTED');

    try {
      let activeRain = false;
      let rainProb = 0;
      let rainMm = 0;
      try {
        if (farmProfile.lat && farmProfile.lon) {
          const weather = await ApiClient.weather.getWeatherAdvice(
            farmProfile.lat, farmProfile.lon, farmProfile.active_crop || undefined
          );
          if (weather) {
            rainProb = weather.rain_probability_pct ?? 0;
            rainMm = weather.rainfall_mm ?? 0;
            activeRain = weather.weather_status === 'RAIN' || rainMm > 1.0;
            setLiveRainProb(rainProb);
          }
        }
      } catch {}

      const res = await ApiClient.pump.dispatchCommand({
        deviceId: farmProfile.primary_device_id || 'ESP32_NODE_01',
        commandType: 'PUMP_ON',
        durationSec,
        reason: manualOverrideActive ? `OVERRIDE: ${overrideReason}` : 'Farmer initiated soil moisture replenishment',
        activeRain,
        rainProbabilityPct: rainProb,
        rainForecastMm: rainMm,
        manualOverride: manualOverrideActive,
      });

      const cmd = res?.command;
      if (cmd?.status === 'blocked') {
        setCurrentLifecycleStage('BLOCKED');
        onBlocked(cmd.reason || `${rainProb}% Rain Forecast. Automatic safety lock engaged to prevent waterlogging.`, rainProb);
      } else {
        setCurrentLifecycleStage('PUBLISHED');
        
        let attempts = 0;
        const pollInterval = setInterval(async () => {
          attempts++;
          try {
            const stateRes = await ApiClient.pump.getPumpState(farmProfile.primary_device_id || 'ESP32_NODE_01');
            if (stateRes?.state) {
              const cmdState = stateRes.state.command_state;
              if (cmdState === 'ACTUATION_ACCEPTED') {
                setCurrentLifecycleStage('ACTUATION_ACCEPTED');
                clearInterval(pollInterval);
                loadPumpState();
              } else if (cmdState?.startsWith('REJECTED') || cmdState === 'FAILED') {
                setCurrentLifecycleStage('REJECTED');
                clearInterval(pollInterval);
                Alert.alert("Hardware Interlock Rejected", `ESP32 refused the command: ${cmdState}`);
                loadPumpState();
              } else if (cmdState === 'RECEIVED' || cmdState === 'ACKNOWLEDGED') {
                setCurrentLifecycleStage('ACKNOWLEDGED');
              }
            }
          } catch (e) {}
          
          if (attempts > 15) { // 30 seconds timeout
            clearInterval(pollInterval);
            Alert.alert("Timeout", "ESP32 hardware did not confirm execution. The network may be down or device offline.");
            setCurrentLifecycleStage('IDLE');
          }
        }, 2000);
      }
    } catch (e: any) {
      Alert.alert('Dispatch Error', e.message || 'Unable to communicate with pump controller.');
      setCurrentLifecycleStage('IDLE');
    } finally {
      setLoading(false);
    }
  };

  return {
    farmProfile,
    pumpStateData,
    loading,
    currentLifecycleStage,
    commandHistory,
    liveRainProb,
    dispatchPump,
    loadPumpState,
  };
}
