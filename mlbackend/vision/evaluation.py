"""
AgriSaathi Vision Pipeline — Rigorous Evaluation & Per-Class Metrics
===================================================================
Generates honest evaluation metrics without fabricated claims:
- Confusion Matrix
- Per-Class Precision, Recall, F1-Score
- Macro and Weighted Averages
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

def evaluate_model_performance(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str]
) -> Dict[str, Any]:
    """Computes transparent, reproducible classification metrics."""
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)

    per_class = {}
    for lbl in labels:
        if lbl in report:
            per_class[lbl] = {
                "precision": round(report[lbl]["precision"], 3),
                "recall": round(report[lbl]["recall"], 3),
                "f1_score": round(report[lbl]["f1-score"], 3),
                "support": report[lbl]["support"]
            }

    return {
        "overall_accuracy": round(acc, 4),
        "macro_f1": round(report.get("macro avg", {}).get("f1-score", 0.0), 4),
        "weighted_f1": round(report.get("weighted avg", {}).get("f1-score", 0.0), 4),
        "per_class_metrics": per_class,
        "confusion_matrix": cm.tolist(),
        "classes": labels
    }
