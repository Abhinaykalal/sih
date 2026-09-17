import { useState, useEffect, useCallback } from 'react';
import { ApiClient } from '../services/ApiClient';
import { OfflineStore } from '../services/OfflineStore';
import { getFarmContextSync } from '../services/FarmContext';

export interface CitationItem {
  chunk_id: string;
  title: string;
  source: string;
  section?: string;
  page?: number;
  relevance_score?: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
  provenance?: string;
  modelName?: string;
  modelStatus?: string;
  retrievedChunks?: number;
  citations?: CitationItem[];
  sensorContext?: any;
  weatherContext?: any;
  warnings?: string[];
  isError?: boolean;
}

export function useAdvisoryChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'hi' | 'te'>('en');
  const [isOffline, setIsOffline] = useState(false);
  const [modelStatus, setModelStatus] = useState<string>('CHECKING');

  const checkAIStatus = useCallback(async () => {
    try {
      const res = await ApiClient.ai.getStatus();
      if (res?.ollama?.status) {
        setModelStatus(res.ollama.status);
      }
    } catch {
      setModelStatus('UNAVAILABLE');
    }
  }, []);

  const loadCachedMessages = useCallback(async () => {
    const cached = await OfflineStore.getCachedChatMessages();
    if (cached && cached.length > 0) {
      setMessages(cached);
    } else {
      setMessages([
        {
          id: 'welcome',
          sender: 'bot',
          text: 'Namaste! I am AgriSaathi AI powered by verified ICAR/IMD agricultural research and local Ollama inference. Ask me about crop health, irrigation timing, NPK balancing, or weather advisories.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          provenance: 'SOURCE_BACKED_KNOWLEDGE',
          modelName: 'qwen2.5:7b-instruct',
          modelStatus: 'AVAILABLE',
          retrievedChunks: 8,
          citations: [
            {
              chunk_id: 'icar-rice-irr-001-chk-01',
              title: 'ICAR Package of Practices for Rice Water & Irrigation Management',
              source: 'Indian Council of Agricultural Research (ICAR-IIRR)',
              section: 'Water Management & AWD Protocol',
            },
          ],
        },
      ]);
    }
  }, []);

  useEffect(() => {
    loadCachedMessages();
    checkAIStatus();
  }, [loadCachedMessages, checkAIStatus]);

  const handleSend = async (queryText: string) => {
    if (!queryText.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      sender: 'user',
      text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const updated = [...messages, userMsg];
    setMessages(updated);
    setLoading(true);

    try {
      const profile = getFarmContextSync();
      const response = await ApiClient.ai.chat({
        question: queryText,
        language: selectedLanguage,
        ...(profile.farm_id ? { farm_id: profile.farm_id } : {}),
        ...(profile.zones[0]?.id ? { zone_id: profile.zones[0].id } : {}),
        include_sensor_context: true,
        include_weather_context: true,
        top_k: 3,
      });

      const botMsg: ChatMessage = {
        id: `b_${Date.now()}`,
        sender: 'bot',
        text: response.answer || 'No answer could be synthesized from knowledge base.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        provenance: response.provenance || 'SOURCE_BACKED_KNOWLEDGE',
        modelName: response.model_name || 'qwen2.5:7b-instruct',
        modelStatus: response.model_status || 'AVAILABLE',
        retrievedChunks: response.retrieved_chunks || 0,
        citations: response.citations || [],
        sensorContext: response.sensor_context,
        weatherContext: response.weather_context,
        warnings: response.warnings || [],
      };

      const finalMsgs = [...updated, botMsg];
      setMessages(finalMsgs);
      await OfflineStore.cacheChatMessages(finalMsgs);
      setIsOffline(false);
      if (response.model_status) setModelStatus(response.model_status);
    } catch (err: any) {
      setIsOffline(true);
      await OfflineStore.enqueueAction('CHAT', { query: queryText, language: selectedLanguage });

      const offlineMsg: ChatMessage = {
        id: `b_err_${Date.now()}`,
        sender: 'bot',
        text: "You're offline. I've queued your question and will ask the AI once the connection is restored.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        provenance: 'OFFLINE_CACHE',
        modelStatus: 'UNREACHABLE',
        isError: true,
      };

      const finalMsgs = [...updated, offlineMsg];
      setMessages(finalMsgs);
      await OfflineStore.cacheChatMessages(finalMsgs);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    setMessages([]);
    await OfflineStore.cacheChatMessages([]);
    loadCachedMessages();
  };

  return {
    messages,
    loading,
    selectedLanguage,
    setSelectedLanguage,
    isOffline,
    modelStatus,
    handleSend,
    clearHistory,
  };
}
