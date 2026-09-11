"""
YOUR CUSTOM AI CHATBOT INFERENCE ENGINE
---------------------------------------
Runs inference on your custom trained AI model (custom_agri_llm.joblib).
"""

import os
import joblib
from typing import Dict, Any

MODEL_PATH = os.path.join(os.path.dirname(__file__), "custom_agri_llm.joblib")

class MyCustomAIChatbot:
    def __init__(self):
        self.model_data = None
        self.load_or_train()

    def load_or_train(self):
        if not os.path.exists(MODEL_PATH):
            try:
                try:
                    from .train_custom_llm import train_my_custom_ai_chatbot
                except ImportError:
                    from train_custom_llm import train_my_custom_ai_chatbot
                train_my_custom_ai_chatbot()
            except Exception as e:
                print(f"Custom model auto-train error: {e}")

        if os.path.exists(MODEL_PATH):
            try:
                self.model_data = joblib.load(MODEL_PATH)
                print(f"[SUCCESS] Loaded Your Custom AI Model: {self.model_data.get('model_name')}")
            except Exception as e:
                print(f"Failed to load custom AI model: {e}")

    def chat(self, user_prompt: str) -> str:
        if not self.model_data:
            return "[MY CUSTOM AI]: Model is initializing. Run py -m mlbackend.train_custom_llm to train your custom chatbot model."

        try:
            pipeline = self.model_data["pipeline"]
            outputs = self.model_data["outputs"]

            predicted_idx = pipeline.predict([user_prompt])[0]
            response = outputs[predicted_idx]

            return response
        except Exception as e:
            return f"Custom AI inference error: {e}"

my_custom_ai = MyCustomAIChatbot()
