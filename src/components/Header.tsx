'use client';

import React from 'react';
import { Sprout, Activity, ShieldCheck, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  language: string;
  setLanguage: (lang: string) => void;
  backendOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  language,
  setLanguage,
  backendOnline,
}) => {
  const tabs = [
    { id: 'chat', label: '🤖 AI Agronomist', icon: '🤖' },
    { id: 'vision', label: '🔬 Crop Disease Diagnosis', icon: '🔬' },
    { id: 'recommend', label: '🌱 Crop Recommendation', icon: '🌱' },
    { id: 'iot', label: '📊 Field Sensors & Irrigation', icon: '📊' },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-white/10 px-4 lg:px-8 py-3.5 mb-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <Sprout className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">AgriSaathi <span className="text-emerald-400">AI</span></h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                SIH26180
              </span>
            </div>
            <p className="text-xs text-gray-400">Precision Agriculture & Edge-Resilient Advisory</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex flex-wrap items-center justify-center gap-1.5 bg-black/40 p-1.5 rounded-xl border border-white/5">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
                  isActive
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/50'
                    : 'text-gray-300 hover:text-white hover:bg-white/5'
                }`}
              >
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* System Status & Language Toggle */}
        <div className="flex items-center gap-3">
          {/* Status Badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            backendOnline 
              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' 
              : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
          }`}>
            {backendOnline ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                <span>Backend Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-amber-400" />
                <span>Offline Fallback</span>
              </>
            )}
          </div>

          {/* Language Selector */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="glass-input text-xs py-1 px-2.5 bg-black/50 text-gray-200 border-white/20 rounded-lg cursor-pointer"
          >
            <option value="en">English (EN)</option>
            <option value="hi">हिंदी (HI)</option>
            <option value="te">తెలుగు (TE)</option>
          </select>
        </div>

      </div>
    </header>
  );
};
