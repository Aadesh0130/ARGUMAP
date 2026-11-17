#!/usr/bin/env python3
"""ARGUMAP — generate_pilot_package.py

Deterministic generator for the Human Annotation Pilot Package based on the
verified 2023 UK Parliament House of Lords AI debate transcript.

Selection Policy:
- Contiguous, salient opening exchanges across the first 3 turns:
  * Turn 1 (turn_001, Lord Ravensdale, turn_index 0): units u_0001 through u_0012 (12 units)
  * Turn 2 (turn_002, Baroness Stowell of Beeston, turn_index 1): units u_0064 through u_0075 (12 units)
  * Turn 3 (turn_003, Lord Browne of Ladyton, turn_index 2): units u_0089 through u_0100 (12 units)
- Total units: 36 units across 3 speakers and 3 speech turns.

Candidate-Pair Universe Policy (Provisional Directional k = 3):
- Intra-turn pairs (delta_turn == 0, source != target): Bidirectional (both u_i -> u_j and u_j -> u_i).
- Cross-turn pairs (1 <= delta_turn <= 3): Chronologically backward-directed only (source in later turn).
- Self-pairs (source == target): Prohibited and excluded.
- Forward cross-turn pairs (delta_turn < 0): Excluded.
- Out-of-window pairs (delta_turn > 3): Excluded from standard candidate universe.
  May only be introduced via explicit annotator override (is_override: true).
- Negative example interpretation: Omitted pairs are NEVER interpreted as NO_RELATION.
  Annotators must explicitly label every candidate pair.
- Total candidate pairs: 828 pairs (396 intra-turn, 432 cross-turn).

Outputs:
- data/annotations/pilot/hansard_2023_pilot_annotator_A.json
- data/annotations/pilot/hansard_2023_pilot_annotator_B.json
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "hansard_lords_ai_debate_2023.json"
PILOT_OUTPUT_DIR = PROJECT_ROOT / "data" / "annotations" / "pilot"

PILOT_UNIT_RANGES = {
    "turn_001": (10, 18),   # u_0010 - u_0018 (Lord Ravensdale: Frontier AI Risk Core)
    "turn_002": (64, 72),   # u_0064 - u_0072 (Baroness Stowell: Open-source & liability)
    "turn_003": (89, 97),   # u_0089 - u_0097 (Lord Browne: Military AI & Taskforce)
    "turn_028": (902, 910), # u_0902 - u_0910 (Viscount Camrose: Ministerial Response & Compute)
}


def get_pilot_target_unit_ids() -> Set[str]:
    """Returns the deterministic set of unit IDs selected for the pilot."""
    ids = set()
    for _, (start_idx, end_idx) in PILOT_UNIT_RANGES.items():
        for i in range(start_idx, end_idx + 1):
            ids.add(f"u_{i:04d}")
    return ids


def extract_pilot_units(processed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts and verifies the 36 pilot units from the processed Hansard dataset."""
    target_ids = get_pilot_target_unit_ids()
    extracted = [u for u in processed_data["units"] if u["unit_id"] in target_ids]
    
    # Sort deterministically by unit_id
    extracted.sort(key=lambda u: u["unit_id"])
    
    if len(extracted) != 36:
        raise ValueError(f"Expected exactly 36 pilot units, got {len(extracted)}")
    return extracted


def generate_candidate_relation_pairs(
    units: List[Dict[str, Any]], k: int = 3, annotator_id: str = "annotator_A"
) -> List[Dict[str, Any]]:
    """Generates the candidate-pair universe under approved Option B (Full Bidirectional across eligible turns).
    
    Candidate-Pair Policy:
    1. u_source != u_target (no self-loops).
    2. Bidirectional pairing across all eligible pilot turns (1,260 directed candidate pairs).
    3. delta_turn = turn_index(u_source) - turn_index(u_target).
    4. turn_dist = abs(delta_turn).
       - turn_dist <= k: standard candidate (is_override=False).
       - turn_dist > k: cross-debate ministerial response override candidate (is_override=True with note).
    """
    candidates: List[Dict[str, Any]] = []
    
    # Deterministic ordering by source unit_id then target unit_id
    sorted_units = sorted(units, key=lambda u: u["unit_id"])
    
    for s_u in sorted_units:
        s_id = s_u["unit_id"]
        s_turn_idx = s_u["turn_index"]
        s_spk = s_u["speaker_id"]
        s_turn_id = s_u["turn_id"]
        
        for t_u in sorted_units:
            t_id = t_u["unit_id"]
            if s_id == t_id:
                # Rule: Self-pairs strictly excluded
                continue
            
            t_turn_idx = t_u["turn_index"]
            t_spk = t_u["speaker_id"]
            t_turn_id = t_u["turn_id"]
            
            delta_turn = s_turn_idx - t_turn_idx
            turn_dist = abs(delta_turn)
            same_speaker = (s_spk == t_spk)
            cross_turn = (s_turn_id != t_turn_id)
            
            # Out-of-window links (turn_dist > k) require explicit override flag and justification
            if turn_dist > k:
                is_override = True
                note = "[PILOT_DIVERSITY_OVERRIDE] Cross-debate ministerial response candidate (Turn 28)"
            else:
                is_override = False
                note = None
            
            candidates.append({
                "source_unit_id": s_id,
                "target_unit_id": t_id,
                "relation_label": None,
                "same_speaker": same_speaker,
                "cross_turn": cross_turn,
                "turn_distance": turn_dist,
                "is_override": is_override,
                "annotator_id": annotator_id,
                "confidence": None,
                "note": note,
                "guideline_version": "1.1.0",
            })
                
    return candidates


def build_annotator_pilot_package(
    processed_data: Dict[str, Any], annotator_id: str
) -> Dict[str, Any]:
    """Assembles a complete, unannotated pilot package for an independent annotator."""
    pilot_units_raw = extract_pilot_units(processed_data)
    
    # Build unit entries with exact source grounding and empty labels
    formatted_units: List[Dict[str, Any]] = []
    for u in pilot_units_raw:
        formatted_units.append({
            "debate_id": "uk_hansard_lords_2023",
            "source_corpus": "uk_parliament_hansard",
            "source_license": "Open Parliament Licence v3.0",
            "turn_id": u["turn_id"],
            "turn_index": u["turn_index"],
            "speaker_id": u["speaker_id"],
            "speaker_role": "Debater",
            "speaker_side": "Neutral",
            "unit_id": u["unit_id"],
            "unit_text": u["text"],
            "char_start": u["char_start"],
            "char_end": u["char_end"],
            "component_label": None,
            "annotator_id": annotator_id,
            "confidence": None,
            "note": None,
            "guideline_version": "1.1.0",
        })

    candidates = generate_candidate_relation_pairs(
        formatted_units, k=3, annotator_id=annotator_id
    )

    package = {
        "debate_id": "uk_hansard_lords_2023",
        "title": "UK House of Lords: Advanced Artificial Intelligence Debate (24 July 2023) - Human Annotation Pilot Package",
        "source_corpus": "uk_parliament_hansard",
        "source_license": "Open Parliament Licence v3.0",
        "guideline_version": "1.1.0",
        "annotator_id": annotator_id,
        "status": "UNANNOTATED_PILOT_PACKAGE",
        "attribution": "Contains Parliamentary information licensed under the Open Parliament Licence v3.0.",
        "pilot_selection": {
            "method": "four_turn_dialectical_diversity",
            "description": (
                "Deterministic selection of 9 proposition units each from Turns 1, 2, 3, "
                "and Turn 28 representing the debate opener, primary interventions, and ministerial summing-up."
            ),
            "source_turns": ["turn_001", "turn_002", "turn_003", "turn_028"],
            "unit_ranges": {
                "turn_001": ["u_0010", "u_0018"],
                "turn_002": ["u_0064", "u_0072"],
                "turn_003": ["u_0089", "u_0097"],
                "turn_028": ["u_0902", "u_0910"],
            },
            "total_units": len(formatted_units),
            "total_candidates": len(candidates),
        },
        "candidate_relation_policy": {
            "policy_name": "approved_bidirectional_option_b",
            "window_k": 3,
            "cross_turn_rule": "bidirectional across pilot turns (turn_dist <= 3 standard, turn_dist > 3 override)",
            "intra_turn_rule": "bidirectional (source != target)",
            "self_pairs": "excluded",
            "forward_cross_turn": "included (bidirectional)",
            "out_of_window_policy": "explicit_override_only (is_override=True with note)",
            "negative_interpretation_rule": "omitted_pairs_are_NOT_no_relation",
        },
        "instructions": {
            "component_annotation": (
                "Assign each unit exactly one of the 6 frozen component labels: "
                "CLAIM, PREMISE, EVIDENCE, COUNTERARGUMENT, REBUTTAL, OTHER. "
                "Set confidence between 0.0 and 1.0. Do not leave component_label as null."
            ),
            "relation_annotation": (
                "For every candidate pair in the relations array, explicitly assign one of the 4 "
                "frozen relation labels: SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION. "
                "Set confidence between 0.0 and 1.0. Do not leave relation_label as null. "
                "Pairs without active rhetorical interaction must be explicitly tagged as NO_RELATION."
            ),
            "ambiguity_logging": (
                "When encountering dialectical ambiguity (e.g. CLAIM vs PREMISE, or ATTACKS vs RESPONDS_TO), "
                "consult ANNOTATION_GUIDELINES.md Section 5. Record any residual ambiguity in the 'note' "
                "field prefixed with '[AMBIGUITY]' to flag it for the lead adjudicator."
            ),
            "out_of_window_overrides": (
                "If an argument targets an earlier turn beyond the candidate window (k > 3), "
                "record a new relation item with is_override=True, source_unit_id, target_unit_id, "
                "relation_label, confidence, and explanatory note."
            ),
        },
        "units": formatted_units,
        "relations": candidates,
    }
    return package


def main() -> int:
    if not PROCESSED_DATA_PATH.exists():
        print(f"[ERROR] Processed transcript not found: {PROCESSED_DATA_PATH}")
        return 1

    with open(PROCESSED_DATA_PATH, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    PILOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate Annotator A and Annotator B packages
    for ann_id in ["annotator_A", "annotator_B"]:
        out_fp = PILOT_OUTPUT_DIR / f"hansard_2023_pilot_{ann_id}.json"
        package = build_annotator_pilot_package(processed_data, ann_id)
        
        with open(out_fp, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, ensure_ascii=False)
            f.write("\n")
        
        print(f"Generated {ann_id} pilot package: {out_fp}")
        print(f"  - Units: {len(package['units'])}")
        print(f"  - Candidate pairs: {len(package['relations'])}")

    print("\nPilot package generation completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
