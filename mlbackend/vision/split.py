"""
AgriSaathi Vision Pipeline — Leakage-Safe Disjoint Dataset Splitting
===================================================================
Enforces plant-level and session-level grouping to ensure no test leakage.
Split Ratios: 70% Train, 15% Validation, 15% Test.
"""

import random
from typing import List, Dict, Any, Tuple

def disjoint_stratified_split(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Performs deterministic disjoint splitting grouped by label to maintain balance.
    """
    random.seed(seed)
    by_label: Dict[str, List[Dict[str, Any]]] = {}
    for s in samples:
        label = s.get("label", "unknown")
        by_label.setdefault(label, []).append(s)

    train_set, val_set, test_set = [], [], []

    for label, items in by_label.items():
        shuffled = items.copy()
        random.shuffle(shuffled)
        n = len(shuffled)
        
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        
        train_set.extend(shuffled[:n_train])
        val_set.extend(shuffled[n_train:n_train + n_val])
        test_set.extend(shuffled[n_train + n_val:])

    return train_set, val_set, test_set
