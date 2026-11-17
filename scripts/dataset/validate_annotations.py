#!/usr/bin/env python3
"""Annotation Validator for ARGUMAP.

Validates human annotation JSON files against the frozen V1 component taxonomy,
frozen relation taxonomy, character offset bounds, entity integrity, and schema constraints.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set


FROZEN_COMPONENT_LABELS = {
    "CLAIM",
    "PREMISE",
    "EVIDENCE",
    "COUNTERARGUMENT",
    "REBUTTAL",
    "OTHER",
}

FROZEN_RELATION_LABELS = {
    "SUPPORTS",
    "ATTACKS",
    "RESPONDS_TO",
    "NO_RELATION",
}

REQUIRED_DOC_FIELDS = [
    "debate_id",
    "title",
    "source_corpus",
    "source_license",
    "guideline_version",
    "units",
    "relations",
]

REQUIRED_UNIT_FIELDS = [
    "debate_id",
    "source_corpus",
    "source_license",
    "turn_id",
    "turn_index",
    "speaker_id",
    "unit_id",
    "unit_text",
    "char_start",
    "char_end",
    "component_label",
    "annotator_id",
    "confidence",
    "guideline_version",
]

REQUIRED_RELATION_FIELDS = [
    "source_unit_id",
    "target_unit_id",
    "relation_label",
    "same_speaker",
    "cross_turn",
    "turn_distance",
    "annotator_id",
    "confidence",
    "guideline_version",
]


def validate_annotation_data(
    data: Dict[str, Any], allow_unannotated: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """Validates in-memory annotation dictionary.
    
    Args:
        data: Annotation document dictionary.
        allow_unannotated: If True, permits component_label and relation_label to be None
                          (for unannotated pilot packages and templates).
                          If False (default), strictly requires non-null frozen labels.
    
    Returns:
        (is_valid, errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(data, dict):
        errors.append(f"Root document must be a JSON object, got {type(data).__name__}.")
        return False, errors, warnings

    for req_f in REQUIRED_DOC_FIELDS:
        if req_f not in data:
            errors.append(f"Missing required root field: '{req_f}'")

    units = data.get("units", [])
    if not isinstance(units, list):
        errors.append(f"Field 'units' must be a list, got {type(units).__name__}.")
        return False, errors, warnings

    relations = data.get("relations", [])
    if not isinstance(relations, list):
        errors.append(f"Field 'relations' must be a list, got {type(relations).__name__}.")
        return False, errors, warnings

    # Validate Units
    unit_ids: Set[str] = set()
    unit_map: Dict[str, Dict[str, Any]] = {}

    for idx, unit in enumerate(units):
        prefix = f"Unit #{idx + 1}"
        if not isinstance(unit, dict):
            errors.append(f"{prefix}: Item must be a JSON object.")
            continue

        u_id = unit.get("unit_id")
        if u_id:
            prefix = f"Unit '{u_id}'"
            if u_id in unit_ids:
                errors.append(f"{prefix}: Duplicate unit_id detected.")
            unit_ids.add(u_id)
            unit_map[u_id] = unit
        else:
            errors.append(f"{prefix}: Missing required field 'unit_id'.")

        for req_u in REQUIRED_UNIT_FIELDS:
            if req_u not in unit:
                errors.append(f"{prefix}: Missing required field '{req_u}'.")

        # Label check
        label = unit.get("component_label")
        if allow_unannotated and label is None:
            # Valid unannotated template/package state
            pass
        elif label not in FROZEN_COMPONENT_LABELS:
            errors.append(
                f"{prefix}: Invalid component_label '{label}'. "
                f"Must be one of {sorted(list(FROZEN_COMPONENT_LABELS))}."
            )

        # Offset check
        start = unit.get("char_start")
        end = unit.get("char_end")
        if isinstance(start, int) and isinstance(end, int):
            if start < 0:
                errors.append(f"{prefix}: char_start must be >= 0, got {start}.")
            if end <= start:
                errors.append(
                    f"{prefix}: char_end ({end}) must be strictly greater than char_start ({start})."
                )
        else:
            if not isinstance(start, int):
                errors.append(f"{prefix}: char_start must be an integer.")
            if not isinstance(end, int):
                errors.append(f"{prefix}: char_end must be an integer.")

        # Text check
        text = unit.get("unit_text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{prefix}: unit_text must be a non-empty string.")

        # Confidence check
        conf = unit.get("confidence")
        if allow_unannotated and label is None and conf is None:
            # Valid unannotated state
            pass
        elif isinstance(conf, (int, float)):
            if conf < 0.0 or conf > 1.0:
                errors.append(f"{prefix}: confidence must be between 0.0 and 1.0, got {conf}.")
        else:
            errors.append(f"{prefix}: confidence must be a numeric float/int, got {type(conf).__name__}.")

    # Validate Relations
    seen_relation_pairs: Set[Tuple[str, str]] = set()

    for idx, rel in enumerate(relations):
        prefix = f"Relation #{idx + 1}"
        if not isinstance(rel, dict):
            errors.append(f"{prefix}: Item must be a JSON object.")
            continue

        for req_r in REQUIRED_RELATION_FIELDS:
            if req_r not in rel:
                errors.append(f"{prefix}: Missing required field '{req_r}'.")

        src_id = rel.get("source_unit_id")
        tgt_id = rel.get("target_unit_id")

        if src_id and tgt_id:
            prefix = f"Relation ({src_id} -> {tgt_id})"
            if (src_id, tgt_id) in seen_relation_pairs:
                warnings.append(f"{prefix}: Duplicate directed edge pair detected in relations list.")
            seen_relation_pairs.add((src_id, tgt_id))

            if src_id == tgt_id:
                errors.append(f"{prefix}: Self-referencing relations (loops) are prohibited.")

            # Nonexistent unit reference check
            if src_id not in unit_ids:
                errors.append(f"{prefix}: source_unit_id '{src_id}' does not exist in units list.")
            if tgt_id not in unit_ids:
                errors.append(f"{prefix}: target_unit_id '{tgt_id}' does not exist in units list.")

            # Semantic consistency checks if both units exist
            if src_id in unit_map and tgt_id in unit_map:
                u_src = unit_map[src_id]
                u_tgt = unit_map[tgt_id]

                actual_same_spk = (u_src.get("speaker_id") == u_tgt.get("speaker_id"))
                reported_same_spk = rel.get("same_speaker")
                if reported_same_spk is not None and reported_same_spk != actual_same_spk:
                    warnings.append(
                        f"{prefix}: 'same_speaker' reported as {reported_same_spk}, "
                        f"but actual speaker match is {actual_same_spk}."
                    )

                actual_turn_dist = abs(u_src.get("turn_index", 0) - u_tgt.get("turn_index", 0))
                reported_turn_dist = rel.get("turn_distance")
                if reported_turn_dist is not None and reported_turn_dist != actual_turn_dist:
                    warnings.append(
                        f"{prefix}: 'turn_distance' reported as {reported_turn_dist}, "
                        f"expected {actual_turn_dist}."
                    )

                # Check out-of-window link requirements
                is_override = rel.get("is_override", False)
                if actual_turn_dist > 3:
                    if not is_override:
                        warnings.append(
                            f"{prefix}: Out-of-window relation (turn_distance={actual_turn_dist} > 3) "
                            f"is not flagged with 'is_override: true'."
                        )
                    note = rel.get("note")
                    if not note or not str(note).strip():
                        warnings.append(
                            f"{prefix}: Out-of-window override should include an explanatory 'note' justification."
                        )

        # Label check
        rel_label = rel.get("relation_label")
        if allow_unannotated and rel_label is None:
            # Valid unannotated candidate pair state
            pass
        elif rel_label not in FROZEN_RELATION_LABELS:
            errors.append(
                f"{prefix}: Invalid relation_label '{rel_label}'. "
                f"Must be one of {sorted(list(FROZEN_RELATION_LABELS))}."
            )

        # Confidence check
        conf = rel.get("confidence")
        if allow_unannotated and rel_label is None and conf is None:
            # Valid unannotated state
            pass
        elif isinstance(conf, (int, float)):
            if conf < 0.0 or conf > 1.0:
                errors.append(f"{prefix}: confidence must be between 0.0 and 1.0, got {conf}.")
        else:
            errors.append(f"{prefix}: confidence must be a numeric float/int, got {type(conf).__name__}.")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def check_candidate_pair_coverage(
    data: Dict[str, Any], expected_candidate_pairs: Set[Tuple[str, str]]
) -> Tuple[bool, List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Verifies that all expected candidate pairs are explicitly present.
    
    Args:
        data: Annotation document dictionary.
        expected_candidate_pairs: Set of (source_unit_id, target_unit_id) tuples.
        
    Returns:
        (is_covered, missing_pairs, extra_pairs)
    """
    relations = data.get("relations", [])
    present_pairs = {(r.get("source_unit_id"), r.get("target_unit_id")) for r in relations}

    missing = sorted(list(expected_candidate_pairs - present_pairs))
    extra = sorted(list(present_pairs - expected_candidate_pairs))

    is_covered = len(missing) == 0
    return is_covered, missing, extra


def check_annotation_completeness(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Checks whether an annotation package has been fully labeled.
    
    Returns:
        (is_complete, missing_reasons)
        is_complete is True only when every unit has a non-null component_label in
        FROZEN_COMPONENT_LABELS and every candidate relation has a non-null relation_label
        in FROZEN_RELATION_LABELS.
    """
    missing: List[str] = []
    units = data.get("units", [])
    for u in units:
        lbl = u.get("component_label")
        if not lbl or lbl not in FROZEN_COMPONENT_LABELS:
            missing.append(f"Unit '{u.get('unit_id')}': missing component_label (got {lbl!r})")

    relations = data.get("relations", [])
    for r in relations:
        src = r.get("source_unit_id")
        tgt = r.get("target_unit_id")
        lbl = r.get("relation_label")
        if not lbl or lbl not in FROZEN_RELATION_LABELS:
            missing.append(f"Candidate relation ({src} -> {tgt}): missing relation_label (got {lbl!r})")

    return len(missing) == 0, missing


def validate_annotation_file(
    file_path: Path, allow_unannotated: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """Validates an annotation file on disk."""
    if not file_path.exists():
        return False, [f"File not found: {file_path}"], []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"JSON decode error in {file_path}: {e}"], []

    return validate_annotation_data(data, allow_unannotated=allow_unannotated)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python validate_annotations.py <path_to_annotation.json>")
        return 1

    target_path = Path(sys.argv[1])
    print(f"=== Validating ARGUMAP Annotation File: {target_path} ===")

    is_valid, errors, warnings = validate_annotation_file(target_path)

    for w in warnings:
        print(f"[WARN] {w}")

    if not is_valid:
        print(f"\nFAILED: {len(errors)} validation error(s) found:")
        for e in errors:
            print(f"  [ERROR] {e}")
        return 1

    print("\nSUCCESS: Annotation file passed all syntactic, semantic, and relational validation checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
