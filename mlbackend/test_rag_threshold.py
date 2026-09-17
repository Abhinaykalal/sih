import os
import json
from typing import List, Dict

from mlbackend.rag_engine import rag_engine

def load_train_dataset() -> List[Dict]:
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rag", "train.jsonl")
    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def evaluate_threshold(threshold: float, dataset: List[Dict]) -> dict:
    rag_engine.similarity_threshold = threshold
    hits = 0
    total_retrieved = 0
    
    for record in dataset:
        q = record["question"]
        expected_topics = [t.lower() for t in record.get("expected_source_topics", [])]
        
        chunks = rag_engine.retrieve_chunks(q, top_k=3)
        total_retrieved += len(chunks)
        
        # Check if any retrieved chunk matches the expected topics
        match_found = False
        for chunk, score in chunks:
            chunk_text = (chunk.text + " " + chunk.topic + " " + chunk.crop).lower()
            if any(et in chunk_text for et in expected_topics):
                match_found = True
                break
                
        if match_found:
            hits += 1
            
    recall = hits / len(dataset) if dataset else 0
    avg_retrieved = total_retrieved / len(dataset) if dataset else 0
    return {"threshold": threshold, "recall": recall, "avg_retrieved": avg_retrieved}

def main():
    print("==============================================")
    print("AgriSaathi RAG Threshold Calibration Optimizer")
    print("==============================================")
    
    if not rag_engine.corpus_hash:
        print("WARNING: RAG Engine failed to load corpus hash! Proceeding anyway...")
        
    dataset = load_train_dataset()
    print(f"Loaded {len(dataset)} evaluation questions.")
    
    thresholds = [1.0, 2.0, 3.0, 4.0, 4.5, 5.0, 6.0, 8.0, 10.0]
    results = []
    
    print("\nSweeping thresholds...")
    for t in thresholds:
        res = evaluate_threshold(t, dataset)
        results.append(res)
        print(f"Threshold: {t:04.1f} | Recall: {res['recall']:.2f} | Avg Chunks: {res['avg_retrieved']:.2f}")
        
    # Find optimal: highest threshold that maintains 100% recall (or best recall)
    best = max(results, key=lambda x: (x['recall'], x['threshold']))
    print(f"\nOPTIMAL THRESHOLD CALIBRATED: {best['threshold']} (Recall: {best['recall']:.2f})")
    
if __name__ == "__main__":
    main()
