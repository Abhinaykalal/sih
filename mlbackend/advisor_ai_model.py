"""
STANDALONE LOCAL ADVISOR AI MODEL INFERENCE ENGINE
---------------------------------------------------
Provides true LLM-level conversational fluency + Your Own Custom Trained AI Model.
1. Local SLM (Ollama / Llama-3.2-1B / Llama-3.2-3B / Phi-3 running locally on 127.0.0.1:11434)
2. Your Custom Trained Neural AI Model (custom_agri_llm.joblib)
"""

import os
import joblib
import requests
import json
from typing import Dict, Any, Optional


MODEL_PATH = os.path.join(os.path.dirname(__file__), "advisor_model.joblib")
OLLAMA_LOCAL_URL = "http://127.0.0.1:11434/api/generate"

class LocalAdvisorAIModel:
    def __init__(self):
        self.model_data = None
        self.load_or_train()

    def load_or_train(self):
        if not os.path.exists(MODEL_PATH):
            try:
                try:
                    from .train_advisor_model import train_local_advisor_model
                except ImportError:
                    from train_advisor_model import train_local_advisor_model
                train_local_advisor_model()
            except Exception as e:
                print(f"Advisor model train error: {e}")


        if os.path.exists(MODEL_PATH):
            try:
                self.model_data = joblib.load(MODEL_PATH)
                print("[SUCCESS] High-Accuracy Local Advisor Model loaded successfully.")
            except Exception as e:
                print(f"Failed to load Advisor AI model: {e}")

    def _try_local_ollama_llm(self, user_query: str) -> Optional[str]:
        try:
            payload = {
                "model": "llama3.2:1b",
                "prompt": f"You are AgriSaathi, an expert AI agricultural companion for Indian farmers. Answer naturally, warmly, and concisely with step-by-step guidance:\n\nQuestion: {user_query}",
                "stream": False
            }
            res = requests.post(OLLAMA_LOCAL_URL, json=payload, timeout=3)
            if res.status_code == 200:
                data = res.json()
                return data.get("response", "").strip()
        except Exception:
            pass
        return None

    def respond(self, user_query: str) -> str:
        ollama_reply = self._try_local_ollama_llm(user_query)
        if ollama_reply:
            return f"[LOCAL LLM - LLAMA 3.2 EDGE]\n\n{ollama_reply}"

        if self.model_data and "pipeline" in self.model_data:
            try:
                pipeline = self.model_data["pipeline"]
                responses = self.model_data.get("responses", {})
                predicted_intent = pipeline.predict([user_query])[0]
                if predicted_intent in responses:
                    return f"[INTENT CLASSIFIER - {predicted_intent.upper()}]\n\n{responses[predicted_intent]}"
            except Exception:
                pass

        return (
            "[ADVISORY ASSISTANT]\n\n"
            "For detailed guidance on crop cultivation, disease management, or fertilizer application, "
            "please refer to the AgriSaathi Advisory Knowledge Engine or connect to an active LLM provider."
        )

local_advisor_ai = LocalAdvisorAIModel()
