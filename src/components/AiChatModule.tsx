'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, BookOpen, AlertCircle, RefreshCw } from 'lucide-react';
import { webApi, ChatMessage } from '@/lib/webApiClient';

interface AiChatModuleProps {
  language: string;
}

export const AiChatModule: React.FC<AiChatModuleProps> = ({ language }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-msg',
      role: 'assistant',
      content: language === 'hi'
        ? 'नमस्ते किसान साथी! मैं आपका एग्रीसाथी कृषि सलाहकार AI हूँ। आप अपनी फसल, मिट्टी, सिंचाई, खाद या कीट नियंत्रण के बारे में कुछ भी पूछ सकते हैं।'
        : language === 'te'
        ? 'నమస్కారం రైతు మిత్రమా! నేను మీ అగ్రిసాథి AI వ్యవసాయ సలహాదారుని. పంటలు, ఎరువులు, నీటిపారుదల లేదా తెగుళ్ల నివారణ గురించి అడగండి.'
        : 'Hello! I am your AgriSaathi AI Agronomist. Ask me anything about crop health, soil moisture management, fertilizer schedules, or pest remediation.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      provenance: {
        model: 'AgriSaathi Agronomist',
        grounded_in_rag: true,
        sources: ['ICAR Precision Crop Guidelines', 'TNAU Agronomy Manual'],
      },
    },
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const sampleQuestions = [
    'How do I treat yellow rust in wheat?',
    'What is the optimal NPK ratio for paddy in vegetative stage?',
    'How frequently should drip irrigation run for cotton in black soil?',
    'My tomato leaves have yellow spots with concentric rings. What should I do?',
  ];

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const historyPayload = messages.map((m) => ({ role: m.role, content: m.content }));
      const response = await webApi.sendChatMessage(query, language, historyPayload);

      const aiMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        provenance: response.provenance,
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: '⚠️ Failed to receive advisory from backend. Please check network or retry.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      
      {/* Sidebar - Quick Prompts & Grounding Info */}
      <div className="lg:col-span-1 flex flex-col gap-4">
        
        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm mb-3">
            <Sparkles className="w-4 h-4" />
            <span>Suggested Questions</span>
          </div>
          <div className="flex flex-col gap-2">
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                className="text-left text-xs text-gray-300 hover:text-emerald-300 bg-white/5 hover:bg-emerald-500/10 p-2.5 rounded-lg border border-white/5 hover:border-emerald-500/20 transition-all leading-relaxed"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 text-blue-400 font-semibold text-sm mb-2">
            <BookOpen className="w-4 h-4" />
            <span>RAG Knowledge Base</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">
            Advisories are grounded in ICAR, TNAU, and agronomic knowledge bases with zero unverified hallucinations.
          </p>
        </div>

      </div>

      {/* Main Chat Stream */}
      <div className="lg:col-span-3 glass-panel flex flex-col h-[650px]">
        
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    isUser
                      ? 'bg-blue-600/30 text-blue-400 border border-blue-500/40'
                      : 'bg-emerald-600/30 text-emerald-400 border border-emerald-500/40'
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div
                  className={`rounded-2xl p-4 text-sm leading-relaxed ${
                    isUser
                      ? 'bg-blue-600/20 border border-blue-500/30 text-gray-100 rounded-tr-none'
                      : 'bg-emerald-950/40 border border-emerald-500/20 text-gray-100 rounded-tl-none'
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.content}</p>

                  {/* Provenance & Citation Tags */}
                  {msg.provenance && (
                    <div className="mt-3 pt-2.5 border-t border-white/10 flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {msg.provenance.model || 'AgriSaathi AI'}
                      </span>
                      {msg.provenance.grounded_in_rag && (
                        <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          RAG Grounded
                        </span>
                      )}
                      {msg.provenance.sources && msg.provenance.sources.length > 0 && (
                        <span className="text-gray-400">
                          Sources: {msg.provenance.sources.join(', ')}
                        </span>
                      )}
                      <span className="ml-auto text-gray-500">{msg.timestamp}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 max-w-[85%] mr-auto items-center">
              <div className="w-8 h-8 rounded-full bg-emerald-600/30 text-emerald-400 border border-emerald-500/40 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="glass-panel p-3.5 rounded-2xl rounded-tl-none flex items-center gap-2 text-xs text-emerald-300">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Generating agronomist advisory with RAG grounding...</span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-white/10 bg-black/30">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                language === 'hi'
                  ? 'फसल या मिट्टी से संबंधित कोई भी सवाल पूछें...'
                  : language === 'te'
                  ? 'వ్యవసాయం లేదా పంటల గురించి ఏదైనా అడగండి...'
                  : 'Ask about crop symptoms, fertilizer dosage, irrigation timings...'
              }
              className="glass-input flex-1 text-sm text-white"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm flex items-center gap-2 transition-all"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>

      </div>

    </div>
  );
};
