"""ARGUMAP Human Annotation Workspace Session Manager.

Manages state persistence, validation, isolation, and safe export for
independent human annotators working on the Hansard AI debate pilot.

Guarantees:
1. Strict Annotator Isolation: Annotator A only accesses A's workspace; B only accesses B's.
2. Template Immutability: Original unannotated pilot packages are NEVER overwritten.
3. Safe Persistence: Working states are saved atomically to prevent corrupted files.
4. Validation & Completeness: Enforces frozen labels, override justifications, and completeness rules.
5. No Accidental Gold Promotion: Submissions are marked COMPLETED_INDEPENDENT_ANNOTATION and
   remain rejected by the model training gatekeeper until formal adjudication.
"""

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset.validate_annotations import (
    FROZEN_COMPONENT_LABELS,
    FROZEN_RELATION_LABELS,
    check_annotation_completeness,
    validate_annotation_data,
)
from ml.data.dataset_loader import check_gold_dataset_readiness

VALID_ANNOTATORS: Set[str] = {"annotator_A", "annotator_B"}


class WorkspaceSession:
    """Manages an active human annotation workspace session."""

    def __init__(
        self,
        annotator_id: str,
        workspace_dir: Optional[Path] = None,
        template_dir: Optional[Path] = None,
        submissions_dir: Optional[Path] = None,
    ) -> None:
        if annotator_id not in VALID_ANNOTATORS:
            raise ValueError(
                f"Invalid annotator_id '{annotator_id}'. Must be one of {sorted(list(VALID_ANNOTATORS))}."
            )

        self.annotator_id = annotator_id
        project_root = Path(__file__).resolve().parents[2]

        self.template_dir = template_dir or (project_root / "data" / "annotations" / "pilot")
        self.workspace_dir = workspace_dir or (self.template_dir / "workspace")
        self.submissions_dir = submissions_dir or (self.template_dir / "submissions")

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.submissions_dir.mkdir(parents=True, exist_ok=True)

        self.template_path = self.template_dir / f"hansard_2023_pilot_{annotator_id}.json"
        self.working_path = self.workspace_dir / f"hansard_2023_pilot_{annotator_id}.working.json"
        self.completed_path = self.submissions_dir / f"hansard_2023_pilot_{annotator_id}.completed.json"

        if not self.template_path.exists():
            raise FileNotFoundError(f"Original pilot template not found: {self.template_path}")

        # In-memory document
        self.data: Dict[str, Any] = self._load_initial_state()

        # Fast lookup indexes
        self._units_by_id: Dict[str, Dict[str, Any]] = {
            u["unit_id"]: u for u in self.data.get("units", [])
        }
        self._relations_by_pair: Dict[Tuple[str, str], Dict[str, Any]] = {
            (r["source_unit_id"], r["target_unit_id"]): r
            for r in self.data.get("relations", [])
        }

    def _load_initial_state(self) -> Dict[str, Any]:
        """Loads working copy if present, otherwise copies initial unannotated template."""
        if self.working_path.exists():
            with open(self.working_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Integrity check: annotator ID in file must match session
            file_annotator = loaded.get("annotator_id")
            if file_annotator != self.annotator_id:
                raise ValueError(
                    f"Integrity violation: working file contains '{file_annotator}', expected '{self.annotator_id}'."
                )
            return loaded

        # Initialize from template without modifying template
        with open(self.template_path, "r", encoding="utf-8") as f:
            initial = json.load(f)

        file_annotator = initial.get("annotator_id")
        if file_annotator != self.annotator_id:
            raise ValueError(
                f"Integrity violation: template file contains '{file_annotator}', expected '{self.annotator_id}'."
            )

        # Mark as in-progress or unannotated
        initial["status"] = "IN_PROGRESS"
        # Atomically write the new working copy
        self._atomic_write(self.working_path, initial)
        return initial

    def _atomic_write(self, target_path: Path, doc: Dict[str, Any]) -> None:
        """Atomically writes JSON document to prevent corrupted files."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path_str = tempfile.mkstemp(
            dir=target_path.parent, prefix="annot_tmp_", suffix=".json"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
                f.write("\n")
            # Replace target atomically
            os.replace(tmp_path_str, target_path)
        except Exception:
            if os.path.exists(tmp_path_str):
                os.remove(tmp_path_str)
            raise

    def save_working_copy(self) -> Path:
        """Persists current state to the working copy file."""
        # Update status according to current progress
        stats = self.get_summary()
        if stats["is_complete"]:
            self.data["status"] = "READY_FOR_EXPORT"
        elif stats["labeled_units"] > 0 or stats["labeled_relations"] > 0:
            self.data["status"] = "IN_PROGRESS"
        else:
            self.data["status"] = "UNANNOTATED_PILOT_PACKAGE"

        self._atomic_write(self.working_path, self.data)
        return self.working_path

    def get_summary(self) -> Dict[str, Any]:
        """Calculates current annotation counts, progress percentages, and status."""
        units = self.data.get("units", [])
        relations = self.data.get("relations", [])

        labeled_units = sum(
            1 for u in units if u.get("component_label") in FROZEN_COMPONENT_LABELS
        )
        total_units = len(units)

        labeled_relations = sum(
            1 for r in relations if r.get("relation_label") in FROZEN_RELATION_LABELS
        )
        total_relations = len(relations)

        is_complete = (labeled_units == total_units) and (labeled_relations == total_relations)

        # Label distributions
        comp_dist: Dict[str, int] = {lbl: 0 for lbl in sorted(list(FROZEN_COMPONENT_LABELS))}
        for u in units:
            lbl = u.get("component_label")
            if lbl in comp_dist:
                comp_dist[lbl] += 1

        rel_dist: Dict[str, int] = {lbl: 0 for lbl in sorted(list(FROZEN_RELATION_LABELS))}
        for r in relations:
            lbl = r.get("relation_label")
            if lbl in rel_dist:
                rel_dist[lbl] += 1

        override_count = sum(1 for r in relations if r.get("is_override", False))

        return {
            "annotator_id": self.annotator_id,
            "status": self.data.get("status", "IN_PROGRESS"),
            "total_units": total_units,
            "labeled_units": labeled_units,
            "unit_progress_pct": round((labeled_units / total_units * 100), 1) if total_units else 0.0,
            "total_relations": total_relations,
            "labeled_relations": labeled_relations,
            "relation_progress_pct": round((labeled_relations / total_relations * 100), 1) if total_relations else 0.0,
            "total_items": total_units + total_relations,
            "labeled_items": labeled_units + labeled_relations,
            "total_progress_pct": round(((labeled_units + labeled_relations) / (total_units + total_relations) * 100), 1)
            if (total_units + total_relations)
            else 0.0,
            "is_complete": is_complete,
            "component_distribution": comp_dist,
            "relation_distribution": rel_dist,
            "override_count": override_count,
            "working_file": str(self.working_path),
            "template_file": str(self.template_path),
            "completed_file": str(self.completed_path),
        }

    def get_units(self) -> List[Dict[str, Any]]:
        """Returns all units with their current annotation values."""
        return self.data.get("units", [])

    def get_unit(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single unit by ID."""
        return self._units_by_id.get(unit_id)

    def update_unit(
        self,
        unit_id: str,
        label: Optional[str],
        confidence: Optional[float] = 1.0,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates a unit's component label, confidence score, and notes."""
        if unit_id not in self._units_by_id:
            raise KeyError(f"Unit ID '{unit_id}' not found in pilot units.")

        if label is not None and label not in FROZEN_COMPONENT_LABELS:
            raise ValueError(
                f"Invalid component label '{label}'. Must be one of {sorted(list(FROZEN_COMPONENT_LABELS))}."
            )

        if confidence is not None:
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                raise ValueError(f"Confidence must be a float between 0.0 and 1.0, got {confidence}.")

        unit = self._units_by_id[unit_id]
        unit["component_label"] = label
        unit["confidence"] = confidence if label is not None else None
        unit["note"] = note if note and note.strip() else None
        unit["annotator_id"] = self.annotator_id

        # Persist automatically
        self.save_working_copy()
        return unit

    def get_relations(
        self,
        filter_mode: str = "all",
        offset: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Returns paginated relations with source and target context."""
        relations = self.data.get("relations", [])

        if filter_mode == "unannotated":
            filtered = [r for r in relations if r.get("relation_label") is None]
        elif filter_mode == "labeled":
            filtered = [r for r in relations if r.get("relation_label") in FROZEN_RELATION_LABELS]
        elif filter_mode == "overrides":
            filtered = [r for r in relations if r.get("is_override", False)]
        elif filter_mode == "cross_turn":
            filtered = [r for r in relations if r.get("cross_turn", False)]
        elif filter_mode == "intra_turn":
            filtered = [r for r in relations if not r.get("cross_turn", False)]
        else:
            filtered = relations

        total_filtered = len(filtered)
        paginated = filtered[offset : offset + limit]

        # Enrich items with source and target texts for visualization
        enriched: List[Dict[str, Any]] = []
        for r in paginated:
            src = self._units_by_id.get(r["source_unit_id"], {})
            tgt = self._units_by_id.get(r["target_unit_id"], {})
            item = copy.deepcopy(r)
            item["source_text"] = src.get("unit_text", "")
            item["source_speaker"] = src.get("speaker_id", "")
            item["source_turn"] = src.get("turn_id", "")
            item["target_text"] = tgt.get("unit_text", "")
            item["target_speaker"] = tgt.get("speaker_id", "")
            item["target_turn"] = tgt.get("turn_id", "")
            enriched.append(item)

        return {
            "total": total_filtered,
            "offset": offset,
            "limit": limit,
            "filter_mode": filter_mode,
            "items": enriched,
        }

    def get_relation(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single candidate pair by (source, target) IDs."""
        pair = (source_id, target_id)
        if pair not in self._relations_by_pair:
            return None
        r = self._relations_by_pair[pair]
        src = self._units_by_id.get(source_id, {})
        tgt = self._units_by_id.get(target_id, {})
        res = copy.deepcopy(r)
        res["source_text"] = src.get("unit_text", "")
        res["source_speaker"] = src.get("speaker_id", "")
        res["source_turn"] = src.get("turn_id", "")
        res["target_text"] = tgt.get("unit_text", "")
        res["target_speaker"] = tgt.get("speaker_id", "")
        res["target_turn"] = tgt.get("turn_id", "")
        return res

    def update_relation(
        self,
        source_id: str,
        target_id: str,
        label: Optional[str],
        confidence: Optional[float] = 1.0,
        note: Optional[str] = None,
        is_override: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Updates a candidate relation's label, confidence score, and override notes."""
        pair = (source_id, target_id)
        if pair not in self._relations_by_pair:
            raise KeyError(f"Candidate pair ({source_id} -> {target_id}) does not exist.")

        if label is not None and label not in FROZEN_RELATION_LABELS:
            raise ValueError(
                f"Invalid relation label '{label}'. Must be one of {sorted(list(FROZEN_RELATION_LABELS))}."
            )

        if confidence is not None:
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                raise ValueError(f"Confidence must be a float between 0.0 and 1.0, got {confidence}.")

        rel = self._relations_by_pair[pair]
        rel["relation_label"] = label
        rel["confidence"] = confidence if label is not None else None
        rel["annotator_id"] = self.annotator_id

        if is_override is not None:
            rel["is_override"] = bool(is_override)

        # If it is an out-of-window link (turn_distance > 3), enforce override requirements
        if rel.get("turn_distance", 0) > 3:
            rel["is_override"] = True
            # If a note is provided, it cannot be empty; if not provided, existing note cannot be empty
            effective_note = note if note is not None else rel.get("note")
            if not effective_note or not str(effective_note).strip():
                raise ValueError(
                    f"Candidate relation ({source_id} -> {target_id}) has turn_distance > 3 "
                    "and requires an explanatory override note justification."
                )
            rel["note"] = str(effective_note).strip()
        else:
            if note is not None:
                rel["note"] = note.strip() if note.strip() else None

        self.save_working_copy()
        return rel

    def validate_session(self) -> Dict[str, Any]:
        """Validates current session state against ARGUMAP schema and completeness criteria."""
        is_valid_syntax, errors, warnings = validate_annotation_data(
            self.data, allow_unannotated=True
        )
        is_complete, missing_items = check_annotation_completeness(self.data)

        # Check completeness under production rules
        prod_valid, prod_errors, _ = validate_annotation_data(
            self.data, allow_unannotated=False
        )

        return {
            "syntax_valid": is_valid_syntax,
            "syntax_errors": errors,
            "warnings": warnings,
            "is_complete": is_complete,
            "missing_items": missing_items,
            "production_valid": prod_valid and is_complete,
            "production_errors": prod_errors,
        }

    def export_completed_package(self) -> Tuple[bool, str, Optional[Path]]:
        """Exports the fully labeled package to the submissions directory.

        Fails if any unit or candidate pair is unannotated.
        """
        validation = self.validate_session()
        if not validation["is_complete"]:
            return (
                False,
                f"Cannot export: Package is incomplete ({len(validation['missing_items'])} items unannotated).",
                None,
            )

        if not validation["production_valid"]:
            return (
                False,
                f"Cannot export: Package failed production validation: {validation['production_errors']}",
                None,
            )

        export_doc = copy.deepcopy(self.data)
        export_doc["status"] = "COMPLETED_INDEPENDENT_ANNOTATION"
        self._atomic_write(self.completed_path, export_doc)

        return True, f"Successfully exported to {self.completed_path}", self.completed_path
