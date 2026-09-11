"""
YOUR OWN CUSTOM AI CHATBOT MODEL TRAINER
----------------------------------------
Build and train your very own custom AI Chatbot model from scratch.
Uses custom dataset from mlbackend/custom_llm_dataset.json and exports mlbackend/custom_agri_llm.joblib.
"""

import json
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline

DATA_PATH = os.path.join(os.path.dirname(__file__), "custom_llm_dataset.json")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "custom_agri_llm.joblib")

def train_my_custom_ai_chatbot():
    print("=" * 60)
    print("TRAINING YOUR CUSTOM AGRISENTINEL AI CHATBOT MODEL...")
    print("=" * 60)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Custom dataset not found at {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    prompts = [item["input"] for item in dataset]
    instructions = [item["instruction"] for item in dataset]
    outputs = [item["output"] for item in dataset]

    inputs = [f"{ins} {p}" for ins, p in zip(instructions, prompts)]
    target_ids = list(range(len(outputs)))

    custom_model_pipeline = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), stop_words="english"),
        MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300, random_state=42)
    )

    custom_model_pipeline.fit(inputs, target_ids)

    custom_ai_artifact = {
        "pipeline": custom_model_pipeline,
        "outputs": outputs,
        "prompts": prompts,
        "model_name": "AgriSaathi-Custom-Neural-LLM-v1.0",
        "total_samples_trained": len(outputs)
    }

    joblib.dump(custom_ai_artifact, MODEL_PATH)
    print("[SUCCESS] Your custom AI Chatbot model has been trained & saved to:")
    print(f"File Path: {MODEL_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    train_my_custom_ai_chatbot()
