"""
LOCAL ADVISOR AI TRAINING SCRIPT
--------------------------------
Trains a local Natural Language Processing & Agronomy Decision Model on agricultural Q&A dataset.
Saves trained pipeline to mlbackend/advisor_model.joblib.
"""

import json
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

DATA_PATH = os.path.join(os.path.dirname(__file__), "agri_training_data.json")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "advisor_model.joblib")

def train_local_advisor_model():
    print("=" * 60)
    print("TRAINING AGRISENTINEL LOCAL ADVISOR AI MODEL...")
    print("=" * 60)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Training dataset not found at {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = [item["query"] for item in data]
    intents = [item["intent"] for item in data]
    response_map = {item["intent"]: item["response"] for item in data}

    model_pipeline = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), stop_words="english"),
        LogisticRegression(C=1.0)
    )

    model_pipeline.fit(queries, intents)

    packaged = {
        "pipeline": model_pipeline,
        "responses": response_map,
        "version": "1.0.0-Local-Advisor"
    }

    joblib.dump(packaged, MODEL_PATH)
    print(f"[SUCCESS] Local Advisor AI Model trained & saved to: {MODEL_PATH}")

if __name__ == "__main__":
    train_local_advisor_model()
