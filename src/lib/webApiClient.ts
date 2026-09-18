/**
 * AgriSaathi Web API Client
 * Connects directly to local FastAPI backend (or configured URL)
 */

export const getApiBase = (): string => {
  if (typeof window !== 'undefined') {
    // In browser context, use empty base (relative URLs) to leverage Next.js server rewrite proxy
    // unless an explicit public API URL is defined.
    return process.env.NEXT_PUBLIC_API_URL || '';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
};

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  provenance?: {
    model?: string;
    grounded_in_rag?: boolean;
    sources?: string[];
  };
}

export interface DiseasePrediction {
  disease: string;
  confidence: number;
  description?: string;
  recommendations?: string[];
  organic_treatments?: string[];
  chemical_treatments?: string[];
  preventive_measures?: string[];
}

export interface CropRecommendationRequest {
  nitrogen: number;
  phosphorus: number;
  potassium: number;
  temperature: number;
  humidity: number;
  ph: number;
  rainfall: number;
}

export interface CropRecommendationResponse {
  recommended_crop: string;
  confidence?: number;
  alternative_crops?: Array<{ crop: string; score: number }>;
  season?: string;
  water_requirement?: string;
}

export interface SensorMetrics {
  soil_moisture: number;
  temperature: number;
  humidity: number;
  light?: number;
  rain?: number;
  npk?: { n: number; p: number; k: number };
  pump_active?: boolean;
  status: string;
  timestamp?: string;
}

export const webApi = {
  /**
   * Health check for backend
   */
  async checkHealth(): Promise<{ status: string; version?: string }> {
    const urls = [
      `${getApiBase()}/api/health`,
      'http://127.0.0.1:8000/api/health',
      'http://localhost:8000/api/health',
    ];

    for (const url of urls) {
      try {
        const res = await fetch(url, { method: 'GET', credentials: 'omit' });
        if (res.ok) {
          const data = await res.json();
          const status = data.status || data.data?.status || (data.success ? 'healthy' : 'offline');
          return { status, version: data.service || data.version };
        }
      } catch {
        continue;
      }
    }

    return { status: 'offline' };
  },

  /**
   * AI Agronomist Chat
   */
  async sendChatMessage(
    query: string,
    language: string = 'en',
    history: Array<{ role: string; content: string }> = []
  ): Promise<{
    reply: string;
    provenance?: { model?: string; grounded_in_rag?: boolean; sources?: string[] };
  }> {
    const endpoints = [
      `${getApiBase()}/api/ai/chat`,
      'http://127.0.0.1:8000/api/ai/chat',
      'http://localhost:8000/api/ai/chat',
    ];

    const payload = {
      message: query,
      question: query,
      query: query,
      language: language,
      history: history.slice(-6),
    };

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (res.ok) {
          const data = await res.json();
          return {
            reply: data.response || data.reply || data.message || data.answer || "I could not generate an advisory for this query.",
            provenance: {
              model: data.model || data.provenance?.model || 'qwen2.5:7b-instruct',
              grounded_in_rag: data.provenance?.grounded_in_rag ?? true,
              sources: data.provenance?.sources || data.citations || ['ICAR Ground Truth'],
            },
          };
        }
      } catch {
        continue;
      }
    }

    return {
      reply: `⚠️ Connection to backend service could not be established. Ensure FastAPI backend is running on port 8000.`,
      provenance: {
        model: 'Offline Fallback',
        grounded_in_rag: false,
        sources: ['Local Offline Rules'],
      },
    };
  },

  /**
   * Crop Disease Image Predictor
   */
  async predictDisease(imageFile: File): Promise<DiseasePrediction> {
    const endpoints = [
      `${getApiBase()}/api/vision/predict`,
      'http://127.0.0.1:8000/api/vision/predict',
      'http://localhost:8000/api/vision/predict',
    ];

    const formData = new FormData();
    formData.append('file', imageFile);

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          body: formData,
        });

        if (res.ok) {
          return await res.json();
        }
      } catch {
        continue;
      }
    }

    throw new Error('Disease diagnostic service unavailable. Please check the backend connection.');
  },

  /**
   * Crop Recommendation Engine
   */
  async getCropRecommendation(params: CropRecommendationRequest): Promise<CropRecommendationResponse> {
    const endpoints = [
      `${getApiBase()}/api/recommend/crop`,
      'http://127.0.0.1:8000/api/recommend/crop',
      'http://localhost:8000/api/recommend/crop',
    ];

    const payload = {
      N: params.nitrogen,
      P: params.phosphorus,
      K: params.potassium,
      temperature: params.temperature,
      humidity: params.humidity,
      ph: params.ph,
      rainfall: params.rainfall,
    };

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (res.ok) {
          return await res.json();
        }
      } catch {
        continue;
      }
    }

    throw new Error('Crop recommendation engine unavailable.');
  },

  /**
   * Live IoT Sensor Metrics
   */
  async getSensorMetrics(): Promise<SensorMetrics> {
    const endpoints = [
      `${getApiBase()}/api/sensor/metrics`,
      'http://127.0.0.1:8000/api/sensor/metrics',
      'http://localhost:8000/api/sensor/metrics',
    ];

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint, { method: 'GET' });
        if (res.ok) {
          return await res.json();
        }
      } catch {
        continue;
      }
    }

    // Phase 1: If backend is unavailable, return null values (never synthetic defaults)
    return {
      soil_moisture: null,
      temperature: null,
      humidity: null,
      light: null,
      rain: null,
      npk: null,
      pump_active: null,
      status: 'OFFLINE_NO_DATA',
      offline_default: true,
      timestamp: new Date().toISOString(),
    };
  },
};
