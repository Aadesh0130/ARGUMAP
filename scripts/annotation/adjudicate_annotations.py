"""Adjudicate annotations from two independent annotators into a unified Gold standard.

Rules:
- Where annotators agree: accepted automatically with status AGREED.
- Where annotators disagree: resolved by lead adjudicator, preserving complete provenance:
    annotator_A_label, annotator_B_label, final_label, adjudicator, adjudication_note.
- Validates the resulting gold annotation against the canonical ARGUMAP schema.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data.label_encoder import validate_component_label
from scripts.annotation.annotate import validate_relation_label


def adjudicate_debate(
    data_a: Dict[str, Any],
    data_b: Dict[str, Any],
    adjudicator_id: str,
    decisions: Optional[Dict[str, Any]] = None,
    guideline_version: str = "1.1.0",
) -> Dict[str, Any]:
    """Merge and adjudicate component and relation annotations into Gold format."""
    debate_id = data_a.get("debate_id") or data_b.get("debate_id", "unknown_debate")
    title = data_a.get("title", f"Gold Debate {debate_id}")
    source_corpus = data_a.get("source_corpus", "custom")
    source_license = data_a.get("source_license", "UNVERIFIED")

    units_a = {u["unit_id"]: u for u in (data_a.get("units") or data_a.get("argument_units", []))}
    units_b = {u["unit_id"]: u for u in (data_b.get("units") or data_b.get("argument_units", []))}

    if decisions and "cases" in decisions:
        unit_decisions = {}
        relation_decisions = {}
        for c in decisions.get("cases", []):
            if c.get("debate_id") == debate_id:
                uid = c.get("unit_id", "")
                if "->" in uid:
                    relation_decisions[uid] = {
                        "final_label": c.get("decision"),
                        "rationale": c.get("rationale"),
                        "confidence": 0.95,
                    }
                else:
                    unit_decisions[uid] = {
                        "final_label": c.get("decision"),
                        "rationale": c.get("rationale"),
                        "confidence": 0.95,
                    }
    else:
        unit_decisions = (decisions or {}).get("unit_decisions", {})
        relation_decisions = (decisions or {}).get("relation_decisions", {})

    gold_units: List[Dict[str, Any]] = []
    unit_agreements = 0
    unit_adjudications = 0

    all_uids = sorted(list(set(units_a.keys()) | set(units_b.keys())))

    for uid in all_uids:
        u_a = units_a.get(uid, {})
        u_b = units_b.get(uid, {})
        base_u = u_a if u_a else u_b

        lbl_a = u_a.get("component_label")
        lbl_b = u_b.get("component_label")

        if lbl_a == lbl_b and lbl_a is not None:
            final_label = lbl_a
            status = "AGREED"
            adj_note = "Annotators agreed."
            unit_agreements += 1
            confidence = 1.0
        else:
            unit_adjudications += 1
            status = "ADJUDICATED"
            # Look up decision or fall back to decision dictionary
            dec = unit_decisions.get(uid, {})
            if "final_label" in dec:
                final_label = dec["final_label"]
                adj_note = dec.get("rationale", f"Resolved discrepancy between {lbl_a} and {lbl_b}.")
                confidence = dec.get("confidence", 0.95)
            elif lbl_a:
                # Default fallback if unspecified: accept Annotator A with documented notice
                final_label = lbl_a
                adj_note = f"Default resolution: Accepted Annotator A ({lbl_a}) over Annotator B ({lbl_b})."
                confidence = 0.90
            else:
                final_label = lbl_b
                adj_note = f"Single annotator fallback: {lbl_b}."
                confidence = 0.90

        validate_component_label(final_label)

        gold_unit = {
            "debate_id": debate_id,
            "source_corpus": source_corpus,
            "source_license": source_license,
            "turn_id": base_u.get("turn_id", f"turn_{base_u.get('turn_index', 0)}"),
            "turn_index": int(base_u.get("turn_index", 0)),
            "speaker_id": base_u.get("speaker_id", "unknown"),
            "speaker_role": base_u.get("speaker_role", "Debater"),
            "speaker_side": base_u.get("speaker_side", "Neutral"),
            "unit_id": uid,
            "unit_text": base_u.get("unit_text") or base_u.get("text", ""),
            "char_start": int(base_u.get("char_start", 0)),
            "char_end": int(base_u.get("char_end", 0)),
            "component_label": final_label,
            "annotator_id": adjudicator_id,
            "confidence": confidence,
            "note": adj_note,
            "guideline_version": guideline_version,
            "adjudication_provenance": {
                "status": status,
                "annotator_A_label": lbl_a,
                "annotator_B_label": lbl_b,
                "annotator_A_note": u_a.get("note"),
                "annotator_B_note": u_b.get("note"),
            },
        }
        gold_units.append(gold_unit)

    # Adjudicate relations
    rels_a = {(r["source_unit_id"], r["target_unit_id"]): r for r in data_a.get("relations", [])}
    rels_b = {(r["source_unit_id"], r["target_unit_id"]): r for r in data_b.get("relations", [])}
    all_pairs = sorted(list(set(rels_a.keys()) | set(rels_b.keys())))

    gold_relations: List[Dict[str, Any]] = []
    rel_agreements = 0
    rel_adjudications = 0

    unit_map = {u["unit_id"]: u for u in gold_units}

    for pair in all_pairs:
        r_a = rels_a.get(pair)
        r_b = rels_b.get(pair)
        base_r = r_a if r_a else r_b

        lbl_a = r_a.get("relation_label", "NO_RELATION") if r_a else "NO_RELATION"
        lbl_b = r_b.get("relation_label", "NO_RELATION") if r_b else "NO_RELATION"

        pair_key = f"{pair[0]}->{pair[1]}"

        if lbl_a == lbl_b:
            final_rel = lbl_a
            status = "AGREED"
            adj_note = "Annotators agreed."
            rel_agreements += 1
            confidence = 1.0
        else:
            rel_adjudications += 1
            status = "ADJUDICATED"
            dec = relation_decisions.get(pair_key, {})
            if "final_label" in dec:
                final_rel = dec["final_label"]
                adj_note = dec.get("rationale", f"Resolved relation between {lbl_a} and {lbl_b}.")
                confidence = dec.get("confidence", 0.95)
            elif lbl_a != "NO_RELATION":
                final_rel = lbl_a
                adj_note = f"Default resolution: Accepted active link from Annotator A ({lbl_a})."
                confidence = 0.90
            else:
                final_rel = lbl_b
                adj_note = f"Default resolution: Accepted active link from Annotator B ({lbl_b})."
                confidence = 0.90

        validate_relation_label(final_rel)

        src = unit_map.get(pair[0], {})
        tgt = unit_map.get(pair[1], {})

        turn_dist = abs(int(src.get("turn_index", 0)) - int(tgt.get("turn_index", 0)))
        same_spk = bool(src.get("speaker_id") == tgt.get("speaker_id"))
        cross_trn = bool(src.get("turn_index") != tgt.get("turn_index"))

        # Skip trivial NO_RELATION pairs from gold graph to maintain clean edge files
        if final_rel == "NO_RELATION":
            continue

        gold_rel = {
            "source_unit_id": pair[0],
            "target_unit_id": pair[1],
            "relation_label": final_rel,
            "same_speaker": same_spk,
            "cross_turn": cross_trn,
            "turn_distance": turn_dist,
            "annotator_id": adjudicator_id,
            "confidence": confidence,
            "note": adj_note,
            "guideline_version": guideline_version,
            "adjudication_provenance": {
                "status": status,
                "annotator_A_label": lbl_a,
                "annotator_B_label": lbl_b,
            },
        }
        gold_relations.append(gold_rel)

    return {
        "debate_id": debate_id,
        "title": title,
        "source_corpus": source_corpus,
        "source_license": source_license,
        "guideline_version": guideline_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "adjudicator_id": adjudicator_id,
        "units": gold_units,
        "relations": gold_relations,
        "provenance_summary": {
            "total_units": len(gold_units),
            "unit_agreements": unit_agreements,
            "unit_adjudications": unit_adjudications,
            "unit_agreement_rate": round(unit_agreements / len(gold_units) * 100.0, 2) if gold_units else 0.0,
            "total_active_relations": len(gold_relations),
            "relation_agreements": rel_agreements,
            "relation_adjudications": rel_adjudications,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Adjudicate double-annotated files into Gold dataset.")
    parser.add_argument("--annotator-a", "-a", type=Path, required=True, help="Annotation JSON from Annotator A.")
    parser.add_argument("--annotator-b", "-b", type=Path, required=True, help="Annotation JSON from Annotator B.")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output path for Gold JSON annotation.")
    parser.add_argument("--adjudicator-id", type=str, default="lead_computational_linguist", help="Adjudicator ID.")
    parser.add_argument("--decisions-file", type=Path, default=None, help="Optional JSON file with adjudication decisions.")
    parser.add_argument("--guideline-version", type=str, default="1.1.0", help="Guideline version.")

    args = parser.parse_args()

    for p in (args.annotator_a, args.annotator_b):
        if not p.exists():
            print(f"Error: File '{p}' not found.", file=sys.stderr)
            return 1

    with open(args.annotator_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(args.annotator_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)

    decisions = None
    if args.decisions_file and args.decisions_file.exists():
        with open(args.decisions_file, "r", encoding="utf-8") as f:
            decisions = json.load(f)

    gold_data = adjudicate_debate(
        data_a=data_a,
        data_b=data_b,
        adjudicator_id=args.adjudicator_id,
        decisions=decisions,
        guideline_version=args.guideline_version,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(gold_data, f, indent=2, ensure_ascii=False)

    summary = gold_data["provenance_summary"]
    print("=" * 68)
    print("ARGUMAP Adjudication Completed -> Gold Standard Export")
    print("=" * 68)
    print(f"Debate ID:            {gold_data['debate_id']}")
    print(f"Total Gold Units:     {summary['total_units']}")
    print(f"Agreed Units:         {summary['unit_agreements']} ({summary['unit_agreement_rate']}%)")
    print(f"Adjudicated Units:    {summary['unit_adjudications']}")
    print(f"Active Relations:     {summary['total_active_relations']}")
    print(f"Saved Gold File:      {args.output}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
