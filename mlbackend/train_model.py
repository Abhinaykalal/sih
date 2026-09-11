import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

def train_crop_recommendation_model(dataset_path: str):
    """
    Trains a Precision Agriculture model using the provided dataset.
    Dataset should be a CSV with columns: [N, P, K, temperature, humidity, ph, rainfall, label]
    """
    if not os.path.exists(dataset_path):
        print(f"❌ Error: Dataset file not found at {dataset_path}")
        return

    print(f"🔄 Loading dataset from: {dataset_path}")
    df = pd.read_csv(dataset_path)

    # 1. Feature Selection
    X = df[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
    y = df['label']

    # 2. Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Train Model (Brutal Accuracy with Random Forest)
    print("🧠 Training AgriSaathi ML Model (RandomForest)...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 4. Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"✅ Training Complete! Accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred))

    # 5. Export
    joblib.dump(model, 'model.joblib')
    print("📦 Model saved to: 'model.joblib'. The Core API is now live with your custom training!")

if __name__ == "__main__":
    # If the user provides the location, replace this path
    DATASET_LOCATION = "dataset.csv" 
    train_crop_recommendation_model(DATASET_LOCATION)
