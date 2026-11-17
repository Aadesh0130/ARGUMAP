"""ARGUMAP Human Annotation CLI Interface.

Allows a human annotator to:
1. Load a preprocessed debate transcript.
2. Navigate speech turns and speaker metadata.
3. Assign discrete component labels (CLAIM, PREMISE, EVIDENCE, COUNTERARGUMENT, REBUTTAL, OTHER).
4. Record confidence and rationale notes.
5. Annotate directed relations (SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION) across candidate pairs.
6. Save and resume progress deterministically.

STRICT CONSTRAINTS:
- No AI pre-labeling.
- No automatic prediction suggestions.
- Strict frozen taxonomy validation.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data.label_encoder import (
    FROZEN_COMPONENT_LABELS,
    validate_component_label,
)

FROZEN_RELATION_LABELS = [
    "SUPPORTS",
    "ATTACKS",
    "RESPONDS_TO",
    "NO_RELATION",
]


def validate_relation_label(label: str) -> None:
    if label not in FROZEN_RELATION_LABELS:
        allowed = ", ".join(FROZEN_RELATION_LABELS)
        raise ValueError(f"Invalid relation label '{label}'. Allowed: [{allowed}].")


class AnnotationSession:
    """Manages state, interactive inputs, and serialization for human annotation."""

    def __init__(
        self,
        transcript_data: Dict[str, Any],
        annotator_id: str,
        guideline_version: str = "1.0.0",
        candidate_window_k: int = 4,
    ) -> None:
        self.debate_id = transcript_data.get("debate_id") or transcript_data.get("document_id", "unknown_debate")
        self.title = transcript_data.get("title", f"Debate {self.debate_id}")
        self.source_corpus = transcript_data.get("source_corpus", "custom")
        self.source_license = transcript_data.get("source_license", "UNVERIFIED")
        self.annotator_id = annotator_id
        self.guideline_version = guideline_version
        self.candidate_window_k = candidate_window_k

        # Load raw units
        raw_units = transcript_data.get("units") or transcript_data.get("argument_units") or []
        self.units: List[Dict[str, Any]] = [dict(u) for u in raw_units]
        self.relations: List[Dict[str, Any]] = [
            dict(r) for r in transcript_data.get("relations", [])
        ]

    @classmethod
    def from_file(
        cls,
        filepath: Path,
        annotator_id: str,
        guideline_version: str = "1.0.0",
        candidate_window_k: int = 4,
    ) -> "AnnotationSession":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            transcript_data=data,
            annotator_id=annotator_id,
            guideline_version=guideline_version,
            candidate_window_k=candidate_window_k,
        )

    def set_unit_annotation(
        self,
        unit_index: int,
        component_label: str,
        confidence: float = 1.0,
        note: Optional[str] = None,
    ) -> None:
        """Assign human label to argument unit."""
        if not (0 <= unit_index < len(self.units)):
            raise IndexError(f"Unit index {unit_index} out of range (total {len(self.units)}).")

        validate_component_label(component_label)
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0 (got {confidence}).")

        u = self.units[unit_index]
        u["component_label"] = component_label
        u["annotator_id"] = self.annotator_id
        u["confidence"] = round(confidence, 4)
        u["note"] = note
        u["guideline_version"] = self.guideline_version

    def add_relation_annotation(
        self,
        source_unit_id: str,
        target_unit_id: str,
        relation_label: str,
        confidence: float = 1.0,
        note: Optional[str] = None,
    ) -> None:
        """Assign human relation label between two argument units."""
        validate_relation_label(relation_label)
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0 (got {confidence}).")
        if source_unit_id == target_unit_id:
            raise ValueError("Self-referencing loops are strictly prohibited.")

        # Find unit metadata
        unit_map = {u["unit_id"]: u for u in self.units}
        if source_unit_id not in unit_map or target_unit_id not in unit_map:
            raise KeyError(f"Source '{source_unit_id}' or Target '{target_unit_id}' not found.")

        src = unit_map[source_unit_id]
        tgt = unit_map[target_unit_id]

        same_speaker = bool(src.get("speaker_id") == tgt.get("speaker_id"))
        cross_turn = bool(src.get("turn_index") != tgt.get("turn_index"))
        turn_dist = abs(int(src.get("turn_index", 0)) - int(tgt.get("turn_index", 0)))

        # Update or append relation
        existing = None
        for r in self.relations:
            if r["source_unit_id"] == source_unit_id and r["target_unit_id"] == target_unit_id:
                existing = r
                break

        rel_data = {
            "source_unit_id": source_unit_id,
            "target_unit_id": target_unit_id,
            "relation_label": relation_label,
            "same_speaker": same_speaker,
            "cross_turn": cross_turn,
            "turn_distance": turn_dist,
            "annotator_id": self.annotator_id,
            "confidence": round(confidence, 4),
            "note": note,
            "guideline_version": self.guideline_version,
        }

        if existing:
            existing.update(rel_data)
        else:
            self.relations.append(rel_data)

    def generate_candidate_pairs(self) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Generate viable candidate pairs respecting turn-distance window k."""
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for i, src in enumerate(self.units):
            for j, tgt in enumerate(self.units):
                if i == j:
                    continue
                turn_dist = abs(int(src.get("turn_index", 0)) - int(tgt.get("turn_index", 0)))
                if turn_dist <= self.candidate_window_k:
                    pairs.append((src, tgt))
        return pairs

    def to_dict(self) -> Dict[str, Any]:
        """Export serialized annotation structure matching schema."""
        return {
            "debate_id": self.debate_id,
            "title": self.title,
            "source_corpus": self.source_corpus,
            "source_license": self.source_license,
            "guideline_version": self.guideline_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "annotator_id": self.annotator_id,
            "units": self.units,
            "relations": self.relations,
        }

    def save(self, filepath: Path) -> None:
        """Persist annotations to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="ARGUMAP Human Annotation Tool")
    parser.add_argument("--input-file", "-i", type=Path, required=True, help="Input preprocessed debate JSON.")
    parser.add_argument("--output-file", "-o", type=Path, required=True, help="Output annotation JSON file.")
    parser.add_argument("--annotator-id", "-a", type=str, required=True, help="Annotator identifier (e.g. annotator_A).")
    parser.add_argument("--candidate-window", type=int, default=4, help="Turn distance window k for candidate relations.")
    parser.add_argument("--non-interactive", action="store_true", help="Non-interactive status check mode.")

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"Error: Input file '{args.input_file}' not found.", file=sys.stderr)
        return 1

    session = AnnotationSession.from_file(
        filepath=args.input_file,
        annotator_id=args.annotator_id,
        candidate_window_k=args.candidate_window,
    )

    if args.non_interactive:
        total_units = len(session.units)
        annotated_units = sum(1 for u in session.units if u.get("component_label"))
        print(f"Debate ID: {session.debate_id}")
        print(f"Total Units: {total_units} | Annotated Units: {annotated_units}")
        print(f"Total Annotated Relations: {len(session.relations)}")
        return 0

    print("=" * 68)
    print(f"ARGUMAP Annotation Interface — Debate: {session.debate_id}")
    print(f"Annotator: {session.annotator_id} | Candidate Window k: {args.candidate_window}")
    print("=" * 68)
    print("\n[Commands: 'q' = Save and Quit, 's' = Skip, '1'..'6' = Assign Component Label]")
    print(f"Labels: 1:CLAIM, 2:PREMISE, 3:EVIDENCE, 4:COUNTERARGUMENT, 5:REBUTTAL, 6:OTHER\n")

    for idx, u in enumerate(session.units):
        current_lbl = u.get("component_label")
        status_tag = f"[{current_lbl}]" if current_lbl else "[UNLABELED]"
        print(f"\n--- Unit {idx + 1}/{len(session.units)} {status_tag} ---")
        print(f"Speaker:    {u.get('speaker_id')} (Turn {u.get('turn_index')})")
        print(f"Text:       \"{u.get('unit_text') or u.get('text')}\"")

        choice = input("Select component label (1-6, 's' to skip, 'q' to save/quit): ").strip()
        if choice.lower() == "q":
            session.save(args.output_file)
            print(f"\nProgress saved to {args.output_file}. Exiting.")
            return 0
        elif choice.lower() == "s":
            continue

        label_map = {
            "1": "CLAIM",
            "2": "PREMISE",
            "3": "EVIDENCE",
            "4": "COUNTERARGUMENT",
            "5": "REBUTTAL",
            "6": "OTHER",
        }
        if choice in label_map:
            lbl = label_map[choice]
            note = input("Optional note (press Enter to skip): ").strip() or None
            session.set_unit_annotation(idx, lbl, confidence=1.0, note=note)
            print(f"Assigned: {lbl}")
        else:
            print("Invalid input, skipping.")

    session.save(args.output_file)
    print(f"\nAll units processed. Saved to {args.output_file}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
