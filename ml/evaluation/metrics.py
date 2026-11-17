"""Evaluation metrics for ARGUMAP 6-class component classification.

All confusion matrices and classification reports strictly maintain the frozen
canonical ARGUMAP label ordering:
    CLAIM, PREMISE, EVIDENCE, COUNTERARGUMENT, REBUTTAL, OTHER
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ml.data.label_encoder import FROZEN_COMPONENT_LABELS, ComponentLabelEncoder
from ml.data.dataset_loader import ArgumentUnitSample


def compute_component_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute primary and per-class metrics for argument component classification.

    Args:
        y_true: Ground truth string labels.
        y_pred: Predicted string labels.
        labels: Optional label ordering. Defaults to FROZEN_COMPONENT_LABELS.

    Returns:
        Dict containing:
            - accuracy
            - macro_f1 (Primary Metric)
            - macro_precision
            - macro_recall
            - weighted_f1
            - per_class: Dict[label, {precision, recall, f1, support}]
            - confusion_matrix: 6x6 nested list
            - label_order: List[str]
    """
    target_labels = labels or list(FROZEN_COMPONENT_LABELS)

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, labels=target_labels, average="macro", zero_division=0))
    macro_prec = float(precision_score(y_true, y_pred, labels=target_labels, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_true, y_pred, labels=target_labels, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, labels=target_labels, average="weighted", zero_division=0))

    # Per-class scores
    per_class_f1 = f1_score(y_true, y_pred, labels=target_labels, average=None, zero_division=0)
    per_class_prec = precision_score(y_true, y_pred, labels=target_labels, average=None, zero_division=0)
    per_class_rec = recall_score(y_true, y_pred, labels=target_labels, average=None, zero_division=0)

    # Class supports
    y_true_list = list(y_true)
    supports = {lbl: y_true_list.count(lbl) for lbl in target_labels}

    per_class_metrics: Dict[str, Dict[str, float]] = {}
    for i, lbl in enumerate(target_labels):
        per_class_metrics[lbl] = {
            "precision": float(per_class_prec[i]),
            "recall": float(per_class_rec[i]),
            "f1": float(per_class_f1[i]),
            "support": int(supports[lbl]),
        }

    # Confusion matrix strictly using the target label ordering
    cm = confusion_matrix(y_true, y_pred, labels=target_labels)
    cm_list = cm.tolist()

    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "weighted_f1": weighted_f1,
        "per_class": per_class_metrics,
        "confusion_matrix": cm_list,
        "label_order": target_labels,
    }


def compute_class_distribution(
    samples: Sequence[ArgumentUnitSample],
) -> Dict[str, Any]:
    """Compute distribution statistics across the 6 frozen component classes.

    Args:
        samples: Sequence of ArgumentUnitSample objects.

    Returns:
        Dict with counts, percentages, and global collection counts.
    """
    total_units = len(samples)
    counts = {lbl: 0 for lbl in FROZEN_COMPONENT_LABELS}
    unique_debates = set()
    unique_speakers = set()

    for s in samples:
        counts[s.component_label] = counts.get(s.component_label, 0) + 1
        unique_debates.add(s.debate_id)
        unique_speakers.add(s.speaker_id)

    distribution: Dict[str, Dict[str, Any]] = {}
    for lbl in FROZEN_COMPONENT_LABELS:
        c = counts[lbl]
        pct = (c / total_units * 100.0) if total_units > 0 else 0.0
        distribution[lbl] = {
            "count": c,
            "percentage": round(pct, 2),
        }

    return {
        "total_units": total_units,
        "total_debates": len(unique_debates),
        "total_speakers": len(unique_speakers),
        "class_distribution": distribution,
    }
