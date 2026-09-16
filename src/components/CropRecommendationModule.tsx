'use client';

import React, { useState } from 'react';
import { Sprout, RefreshCw, CheckCircle2, Droplets, Thermometer, Wind, TestTube } from 'lucide-react';
import { webApi, CropRecommendationResponse } from '@/lib/webApiClient';

export const CropRecommendationModule: React.FC = () => {
  const [formData, setFormData] = useState({
    nitrogen: 40,
    phosphorus: 30,
    potassium: 35,
    temperature: 26,
    humidity: 65,
    ph: 6.5,
    rainfall: 120,
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CropRecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await webApi.getCropRecommendation(formData);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Crop recommendation failed. Check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* Input Parameters Form */}
      <div className="lg:col-span-6 glass-panel p-6">
        <div className="flex items-center gap-2 text-emerald-400 font-semibold mb-2">
          <Sprout className="w-5 h-5" />
          <h2 className="text-lg text-white">Soil & Climate Parameters</h2>
        </div>
        <p className="text-xs text-gray-400 mb-6">
          Enter N-P-K nutrient levels, soil pH, and local climatic conditions to predict the highest-yielding crop for your field.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          
          {/* NPK Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1">Nitrogen (N)</label>
              <input
                type="number"
                value={formData.nitrogen}
                onChange={(e) => setFormData({ ...formData, nitrogen: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                placeholder="40"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1">Phosphorus (P)</label>
              <input
                type="number"
                value={formData.phosphorus}
                onChange={(e) => setFormData({ ...formData, phosphorus: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                placeholder="30"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1">Potassium (K)</label>
              <input
                type="number"
                value={formData.potassium}
                onChange={(e) => setFormData({ ...formData, potassium: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                placeholder="35"
                required
              />
            </div>
          </div>

          {/* Climate & Soil Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1 flex items-center gap-1">
                <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                <span>Temperature (°C)</span>
              </label>
              <input
                type="number"
                step="0.1"
                value={formData.temperature}
                onChange={(e) => setFormData({ ...formData, temperature: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1 flex items-center gap-1">
                <Wind className="w-3.5 h-3.5 text-blue-400" />
                <span>Humidity (%)</span>
              </label>
              <input
                type="number"
                value={formData.humidity}
                onChange={(e) => setFormData({ ...formData, humidity: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1 flex items-center gap-1">
                <TestTube className="w-3.5 h-3.5 text-purple-400" />
                <span>Soil pH</span>
              </label>
              <input
                type="number"
                step="0.1"
                value={formData.ph}
                onChange={(e) => setFormData({ ...formData, ph: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-300 font-medium block mb-1 flex items-center gap-1">
                <Droplets className="w-3.5 h-3.5 text-cyan-400" />
                <span>Rainfall (mm)</span>
              </label>
              <input
                type="number"
                value={formData.rainfall}
                onChange={(e) => setFormData({ ...formData, rainfall: Number(e.target.value) })}
                className="glass-input w-full text-sm"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-4 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/40"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Evaluating Agronomic ML Model...</span>
              </>
            ) : (
              <>
                <Sprout className="w-4 h-4" />
                <span>Calculate Crop Recommendation</span>
              </>
            )}
          </button>

        </form>
      </div>

      {/* Output / Results Panel */}
      <div className="lg:col-span-6 glass-panel p-6 flex flex-col justify-between">
        <div>
          <h3 className="text-base font-semibold text-white mb-4">Precision Crop Match</h3>

          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
              {error}
            </div>
          )}

          {!result && !error && !loading && (
            <div className="h-64 flex flex-col items-center justify-center text-center text-gray-400">
              <Sprout className="w-12 h-12 text-gray-400 mb-3" />
              <p className="text-sm font-medium text-gray-300">Ready to evaluate field suitability</p>
              <p className="text-xs text-gray-400 mt-1 max-w-xs">
                Fill the soil & climate metrics on the left to run ML inference.
              </p>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              
              {/* Primary Recommended Crop */}
              <div className="p-5 rounded-2xl bg-gradient-to-br from-emerald-950/60 to-emerald-900/20 border border-emerald-500/40">
                <span className="text-xs uppercase font-bold text-emerald-400 tracking-wider">Top Recommended Crop</span>
                <div className="flex items-center justify-between mt-1">
                  <h4 className="text-2xl font-black text-white capitalize">{result.recommended_crop}</h4>
                  {result.confidence && (
                    <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold border border-emerald-500/30">
                      {Math.round(result.confidence * 100)}% Match
                    </span>
                  )}
                </div>
              </div>

              {/* Season & Water Details */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl bg-black/30 border border-white/5">
                  <span className="text-[11px] text-gray-400 block">Optimal Season</span>
                  <span className="text-sm font-semibold text-gray-200 mt-0.5 block capitalize">
                    {result.season || 'Kharif / Rabi'}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-black/30 border border-white/5">
                  <span className="text-[11px] text-gray-400 block">Water Requirement</span>
                  <span className="text-sm font-semibold text-gray-200 mt-0.5 block capitalize">
                    {result.water_requirement || 'Moderate (Drip Recommended)'}
                  </span>
                </div>
              </div>

              {/* Alternative Crops */}
              {result.alternative_crops && result.alternative_crops.length > 0 && (
                <div className="p-4 rounded-xl bg-black/20 border border-white/5">
                  <span className="text-xs font-semibold text-gray-300 block mb-2">Secondary Viable Options</span>
                  <div className="flex flex-wrap gap-2">
                    {result.alternative_crops.map((alt, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-lg bg-white/5 text-gray-300 text-xs border border-white/10 flex items-center gap-1.5 capitalize"
                      >
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span>{alt.crop} ({Math.round(alt.score * 100)}%)</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>

        <div className="text-[11px] text-gray-400 border-t border-white/10 pt-3 mt-4">
          Model trained on Indian soil profiles across 22+ agricultural agro-climatic zones.
        </div>

      </div>

    </div>
  );
};
