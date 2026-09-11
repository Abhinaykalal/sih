"""
TRAINING SCRIPT FOR AGRISENTINEL LOCAL EDGE AI MODEL
---------------------------------------------------
Trains a local NLP & Agronomy Decision Model on agricultural intent dataset.
Saves trained pipeline to mlbackend/edge_ai_model.joblib for zero-internet Qualcomm Edge execution.
"""

import json
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

DATA_PATH = os.path.join(os.path.dirname(__file__), "agri_training_data.json")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "edge_ai_model.joblib")

def train_local_edge_ai_model():
    print("=" * 60)
    print("TRAINING AGRISENTINEL LOCAL EDGE AI MODEL...")
    print("=" * 60)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Training dataset not found at {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = [item["query"] for item in data]
    intents = [item["intent"] for item in data]
    response_map = {item["intent"]: item["response"] for item in data}

    # Build NLP Pipeline (TF-IDF + Naive Bayes Classifier)
    model_pipeline = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), stop_words="english"),
        MultinomialNB()
    )

    # Train model
    model_pipeline.fit(queries, intents)

    # Package trained model + response map
    packaged = {
        "pipeline": model_pipeline,
        "responses": response_map,
        "version": "1.0.0-Qualcomm-Edge"
    }

    joblib.dump(packaged, MODEL_PATH)
    print(f"✅ Local Edge AI Model trained & saved to: {MODEL_PATH}")

if __name__ == "__main__":
    train_local_edge_ai_model()
