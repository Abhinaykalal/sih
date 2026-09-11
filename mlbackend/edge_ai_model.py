"""
LOCAL QUALCOMM EDGE AI MODEL INFERENCE ENGINE
---------------------------------------------
Executes local AI inference using trained machine learning model (edge_ai_model.joblib).
Replaces cloud APIs when Groq API is offline / unconfigured.
"""

import os
import joblib
from typing import Dict, Any

MODEL_PATH = os.path.join(os.path.dirname(__file__), "edge_ai_model.joblib")

class LocalEdgeAIModel:
    def __init__(self):
        self.model_data = None
        self.load_or_train_model()

    def load_or_train_model(self):
        if not os.path.exists(MODEL_PATH):
            print("Edge AI model file not found. Running training script...")
            try:
                try:
                    from .train_edge_model import train_local_edge_ai_model
                except ImportError:
                    from train_edge_model import train_local_edge_ai_model
                train_local_edge_ai_model()

            except Exception as e:
                print(f"Model auto-train error: {e}")
                return

        if os.path.exists(MODEL_PATH):
            try:
                self.model_data = joblib.load(MODEL_PATH)
                print("✅ Qualcomm Local Edge AI Model loaded successfully.")
            except Exception as e:
                print(f"Failed to load Edge AI model: {e}")

    def predict(self, user_query: str) -> str:
        """Executes local ML model inference on user query."""
        if not self.model_data:
            return "📡 [QUALCOMM EDGE AI]: Local AI model initializing. Please train using mlbackend/train_edge_model.py"

        try:
            pipeline = self.model_data["pipeline"]
            responses = self.model_data["responses"]

            predicted_intent = pipeline.predict([user_query])[0]
            response_text = responses.get(predicted_intent, "Apply standard crop protection and monitor soil moisture.")

            return (
                f"🤖 [LOCAL EDGE AI MODEL INFERENCE]\n"
                f"Predicted Intent: {predicted_intent.upper()}\n\n"
                f"💡 AI Advice:\n{response_text}\n\n"
                f"⚡ Executed on-device (Qualcomm Edge ML Engine - 0% Internet)"
            )
        except Exception as e:
            return f"Edge AI inference error: {e}"

# Global Edge AI instance
local_edge_ai = LocalEdgeAIModel()
