'use client';

import React, { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, ShieldAlert, Sparkles, RefreshCw, Leaf } from 'lucide-react';
import { webApi, DiseasePrediction } from '@/lib/webApiClient';

export const VisionDiagnosticModule: React.FC = () => {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<DiseasePrediction | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedImage) return;
    setAnalyzing(true);
    setError(null);

    try {
      const diagnosis = await webApi.predictDisease(selectedImage);
      setResult(diagnosis);
    } catch (err: any) {
      setError(err.message || 'Diagnosis failed. Please ensure the backend vision service is operational.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* Upload & Image Preview Panel */}
      <div className="lg:col-span-5 glass-panel p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 font-semibold mb-2">
            <Leaf className="w-5 h-5" />
            <h2 className="text-lg text-white">Crop Leaf Disease Diagnostic</h2>
          </div>
          <p className="text-xs text-gray-400 mb-6">
            Upload an image of an affected leaf, stem, or plant to identify pathological infections and receive ICAR-approved remedies.
          </p>

          {/* Upload Dropzone */}
          <label className="border-2 border-dashed border-emerald-500/30 hover:border-emerald-500/60 bg-black/30 rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all mb-4 relative overflow-hidden group">
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />

            {previewUrl ? (
              <div className="relative w-full aspect-video rounded-lg overflow-hidden border border-emerald-500/20">
                <img
                  src={previewUrl}
                  alt="Crop preview"
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white text-xs font-medium transition-opacity">
                  Click to replace image
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center text-center py-6">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-3">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <span className="text-sm font-medium text-gray-200 mb-1">Click to browse or drop leaf image</span>
                <span className="text-xs text-gray-400">Supports JPG, PNG, WEBP (Max 10MB)</span>
              </div>
            )}
          </label>
        </div>

        {/* Action Button */}
        <button
          onClick={handleAnalyze}
          disabled={!selectedImage || analyzing}
          className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/40"
        >
          {analyzing ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Analyzing Leaf Pathology...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Run Diagnostic Inference</span>
            </>
          )}
        </button>
      </div>

      {/* Results & Prescription Panel */}
      <div className="lg:col-span-7 glass-panel p-6">
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <span>Diagnostic Evaluation & Prescription</span>
        </h3>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!result && !error && !analyzing && (
          <div className="h-64 flex flex-col items-center justify-center text-center text-gray-400">
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-3">
              <Leaf className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-300">No image analyzed yet</p>
            <p className="text-xs text-gray-400 mt-1 max-w-sm">
              Upload a plant photo and trigger inference to receive real-time disease identification and treatments.
            </p>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            
            {/* Disease Heading Card */}
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 flex items-center justify-between">
              <div>
                <span className="text-xs text-emerald-400 uppercase tracking-wide font-semibold">Identified Condition</span>
                <h4 className="text-lg font-bold text-white mt-0.5">{result.disease}</h4>
              </div>
              <div className="text-right">
                <span className="text-xs text-gray-400 block">Confidence</span>
                <span className="text-sm font-bold text-emerald-400">
                  {Math.round(result.confidence * 100)}%
                </span>
              </div>
            </div>

            {/* Description */}
            {result.description && (
              <p className="text-xs text-gray-300 leading-relaxed bg-black/30 p-3.5 rounded-xl border border-white/5">
                {result.description}
              </p>
            )}

            {/* Organic Treatments */}
            {result.organic_treatments && result.organic_treatments.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Organic & Biological Solutions</span>
                </span>
                <ul className="space-y-1 pl-4">
                  {result.organic_treatments.map((t, i) => (
                    <li key={i} className="text-xs text-gray-300 list-disc">{t}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Chemical Treatments */}
            {result.chemical_treatments && result.chemical_treatments.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Targeted Chemical Treatments</span>
                </span>
                <ul className="space-y-1 pl-4">
                  {result.chemical_treatments.map((t, i) => (
                    <li key={i} className="text-xs text-gray-300 list-disc">{t}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Preventive Measures */}
            {result.preventive_measures && result.preventive_measures.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-blue-400 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Preventive Best Practices</span>
                </span>
                <ul className="space-y-1 pl-4">
                  {result.preventive_measures.map((t, i) => (
                    <li key={i} className="text-xs text-gray-300 list-disc">{t}</li>
                  ))}
                </ul>
              </div>
            )}

          </div>
        )}

      </div>

    </div>
  );
};
