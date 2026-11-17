"""Compare two annotation files for identical debate transcripts.

Outputs:
- Alignment check between unit IDs and relation pairs.
- Exact count and percentage of component agreements and disagreements.
- Detailed mismatch table with proposition text, speaker, and labels.
- Relation agreement and disagreement report.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data.label_encoder import FROZEN_COMPONENT_LABELS


def compare_component_annotations(
    units_a: List[Dict[str, Any]],
    units_b: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare component labels across units with matching unit_id."""
    map_a = {u["unit_id"]: u for u in units_a}
    map_b = {u["unit_id"]: u for u in units_b}

    common_ids = [uid for uid in map_a if uid in map_b]
    if not common_ids:
        return {"error": "No common unit_ids found between annotation files."}

    agreements = 0
    disagreements: List[Dict[str, Any]] = []

    for uid in common_ids:
        u_a = map_a[uid]
        u_b = map_b[uid]
        lbl_a = u_a.get("component_label")
        lbl_b = u_b.get("component_label")

        if lbl_a == lbl_b:
            agreements += 1
        else:
            disagreements.append({
                "unit_id": uid,
                "text": u_a.get("unit_text") or u_a.get("text", ""),
                "speaker_id": u_a.get("speaker_id", "unknown"),
                "turn_index": u_a.get("turn_index", 0),
                "annotator_A_label": lbl_a,
                "annotator_B_label": lbl_b,
                "note_A": u_a.get("note"),
                "note_B": u_b.get("note"),
            })

    total = len(common_ids)
    pct = (agreements / total * 100.0) if total > 0 else 0.0

    return {
        "total_units": total,
        "agreed_units": agreements,
        "disagreed_units": len(disagreements),
        "observed_agreement_pct": round(pct, 2),
        "disagreements": disagreements,
    }


def compare_relation_annotations(
    relations_a: List[Dict[str, Any]],
    relations_b: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare relation labels across pairs with matching (source_unit_id, target_unit_id)."""
    pair_map_a = {(r["source_unit_id"], r["target_unit_id"]): r for r in relations_a}
    pair_map_b = {(r["source_unit_id"], r["target_unit_id"]): r for r in relations_b}

    all_pairs = sorted(list(set(pair_map_a.keys()) | set(pair_map_b.keys())))
    agreements = 0
    disagreements: List[Dict[str, Any]] = []

    for pair in all_pairs:
        r_a = pair_map_a.get(pair)
        r_b = pair_map_b.get(pair)
        lbl_a = r_a.get("relation_label", "NO_RELATION") if r_a else "NO_RELATION"
        lbl_b = r_b.get("relation_label", "NO_RELATION") if r_b else "NO_RELATION"

        if lbl_a == lbl_b:
            agreements += 1
        else:
            disagreements.append({
                "source_unit_id": pair[0],
                "target_unit_id": pair[1],
                "annotator_A_label": lbl_a,
                "annotator_B_label": lbl_b,
                "turn_distance": r_a.get("turn_distance") if r_a else (r_b.get("turn_distance") if r_b else None),
            })

    total = len(all_pairs)
    pct = (agreements / total * 100.0) if total > 0 else 0.0

    return {
        "total_evaluated_pairs": total,
        "agreed_pairs": agreements,
        "disagreed_pairs": len(disagreements),
        "observed_agreement_pct": round(pct, 2),
        "disagreements": disagreements,
    }


def format_comparison_report(
    comp_results: Dict[str, Any],
    rel_results: Dict[str, Any],
    file_a: Path,
    file_b: Path,
) -> str:
    lines: List[str] = [
        "=" * 72,
        "ARGUMAP Annotation Comparison Report (Double Annotation)",
        "=" * 72,
        f"Annotator A: {file_a.name}",
        f"Annotator B: {file_b.name}",
        "-" * 72,
        "COMPONENT ANNOTATION:",
        f"  Total Shared Units:      {comp_results['total_units']}",
        f"  Agreed Units:            {comp_results['agreed_units']}",
        f"  Disagreed Units:         {comp_results['disagreed_units']}",
        f"  Observed Agreement:      {comp_results['observed_agreement_pct']:.2f}%",
        "-" * 72,
        "RELATION ANNOTATION:",
        f"  Total Evaluated Pairs:   {rel_results['total_evaluated_pairs']}",
        f"  Agreed Pairs:            {rel_results['agreed_pairs']}",
        f"  Disagreed Pairs:         {rel_results['disagreed_pairs']}",
        f"  Observed Agreement:      {rel_results['observed_agreement_pct']:.2f}%",
        "=" * 72,
    ]

    if comp_results["disagreements"]:
        lines.append("\nCOMPONENT DISAGREEMENTS:")
        for d in comp_results["disagreements"]:
            lines.append(
                f"  [{d['unit_id']}] Speaker: {d['speaker_id']:<12} | "
                f"A: {d['annotator_A_label']:<15} vs B: {d['annotator_B_label']:<15}\n"
                f"    Text: \"{d['text'][:65]}...\""
            )

    if rel_results["disagreements"]:
        lines.append("\nRELATION DISAGREEMENTS:")
        for r in rel_results["disagreements"]:
            lines.append(
                f"  ({r['source_unit_id']} -> {r['target_unit_id']}) | "
                f"A: {r['annotator_A_label']:<12} vs B: {r['annotator_B_label']:<12} "
                f"(turn dist: {r['turn_distance']})"
            )

    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two ARGUMAP annotation files.")
    parser.add_argument("--annotator-a", "-a", type=Path, required=True, help="Annotation JSON from Annotator A.")
    parser.add_argument("--annotator-b", "-b", type=Path, required=True, help="Annotation JSON from Annotator B.")
    parser.add_argument("--output-json", "-o", type=Path, default=None, help="Optional output path for JSON report.")

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
    rels_a = data_a.get("relations", [])
    rels_b = data_b.get("relations", [])

    comp_cmp = compare_component_annotations(units_a, units_b)
    rel_cmp = compare_relation_annotations(rels_a, rels_b)

    report_text = format_comparison_report(comp_cmp, rel_cmp, args.annotator_a, args.annotator_b)
    print(report_text)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump({
                "component_comparison": comp_cmp,
                "relation_comparison": rel_cmp,
            }, f, indent=2)
        print(f"\nSaved structured comparison to: {args.output_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
