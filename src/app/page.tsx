'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { AiChatModule } from '@/components/AiChatModule';
import { VisionDiagnosticModule } from '@/components/VisionDiagnosticModule';
import { CropRecommendationModule } from '@/components/CropRecommendationModule';
import { IoTDashboardModule } from '@/components/IoTDashboardModule';
import { webApi } from '@/lib/webApiClient';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [language, setLanguage] = useState<string>('en');
  const [backendOnline, setBackendOnline] = useState<boolean>(true);

  useEffect(() => {
    // Check backend health on mount
    webApi.checkHealth().then((res) => {
      setBackendOnline(res.status === 'ok' || res.status === 'healthy');
    });

    const interval = setInterval(() => {
      webApi.checkHealth().then((res) => {
        setBackendOnline(res.status === 'ok' || res.status === 'healthy');
      });
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0A0F0D] text-gray-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-200">
      
      {/* Dynamic Background Gradients */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 flex-1 flex flex-col">
        
        {/* Navigation Header */}
        <Header
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          language={language}
          setLanguage={setLanguage}
          backendOnline={backendOnline}
        />

        {/* Main Content Area */}
        <main className="max-w-7xl w-full mx-auto px-4 lg:px-8 pb-12 flex-1">
          {activeTab === 'chat' && <AiChatModule language={language} />}
          {activeTab === 'vision' && <VisionDiagnosticModule />}
          {activeTab === 'recommend' && <CropRecommendationModule />}
          {activeTab === 'iot' && <IoTDashboardModule />}
        </main>

        {/* Footer */}
        <footer className="border-t border-white/5 py-6 text-center text-xs text-gray-500">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <span>AgriSaathi AI • Problem Statement SIH26180</span>
            <span>Edge-Native AI, IoT Telemetry & Precision Agriculture</span>
          </div>
        </footer>

      </div>

    </div>
  );
}
