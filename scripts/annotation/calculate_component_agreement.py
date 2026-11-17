"""Calculate inter-annotator agreement for argument component classification.

Metrics:
- Observed Agreement (Po)
- Expected Chance Agreement (Pe)
- Cohen's Kappa (kappa)
- Krippendorff's Alpha (nominal)
- 6x6 Disagreement / Confusion Matrix in frozen taxonomy order:
    CLAIM, PREMISE, EVIDENCE, COUNTERARGUMENT, REBUTTAL, OTHER
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data.label_encoder import FROZEN_COMPONENT_LABELS, ComponentLabelEncoder


def compute_cohens_kappa(
    labels_a: List[str],
    labels_b: List[str],
    classes: List[str] = FROZEN_COMPONENT_LABELS,
) -> Dict[str, Any]:
    """Compute multi-class Cohen's Kappa and confusion matrix between two annotators."""
    if len(labels_a) != len(labels_b):
        raise ValueError(f"Label lengths do not match ({len(labels_a)} vs {len(labels_b)}).")
    n = len(labels_a)
    if n == 0:
        return {
            "status": "AGREEMENT NOT AVAILABLE",
            "reason": "Empty label sequence.",
            "cohens_kappa": 0.0,
            "observed_agreement": 0.0,
        }

    k = len(classes)
    class_to_idx = {c: i for i, c in enumerate(classes)}

    # Build k x k contingency matrix
    matrix = np.zeros((k, k), dtype=np.int32)
    for a, b in zip(labels_a, labels_b):
        idx_a = class_to_idx[a]
        idx_b = class_to_idx[b]
        matrix[idx_a, idx_b] += 1

    # Observed agreement
    po = np.trace(matrix) / n

    # Expected agreement
    row_sums = np.sum(matrix, axis=1)
    col_sums = np.sum(matrix, axis=0)
    pe = np.sum((row_sums * col_sums) / (n * n))

    # Kappa
    if 1.0 - pe < 1e-9:
        kappa = 1.0 if po == 1.0 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    # Per-class counts
    per_class: Dict[str, Dict[str, Any]] = {}
    for i, c in enumerate(classes):
        agreed = int(matrix[i, i])
        total_a = int(row_sums[i])
        total_b = int(col_sums[i])
        per_class[c] = {
            "annotator_A_count": total_a,
            "annotator_B_count": total_b,
            "agreed_count": agreed,
        }

    return {
        "status": "COMPLETED",
        "total_units": n,
        "observed_agreement": float(round(po, 4)),
        "expected_agreement": float(round(pe, 4)),
        "cohens_kappa": float(round(kappa, 4)),
        "matrix": matrix.tolist(),
        "classes": list(classes),
        "per_class": per_class,
    }


def compute_krippendorffs_alpha_nominal(
    labels_a: List[str],
    labels_b: List[str],
    classes: List[str] = FROZEN_COMPONENT_LABELS,
) -> float:
    """Compute nominal Krippendorff's alpha for 2 annotators."""
    n = len(labels_a)
    if n == 0:
        return 0.0

    agreed = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    d_o = 1.0 - (agreed / n)

    # Marginal distribution
    all_labels = labels_a + labels_b
    total_tokens = len(all_labels)
    class_counts = {c: all_labels.count(c) for c in classes}

    d_e = 0.0
    for c in classes:
        p_c = class_counts[c] / total_tokens
        d_e += p_c * (1.0 - p_c)

    if d_e < 1e-9:
        return 1.0 if d_o == 0.0 else 0.0

    alpha = 1.0 - (d_o / d_e)
    return float(round(alpha, 4))


def format_component_agreement_report(results: Dict[str, Any]) -> str:
    if results.get("status") != "COMPLETED":
        return f"STATUS: AGREEMENT NOT AVAILABLE\nReason: {results.get('reason', 'Insufficient data')}"

    lines: List[str] = [
        "=" * 72,
        "ARGUMAP Component Inter-Annotator Agreement Report",
        "=" * 72,
        f"Total Shared Units:    {results['total_units']}",
        f"Observed Agreement:    {results['observed_agreement'] * 100:.2f}%",
        f"Expected Agreement:    {results['expected_agreement'] * 100:.2f}%",
        f"Cohen's Kappa (kappa): {results['cohens_kappa']:.4f}",
    ]

    # Target threshold check
    kappa = results["cohens_kappa"]
    if kappa >= 0.70:
        interp = "SUBSTANTIAL / PASSES THRESHOLD (Target kappa >= 0.70)"
    elif kappa >= 0.60:
        interp = "MODERATE AGREEMENT (Below 0.70 threshold - calibration recommended)"
    else:
        interp = "LOW AGREEMENT (Requires guideline calibration)"
    lines.append(f"Agreement Level:       {interp}")

    lines.extend([
        "-" * 72,
        f"{'Class':<18} | {'Annotator A':<14} | {'Annotator B':<14} | {'Agreed':<8}",
        "-" * 72,
    ])

    for c in results["classes"]:
        info = results["per_class"][c]
        lines.append(
            f"{c:<18} | {info['annotator_A_count']:<14} | {info['annotator_B_count']:<14} | {info['agreed_count']:<8}"
        )

    lines.extend([
        "-" * 72,
        "Contingency Matrix (Rows: Annotator A, Columns: Annotator B):",
    ])
    header = " ".join(f"{c[:4]:>6}" for c in results["classes"])
    lines.append(f"{'':<18} {header}")

    for i, row in enumerate(results["matrix"]):
        row_name = results["classes"][i]
        row_str = " ".join(f"{val:>6d}" for val in row)
        lines.append(f"{row_name:<18} {row_str}")

    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate component annotation agreement between two annotators.")
    parser.add_argument("--annotator-a", "-a", type=Path, required=True, help="Annotation JSON from Annotator A.")
    parser.add_argument("--annotator-b", "-b", type=Path, required=True, help="Annotation JSON from Annotator B.")
    parser.add_argument("--output-json", "-o", type=Path, default=None, help="Optional output path for JSON results.")

    args = parser.parse_args()

    for p in (args.annotator_a, args.annotator_b):
        if not p.exists():
            print(f"Error: File '{p}' not found.", file=sys.stderr)
            return 1

    with open(args.annotator_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(args.annotator_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)

    units_a = data_a.get("units") or data_a.get("argument_units", [])
    units_b = data_b.get("units") or data_b.get("argument_units", [])

    map_a = {u["unit_id"]: u.get("component_label") for u in units_a if u.get("component_label")}
    map_b = {u["unit_id"]: u.get("component_label") for u in units_b if u.get("component_label")}

    common_ids = [uid for uid in map_a if uid in map_b]
    if len(common_ids) < 2:
        print("STATUS: AGREEMENT NOT AVAILABLE")
        print(f"Reason: Insufficient shared annotated units (found {len(common_ids)}).")
        return 1

    labels_a = [map_a[uid] for uid in common_ids]
    labels_b = [map_b[uid] for uid in common_ids]

    results = compute_cohens_kappa(labels_a, labels_b)
    alpha = compute_krippendorffs_alpha_nominal(labels_a, labels_b)
    results["krippendorffs_alpha"] = alpha

    print(format_component_agreement_report(results))
    print(f"Krippendorff's Alpha:  {alpha:.4f}\n")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Saved results to {args.output_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
