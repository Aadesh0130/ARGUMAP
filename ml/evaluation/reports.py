"""Formatting and reporting routines for ARGUMAP evaluation and dataset analysis."""

from typing import Any, Dict, List, Optional
from ml.data.label_encoder import FROZEN_COMPONENT_LABELS


def format_dataset_distribution_report(
    distribution_data: Dict[str, Any],
    is_ready: bool = True,
    unready_reason: Optional[str] = None,
) -> str:
    """Format human-readable dataset distribution report."""
    lines: List[str] = [
        "=" * 68,
        "ARGUMAP Component Dataset Distribution Report",
        "=" * 68,
    ]

    if not is_ready:
        lines.extend([
            "STATUS: DATASET NOT READY FOR TRAINING",
            f"REASON: {unready_reason or 'Insufficient production gold annotations.'}",
            "=" * 68,
        ])
        return "\n".join(lines)

    lines.extend([
        f"Total Argument Units: {distribution_data['total_units']}",
        f"Total Debates:        {distribution_data['total_debates']}",
        f"Total Speakers:       {distribution_data['total_speakers']}",
        "-" * 68,
        f"{'Label':<18} | {'Count':<8} | {'Percentage':<10}",
        "-" * 68,
    ])

    for lbl in FROZEN_COMPONENT_LABELS:
        info = distribution_data["class_distribution"].get(lbl, {"count": 0, "percentage": 0.0})
        lines.append(f"{lbl:<18} | {info['count']:<8} | {info['percentage']:>6.2f}%")

    lines.append("=" * 68)
    return "\n".join(lines)


def format_metrics_report(
    metrics: Dict[str, Any],
    model_name: str = "Model",
) -> str:
    """Format human-readable evaluation metrics report."""
    lines: List[str] = [
        "=" * 72,
        f"ARGUMAP Evaluation Report: {model_name}",
        "=" * 72,
        f"Accuracy:        {metrics['accuracy']:.4f}",
        f"Macro F1:        {metrics['macro_f1']:.4f}  (PRIMARY METRIC)",
        f"Macro Precision: {metrics['macro_precision']:.4f}",
        f"Macro Recall:    {metrics['macro_recall']:.4f}",
        f"Weighted F1:     {metrics['weighted_f1']:.4f}",
        "-" * 72,
        f"{'Class':<18} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}",
        "-" * 72,
    ]

    for lbl in metrics["label_order"]:
        cls_m = metrics["per_class"][lbl]
        lines.append(
            f"{lbl:<18} | {cls_m['precision']:<10.4f} | {cls_m['recall']:<10.4f} | "
            f"{cls_m['f1']:<10.4f} | {cls_m['support']:<8}"
        )

    lines.extend([
        "-" * 72,
        "Confusion Matrix (Rows: Ground Truth, Columns: Predicted):",
        f"Labels: {', '.join(metrics['label_order'])}",
    ])

    # Header for confusion matrix
    col_headers = " ".join(f"{lbl[:4]:>5}" for lbl in metrics["label_order"])
    lines.append(f"{'':<18} {col_headers}")

    for i, row in enumerate(metrics["confusion_matrix"]):
        row_lbl = metrics["label_order"][i]
        row_str = " ".join(f"{val:>5d}" for val in row)
        lines.append(f"{row_lbl:<18} {row_str}")

    lines.append("=" * 72)
    return "\n".join(lines)
