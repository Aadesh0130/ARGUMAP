"""Calculate inter-annotator agreement for argument relation annotation.

Evaluates agreement across:
- All 4 relation classes (SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION)
- Active rhetorical links (excluding NO_RELATION pairs)

IMPORTANT: The pilot annotations store only positive/active relation edges.
NO_RELATION is NOT explicitly annotated.  Without a defined candidate-pair
universe (turn distance window k), imputing NO_RELATION for omitted pairs
produces invalid agreement statistics.  Use ``compute_relation_agreement_shared_only``
for the valid shared-pairs-only computation.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FROZEN_RELATION_LABELS = [
    "SUPPORTS",
    "ATTACKS",
    "RESPONDS_TO",
    "NO_RELATION",
]


def compute_relation_kappa(
    relations_a: List[Dict[str, Any]],
    relations_b: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute Cohen's kappa for pairwise relation annotations.

    .. warning::

        This function treats an omitted pair as ``NO_RELATION``.  This is
        ONLY valid when the candidate-pair universe is explicitly defined
        (e.g. via a turn distance window *k*) and both annotators have
        evaluated the same complete set of candidate pairs.  In the current
        pilot data, annotators record only positive edges and the candidate
        window *k* has not been set, so results from this function should
        NOT be reported as valid agreement metrics.

        Use :func:`compute_relation_agreement_shared_only` instead.
    """
    pair_map_a = {(r["source_unit_id"], r["target_unit_id"]): r["relation_label"] for r in relations_a}
    pair_map_b = {(r["source_unit_id"], r["target_unit_id"]): r["relation_label"] for r in relations_b}

    all_pairs = sorted(list(set(pair_map_a.keys()) | set(pair_map_b.keys())))
    if len(all_pairs) < 2:
        return {
            "status": "AGREEMENT NOT AVAILABLE",
            "reason": "Insufficient shared candidate relation pairs.",
        }

    labels_a = [pair_map_a.get(p, "NO_RELATION") for p in all_pairs]
    labels_b = [pair_map_b.get(p, "NO_RELATION") for p in all_pairs]

    k = len(FROZEN_RELATION_LABELS)
    class_to_idx = {c: i for i, c in enumerate(FROZEN_RELATION_LABELS)}
    matrix = np.zeros((k, k), dtype=np.int32)

    for a, b in zip(labels_a, labels_b):
        matrix[class_to_idx[a], class_to_idx[b]] += 1

    n = len(all_pairs)
    po = np.trace(matrix) / n
    row_sums = np.sum(matrix, axis=1)
    col_sums = np.sum(matrix, axis=0)
    pe = np.sum((row_sums * col_sums) / (n * n))

    if 1.0 - pe < 1e-9:
        kappa = 1.0 if po == 1.0 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    # Active relations only (excluding NO_RELATION-NO_RELATION pairs)
    active_indices = [
        i for i, (a, b) in enumerate(zip(labels_a, labels_b))
        if not (a == "NO_RELATION" and b == "NO_RELATION")
    ]
    if len(active_indices) >= 2:
        act_a = [labels_a[i] for i in active_indices]
        act_b = [labels_b[i] for i in active_indices]
        act_agreed = sum(1 for a, b in zip(act_a, act_b) if a == b)
        active_po = act_agreed / len(active_indices)
    else:
        active_po = 1.0 if len(active_indices) == 0 else 0.0

    return {
        "status": "COMPLETED",
        "method": "union_with_NO_RELATION_imputation",
        "validity_warning": (
            "NO_RELATION was imputed for omitted pairs. This is invalid "
            "without a defined candidate-pair universe (turn distance "
            "window k). Do not report this metric as valid IAA."
        ),
        "total_pairs": n,
        "active_pairs": len(active_indices),
        "observed_agreement": float(round(po, 4)),
        "active_observed_agreement": float(round(active_po, 4)),
        "cohens_kappa": float(round(kappa, 4)),
        "matrix": matrix.tolist(),
        "classes": list(FROZEN_RELATION_LABELS),
    }


def compute_relation_agreement_shared_only(
    relations_a: List[Dict[str, Any]],
    relations_b: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute relation agreement on pairs annotated by BOTH annotators.

    This method does NOT impute NO_RELATION for omitted pairs and is valid
    even when the candidate-pair universe is undefined.  It measures whether
    annotators agree on the *label* for pairs they both chose to annotate,
    but does NOT measure whether they agree on *which pairs* to annotate.

    Returns a dict with status, metrics, and diagnostic information.
    """
    pair_map_a: Dict[Tuple[str, str], str] = {
        (r["source_unit_id"], r["target_unit_id"]): r["relation_label"]
        for r in relations_a
    }
    pair_map_b: Dict[Tuple[str, str], str] = {
        (r["source_unit_id"], r["target_unit_id"]): r["relation_label"]
        for r in relations_b
    }

    shared_pairs = sorted(set(pair_map_a.keys()) & set(pair_map_b.keys()))
    only_a = sorted(set(pair_map_a.keys()) - set(pair_map_b.keys()))
    only_b = sorted(set(pair_map_b.keys()) - set(pair_map_a.keys()))

    if len(shared_pairs) < 2:
        return {
            "status": "AGREEMENT NOT AVAILABLE",
            "reason": (
                f"Insufficient shared annotated relation pairs "
                f"({len(shared_pairs)} found, need >= 2)."
            ),
            "shared_pairs": len(shared_pairs),
            "only_annotator_A_pairs": len(only_a),
            "only_annotator_B_pairs": len(only_b),
        }

    labels_a = [pair_map_a[p] for p in shared_pairs]
    labels_b = [pair_map_b[p] for p in shared_pairs]

    # Determine the label set actually present (may not include NO_RELATION
    # if annotations only record positive edges)
    present_labels = sorted(set(labels_a) | set(labels_b))
    # Use the frozen set for the matrix, but only count what's present
    classes = [c for c in FROZEN_RELATION_LABELS if c in present_labels]
    if not classes:
        classes = list(FROZEN_RELATION_LABELS)

    k = len(classes)
    class_to_idx = {c: i for i, c in enumerate(classes)}
    matrix = np.zeros((k, k), dtype=np.int32)

    for a, b in zip(labels_a, labels_b):
        if a in class_to_idx and b in class_to_idx:
            matrix[class_to_idx[a], class_to_idx[b]] += 1

    n = len(shared_pairs)
    po = float(np.trace(matrix) / n)
    row_sums = np.sum(matrix, axis=1)
    col_sums = np.sum(matrix, axis=0)
    pe = float(np.sum((row_sums * col_sums) / (n * n)))

    kappa: Optional[float] = None
    kappa_status: str = "COMPLETED"
    kappa_note: Optional[str] = None

    if 1.0 - pe < 1e-9:
        if po == 1.0:
            # All items in single class agreed perfectly: kappa mathematically undefined (0/0)
            # or indeterminate. Standard statistical practice treats zero variance as undefined or 1.0.
            # Mark clearly:
            kappa = 1.0
            kappa_note = "Expected agreement pe == 1.0 (single class used exclusively with 100% observed agreement)."
        else:
            kappa = None
            kappa_status = "UNDEFINED"
            kappa_note = "Expected agreement pe == 1.0 but observed agreement po < 1.0; Cohen's kappa is mathematically undefined."
    else:
        kappa = float(round((po - pe) / (1.0 - pe), 4))

    agreed = sum(1 for a, b in zip(labels_a, labels_b) if a == b)

    # Per-class counts
    per_class: Dict[str, Dict[str, int]] = {}
    for i, c in enumerate(classes):
        per_class[c] = {
            "annotator_A_count": int(row_sums[i]),
            "annotator_B_count": int(col_sums[i]),
            "agreed_count": int(matrix[i, i]),
        }

    # Disagreement detail
    disagreements: List[Dict[str, str]] = []
    for p, la, lb in zip(shared_pairs, labels_a, labels_b):
        if la != lb:
            disagreements.append({
                "pair": f"{p[0]}->{p[1]}",
                "annotator_A": la,
                "annotator_B": lb,
            })

    res: Dict[str, Any] = {
        "status": "COMPLETED",
        "method": "shared_pairs_only",
        "scope": "SHARED EXPLICIT POSITIVE PAIRS ONLY",
        "limitation": (
            "Agreement computed ONLY on relation pairs explicitly annotated by both annotators. "
            "Does not measure agreement on negative relations (NO_RELATION), nor whether annotators "
            "agree on which pairs to link. Valid without a defined candidate-pair window."
        ),
        "note": (
            "Agreement computed only on pairs annotated by both annotators. "
            "Does not measure agreement on pair selection. Valid without a "
            "candidate-pair universe."
        ),
        "shared_pairs": n,
        "only_annotator_A_pairs": len(only_a),
        "only_annotator_B_pairs": len(only_b),
        "agreed": agreed,
        "observed_agreement": round(po, 4),
        "expected_agreement": round(pe, 4),
        "cohens_kappa": kappa,
        "cohens_kappa_status": kappa_status,
        "matrix": matrix.tolist(),
        "classes": classes,
        "per_class": per_class,
        "disagreements": disagreements,
    }
    if kappa_note:
        res["cohens_kappa_note"] = kappa_note
    return res


def format_relation_agreement_report(results: Dict[str, Any]) -> str:
    if results.get("status") != "COMPLETED":
        return f"STATUS: AGREEMENT NOT AVAILABLE\nReason: {results.get('reason', 'Insufficient data')}"

    lines: List[str] = [
        "=" * 72,
        "ARGUMAP Relation Inter-Annotator Agreement Report",
        "=" * 72,
    ]

    method = results.get("method", "unknown")
    lines.append(f"Method:                      {method}")

    if "validity_warning" in results:
        lines.append(f"WARNING: {results['validity_warning']}")

    if "note" in results:
        lines.append(f"Note: {results['note']}")

    if "total_pairs" in results:
        lines.append(f"Total Evaluated Pairs:       {results['total_pairs']}")
    if "shared_pairs" in results:
        lines.append(f"Shared Annotated Pairs:      {results['shared_pairs']}")
    if "only_annotator_A_pairs" in results:
        lines.append(f"Only Annotator A Pairs:      {results['only_annotator_A_pairs']}")
    if "only_annotator_B_pairs" in results:
        lines.append(f"Only Annotator B Pairs:      {results['only_annotator_B_pairs']}")
    if "active_pairs" in results:
        lines.append(f"Active Non-Trivial Pairs:    {results['active_pairs']}")

    lines.append(f"Overall Observed Agreement:  {results['observed_agreement'] * 100:.2f}%")

    if "active_observed_agreement" in results:
        lines.append(f"Active Link Agreement:       {results['active_observed_agreement'] * 100:.2f}%")

    kappa = results.get("cohens_kappa")
    if kappa is not None:
        lines.append(f"Relation Cohen's Kappa:      {kappa:.4f}")
        if kappa >= 0.65:
            interp = "SUBSTANTIAL / PASSES THRESHOLD (Target kappa >= 0.65)"
        elif kappa >= 0.50:
            interp = "MODERATE (Below 0.65 target - relation window calibration needed)"
        else:
            interp = "LOW (Requires relation tie-breaker review)"
        lines.append(f"Agreement Level:             {interp}")
    else:
        lines.append(f"Relation Cohen's Kappa:      UNAVAILABLE ({results.get('cohens_kappa_note', 'Undefined')})")
        lines.append("Agreement Level:             UNAVAILABLE")

    lines.extend([
        "-" * 72,
        "Contingency Matrix (Rows: Annotator A, Columns: Annotator B):",
    ])
    header = " ".join(f"{c[:5]:>7}" for c in results["classes"])
    lines.append(f"{'':>16} {header}")

    for i, row in enumerate(results["matrix"]):
        row_name = results["classes"][i]
        row_str = " ".join(f"{val:>7d}" for val in row)
        lines.append(f"{row_name:<16} {row_str}")

    # Show disagreements if available
    disagreements = results.get("disagreements", [])
    if disagreements:
        lines.append("-" * 72)
        lines.append("Disagreements:")
        for d in disagreements:
            lines.append(f"  {d['pair']}: A={d['annotator_A']}, B={d['annotator_B']}")

    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate relation annotation agreement.")
    parser.add_argument("--annotator-a", "-a", type=Path, required=True, help="Annotation JSON from Annotator A.")
    parser.add_argument("--annotator-b", "-b", type=Path, required=True, help="Annotation JSON from Annotator B.")
    parser.add_argument("--output-json", "-o", type=Path, default=None, help="Optional output path for JSON report.")
    parser.add_argument(
        "--method",
        choices=["shared_only", "union_impute"],
        default="shared_only",
        help=(
            "Agreement method. 'shared_only' (default) computes on shared "
            "pairs only. 'union_impute' imputes NO_RELATION for missing "
            "pairs (requires valid candidate-pair universe)."
        ),
    )

    args = parser.parse_args()

    for p in (args.annotator_a, args.annotator_b):
        if not p.exists():
            print(f"Error: File '{p}' not found.", file=sys.stderr)
            return 1

    with open(args.annotator_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(args.annotator_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)

    rels_a = data_a.get("relations", [])
    rels_b = data_b.get("relations", [])

    if args.method == "shared_only":
        results = compute_relation_agreement_shared_only(rels_a, rels_b)
    else:
        results = compute_relation_kappa(rels_a, rels_b)

    print(format_relation_agreement_report(results))

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved results to {args.output_json}")

    return 0 if results.get("status") == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())

