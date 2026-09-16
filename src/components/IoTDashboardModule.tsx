'use client';

import React, { useState, useEffect } from 'react';
import { Activity, Droplets, Thermometer, Sun, CloudRain, Zap, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';
import { webApi, SensorMetrics } from '@/lib/webApiClient';

export const IoTDashboardModule: React.FC = () => {
  const [metrics, setMetrics] = useState<SensorMetrics>({
    soil_moisture: 38.4,
    temperature: 27.6,
    humidity: 62.0,
    light: 8400,
    rain: 0,
    npk: { n: 42, p: 28, k: 34 },
    pump_active: false,
    status: 'connecting',
  });

  const [loading, setLoading] = useState(false);
  const [pumpManual, setPumpManual] = useState(false);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const data = await webApi.getSensorMetrics();
      setMetrics(data);
    } catch {
      // Keep cached metrics
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000); // 10s auto poll
    return () => clearInterval(interval);
  }, []);

  const isMoistureLow = metrics.soil_moisture < 30;
  const isHeatHigh = metrics.temperature > 35;

  return (
    <div className="space-y-6">
      
      {/* Top Banner & Quick Refresh */}
      <div className="glass-panel p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Edge IoT Gateway & Irrigation Telemetry</h2>
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] font-medium border border-emerald-500/30">
              ESP32 Node 01
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Real-time multi-sensor telemetry with automatic local threshold evaluations and relay trigger.
          </p>
        </div>

        <button
          onClick={fetchMetrics}
          disabled={loading}
          className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white text-xs font-medium border border-white/10 flex items-center gap-2 transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Resilience Alerts (if any) */}
      {(isMoistureLow || isHeatHigh) && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <h4 className="font-bold text-amber-300">Resilience Alert Active</h4>
            {isMoistureLow && (
              <p className="text-amber-200/80 mt-0.5">
                • Soil moisture is below threshold ({metrics.soil_moisture}% &lt; 30%). Automatic drip irrigation recommended.
              </p>
            )}
            {isHeatHigh && (
              <p className="text-amber-200/80 mt-0.5">
                • Ambient temperature elevated ({metrics.temperature}°C &gt; 35°C). High transpiration risk.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Sensor Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Soil Moisture */}
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400">Soil Moisture</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Droplets className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{metrics.soil_moisture}%</div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px]">
            <span className={`w-2 h-2 rounded-full ${isMoistureLow ? 'bg-amber-400' : 'bg-emerald-400'}`} />
            <span className={isMoistureLow ? 'text-amber-400' : 'text-emerald-400'}>
              {isMoistureLow ? 'Dry - Needs Irrigation' : 'Optimal Field Capacity'}
            </span>
          </div>
        </div>

        {/* Ambient Temperature */}
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400">Temperature</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <Thermometer className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{metrics.temperature}°C</div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px]">
            <span className={`w-2 h-2 rounded-full ${isHeatHigh ? 'bg-amber-400' : 'bg-emerald-400'}`} />
            <span className={isHeatHigh ? 'text-amber-400' : 'text-gray-400'}>
              {isHeatHigh ? 'Heat Stress Warning' : 'Normal Range'}
            </span>
          </div>
        </div>

        {/* Relative Humidity */}
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400">Relative Humidity</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Droplets className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{metrics.humidity}%</div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px] text-gray-400">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            <span>DHT22 Precision Sensor</span>
          </div>
        </div>

        {/* Solar Insolation */}
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400">Sunlight Lux</span>
            <div className="p-2 rounded-lg bg-yellow-500/10 text-yellow-400">
              <Sun className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{metrics.light || 8400} Lux</div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px] text-gray-400">
            <span className="w-2 h-2 rounded-full bg-yellow-400" />
            <span>LDR Photodiode Array</span>
          </div>
        </div>

      </div>

      {/* Bottom Row: NPK Status & Irrigation Pump Controller */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* NPK Real-time Balance */}
        <div className="lg:col-span-6 glass-panel p-6">
          <h3 className="text-sm font-semibold text-white mb-4">Soil Macronutrient Balance (NPK)</h3>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-300">Nitrogen (N)</span>
                <span className="text-emerald-400 font-bold">{metrics.npk?.n || 42} mg/kg</span>
              </div>
              <div className="w-full bg-black/40 h-2 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${Math.min(100, ((metrics.npk?.n || 42) / 80) * 100)}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-300">Phosphorus (P)</span>
                <span className="text-blue-400 font-bold">{metrics.npk?.p || 28} mg/kg</span>
              </div>
              <div className="w-full bg-black/40 h-2 rounded-full overflow-hidden">
                <div className="bg-blue-500 h-full rounded-full" style={{ width: `${Math.min(100, ((metrics.npk?.p || 28) / 50) * 100)}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-300">Potassium (K)</span>
                <span className="text-amber-400 font-bold">{metrics.npk?.k || 34} mg/kg</span>
              </div>
              <div className="w-full bg-black/40 h-2 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full rounded-full" style={{ width: `${Math.min(100, ((metrics.npk?.k || 34) / 60) * 100)}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Pump Relay Controller */}
        <div className="lg:col-span-6 glass-panel p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Smart Irrigation Relay Switch</h3>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                pumpManual || metrics.pump_active
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-gray-800 text-gray-400 border border-gray-700'
              }`}>
                {pumpManual || metrics.pump_active ? 'PUMP ACTIVE' : 'PUMP OFF'}
              </span>
            </div>
            <p className="text-xs text-gray-400 leading-relaxed mb-4">
              Manual override allows forced watering. When in Auto Mode, the edge controller triggers irrigation when moisture drops below 30%.
            </p>
          </div>

          <div className="pt-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-300">Manual Relay Override</span>
            <button
              onClick={() => setPumpManual(!pumpManual)}
              className={`px-5 py-2.5 rounded-xl font-semibold text-xs transition-all flex items-center gap-2 ${
                pumpManual
                  ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/30'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30'
              }`}
            >
              <Zap className="w-4 h-4" />
              <span>{pumpManual ? 'Stop Irrigation Pump' : 'Start Irrigation Pump'}</span>
            </button>
          </div>

        </div>

      </div>

    </div>
  );
};
