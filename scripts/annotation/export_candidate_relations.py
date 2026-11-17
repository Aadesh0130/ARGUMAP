"""ARGUMAP — Candidate Relation Pairs Full Exporter.

Exports all 1,260 candidate relation pairs for the UK Hansard AI debate pilot into:
`data/annotation/candidate_relations_full.json`

Requirements enforced:
1. Canonical text grounding: Source and target proposition texts are retrieved
   strictly from the canonical component-unit dataset (`data/processed/hansard_lords_ai_debate_2023.json`),
   not from repeated or cached text in annotation exports.
2. Structure & Metadata Preservation: Preserves unique pair IDs, directed edge ordering,
   cross-turn/intra-turn flags, turn distances, and out-of-window override flags/notes.
3. Complete Candidate Universe: Includes all 1,260 directed pairs (including both forward
   and reverse cross-turn and intra-turn directions).
4. Truthfulness: Strictly avoids inventing missing texts or artificial labels.
5. Referential Integrity: Validates that both unit IDs exist in the canonical dataset.
6. Validation & Reporting: Computes and reports total pair count, missing texts,
   duplicates, and invalid unit references.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CANONICAL_PATH = PROJECT_ROOT / "data" / "processed" / "hansard_lords_ai_debate_2023.json"
DEFAULT_PILOT_PATH = PROJECT_ROOT / "data" / "annotations" / "pilot" / "hansard_2023_pilot_annotator_A.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "annotation" / "candidate_relations_full.json"


def load_canonical_units(
    canonical_path: Path = DEFAULT_CANONICAL_PATH,
) -> Dict[str, Dict[str, Any]]:
    """Loads canonical units map from the processed dataset.

    Returns:
        Dict mapping unit_id -> canonical unit dictionary.
    """
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical dataset not found: {canonical_path}")

    with open(canonical_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    units_list = data.get("units", [])
    if not units_list:
        raise ValueError(f"No units found in canonical dataset {canonical_path}")

    canonical_map: Dict[str, Dict[str, Any]] = {}
    for u in units_list:
        uid = u.get("unit_id")
        if uid:
            canonical_map[uid] = u

    return canonical_map


def load_candidate_relation_pairs(
    pilot_path: Path = DEFAULT_PILOT_PATH,
) -> List[Dict[str, Any]]:
    """Loads candidate relations in their exact sequence from the pilot template."""
    if not pilot_path.exists():
        raise FileNotFoundError(f"Pilot template not found: {pilot_path}")

    with open(pilot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    relations = data.get("relations", [])
    if not relations:
        raise ValueError(f"No relations found in pilot package {pilot_path}")

    return relations


def export_candidate_relations(
    canonical_path: Path = DEFAULT_CANONICAL_PATH,
    pilot_path: Path = DEFAULT_PILOT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    dry_run: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Generates the complete 1,260 candidate relation export.

    Returns:
        (exported_pairs, audit_report)
    """
    canonical_units = load_canonical_units(canonical_path)
    raw_relations = load_candidate_relation_pairs(pilot_path)

    exported_pairs: List[Dict[str, Any]] = []
    seen_pair_ids: Set[str] = set()

    missing_source_texts = 0
    missing_target_texts = 0
    duplicate_pair_ids = 0
    invalid_unit_references = 0

    for idx, r in enumerate(raw_relations):
        s_id = r.get("source_unit_id")
        t_id = r.get("target_unit_id")

        # Referential validation
        s_unit = canonical_units.get(s_id) if s_id else None
        t_unit = canonical_units.get(t_id) if t_id else None

        if not s_id or not t_id or s_unit is None or t_unit is None:
            invalid_unit_references += 1

        pair_id = f"{s_id}->{t_id}" if (s_id and t_id) else f"unknown_pair_{idx}"
        if pair_id in seen_pair_ids:
            duplicate_pair_ids += 1
        seen_pair_ids.add(pair_id)

        # Canonical text resolution (strictly from canonical dataset text field)
        source_text = s_unit.get("text") if s_unit else None
        target_text = t_unit.get("text") if t_unit else None

        if source_text is None or not str(source_text).strip():
            missing_source_texts += 1
        if target_text is None or not str(target_text).strip():
            missing_target_texts += 1

        # Speaker & turn resolution
        source_speaker = s_unit.get("speaker_name") or s_unit.get("speaker_id") if s_unit else None
        source_speaker_id = s_unit.get("speaker_id") if s_unit else None
        target_speaker = t_unit.get("speaker_name") or t_unit.get("speaker_id") if t_unit else None
        target_speaker_id = t_unit.get("speaker_id") if t_unit else None

        source_turn = s_unit.get("turn_id") if s_unit else None
        source_turn_index = s_unit.get("turn_index") if s_unit else None
        target_turn = t_unit.get("turn_id") if t_unit else None
        target_turn_index = t_unit.get("turn_index") if t_unit else None

        # Overrides & notes
        is_override = bool(r.get("is_override", False))
        note = r.get("note")

        # Current annotation status & labels
        current_label = r.get("relation_label")
        annotation_status = "ANNOTATED" if current_label is not None else "UNANNOTATED"

        pair_entry: Dict[str, Any] = {
            "pair_id": pair_id,
            "source_unit_id": s_id,
            "source_text": source_text,
            "target_unit_id": t_id,
            "target_text": target_text,
            "source_speaker": source_speaker,
            "source_speaker_id": source_speaker_id,
            "target_speaker": target_speaker,
            "target_speaker_id": target_speaker_id,
            "source_turn": source_turn,
            "source_turn_index": source_turn_index,
            "target_turn": target_turn,
            "target_turn_index": target_turn_index,
            "is_override": is_override,
            "notes": note,
            "note": note,
            "annotation_status": annotation_status,
            "label": current_label,
            "relation_label": current_label,
            "same_speaker": r.get("same_speaker"),
            "cross_turn": r.get("cross_turn"),
            "turn_distance": r.get("turn_distance"),
            "confidence": r.get("confidence"),
            "annotator_id": r.get("annotator_id"),
            "guideline_version": r.get("guideline_version", "1.1.0"),
        }

        exported_pairs.append(pair_entry)

    total_pairs = len(exported_pairs)

    report = {
        "output_path": str(output_path.resolve()),
        "total_pairs": total_pairs,
        "missing_source_texts": missing_source_texts,
        "missing_target_texts": missing_target_texts,
        "duplicate_pair_ids": duplicate_pair_ids,
        "invalid_unit_references": invalid_unit_references,
        "unique_pair_ids": len(seen_pair_ids),
        "override_pairs_count": sum(1 for p in exported_pairs if p["is_override"]),
        "unannotated_pairs_count": sum(1 for p in exported_pairs if p["annotation_status"] == "UNANNOTATED"),
        "annotated_pairs_count": sum(1 for p in exported_pairs if p["annotation_status"] == "ANNOTATED"),
        "dry_run": dry_run,
    }

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        tmp_path = output_path.with_suffix(".tmp.json")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(exported_pairs, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, output_path)

    return exported_pairs, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ARGUMAP candidate relation pairs to JSON.")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_PATH), help="Target output JSON path.")
    parser.add_argument("--canonical", type=str, default=str(DEFAULT_CANONICAL_PATH), help="Canonical dataset path.")
    parser.add_argument("--pilot", type=str, default=str(DEFAULT_PILOT_PATH), help="Pilot template path.")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation without writing file.")
    args = parser.parse_args()

    out_p = Path(args.output)
    canon_p = Path(args.canonical)
    pilot_p = Path(args.pilot)

    pairs, report = export_candidate_relations(
        canonical_path=canon_p,
        pilot_path=pilot_p,
        output_path=out_p,
        dry_run=args.dry_run,
    )

    print("=" * 60)
    print("ARGUMAP CANDIDATE RELATIONS EXPORT SUMMARY")
    print("=" * 60)
    print(f"Output File:             {report['output_path']}")
    print(f"Total Pair Count:        {report['total_pairs']}")
    print(f"Missing Source Texts:    {report['missing_source_texts']}")
    print(f"Missing Target Texts:    {report['missing_target_texts']}")
    print(f"Duplicate Pair IDs:      {report['duplicate_pair_ids']}")
    print(f"Invalid Unit References: {report['invalid_unit_references']}")
    print(f"Override Pairs Count:    {report['override_pairs_count']}")
    print(f"Unannotated Pairs:       {report['unannotated_pairs_count']}")
    print(f"Annotated Pairs:         {report['annotated_pairs_count']}")
    print("=" * 60)

    # Validation assertions
    if report["total_pairs"] != 1260:
        sys.exit(f"Error: Expected 1,260 pairs, got {report['total_pairs']}")
    if report["missing_source_texts"] > 0:
        sys.exit(f"Error: Detected {report['missing_source_texts']} missing source texts")
    if report["missing_target_texts"] > 0:
        sys.exit(f"Error: Detected {report['missing_target_texts']} missing target texts")
    if report["duplicate_pair_ids"] > 0:
        sys.exit(f"Error: Detected {report['duplicate_pair_ids']} duplicate pair IDs")
    if report["invalid_unit_references"] > 0:
        sys.exit(f"Error: Detected {report['invalid_unit_references']} invalid unit references")

    print("Validation SUCCESS: All candidate relations verified against canonical units.")


if __name__ == "__main__":
    main()
