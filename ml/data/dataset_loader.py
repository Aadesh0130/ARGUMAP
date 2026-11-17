"""Dataset loader for ARGUMAP annotation format.

Loads annotated argument units from data/annotations/, validates labels
strictly against the frozen 6-class component taxonomy, and constructs
ArgumentUnitSample objects with debate-level metadata and contextual slots.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ml.data.label_encoder import FROZEN_COMPONENT_LABELS, validate_component_label


@dataclass
class ArgumentUnitSample:
    """Representation of an annotated argument proposition."""
    text: str
    component_label: str
    debate_id: str
    document_id: str
    speaker_id: str
    turn_id: str
    turn_index: int
    unit_id: str
    # Context-aware slots prepared for future iterations
    previous_unit: Optional[str] = None
    current_unit: Optional[str] = None
    next_unit: Optional[str] = None
    speaker: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.text or not isinstance(self.text, str) or not self.text.strip():
            raise ValueError(f"Argument unit text cannot be empty or whitespace (unit_id: '{self.unit_id}').")
        # Populate context defaults
        if self.current_unit is None:
            self.current_unit = self.text
        if self.speaker is None:
            self.speaker = self.speaker_id
        # Strict validation
        validate_component_label(self.component_label)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "component_label": self.component_label,
            "debate_id": self.debate_id,
            "document_id": self.document_id,
            "speaker_id": self.speaker_id,
            "turn_id": self.turn_id,
            "turn_index": self.turn_index,
            "unit_id": self.unit_id,
            "previous_unit": self.previous_unit,
            "current_unit": self.current_unit,
            "next_unit": self.next_unit,
            "speaker": self.speaker,
        }


def check_gold_dataset_readiness(
    annotations_dir: Path,
    manifest_path: Optional[Path] = None,
) -> Tuple[bool, str, List[Path]]:
    """Determine whether real ARGUMAP gold annotations are present and cleared for training.

    Rules:
    - Step 5 pilot demo annotations must NOT be treated as production gold data.
    - If data/annotations contains no production gold files, report NOT READY.
    - Candidate gold files must be cleared for training in dataset_manifest.json.
      Any unverified license or BLOCKED status halts model training under Prime Directive 7.

    Returns:
        (is_ready, reason_message, list_of_valid_file_paths)
    """
    if not annotations_dir.exists():
        return False, f"Directory '{annotations_dir}' does not exist.", []

    json_files = list(annotations_dir.glob("**/*.json"))
    # Filter out schemas
    candidate_files = [
        f for f in json_files
        if not f.name.endswith(".schema.json") and "schema" not in f.name.lower()
    ]

    # Exclude pilot demonstration and template files from gold data
    gold_files = [
        f for f in candidate_files
        if "pilot" not in f.parts
        and "demo" not in f.stem.lower()
        and "template" not in f.parts
        and "template" not in f.stem.lower()
    ]

    if not gold_files:
        return (
            False,
            "No production ARGUMAP gold annotations found. "
            "Existing files under data/annotations/pilot/ and data/annotations/templates/ are demonstration artifacts only (or unannotated templates).",
            [],
        )

    # Inspect candidate gold files for unverified licensing / training clearance
    m_path = manifest_path or (Path(__file__).resolve().parents[2] / "data" / "dataset_manifest.json")
    manifest_clearance: Dict[str, str] = {}
    if m_path.exists():
        try:
            with open(m_path, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
                for ds in mdata.get("datasets", []):
                    ds_id = ds.get("dataset_id")
                    if ds_id:
                        manifest_clearance[ds_id] = ds.get("training_clearance_status", "BLOCKED")
        except Exception:
            pass

    blocked_corpora = set()
    cleared_files: List[Path] = []

    for gf in gold_files:
        try:
            with open(gf, "r", encoding="utf-8") as f:
                d = json.load(f)
            src_lic = str(d.get("source_license", "")).upper()
            src_corpus = d.get("source_corpus")
            status = str(d.get("status", "")).upper()

            # Reject explicit templates or draft files
            if "TEMPLATE" in status or "DRAFT" in status or "template" in gf.stem.lower():
                blocked_corpora.add(f"{gf.stem} (unannotated template)")
                continue

            # Ensure units, if present, are not unannotated / null-labeled
            raw_units = d.get("units") or d.get("argument_units") or []
            unannotated_count = sum(
                1 for u in raw_units
                if not u.get("component_label") or u.get("component_label") not in FROZEN_COMPONENT_LABELS
            )
            if unannotated_count > 0:
                blocked_corpora.add(f"{gf.stem} ({unannotated_count} unannotated units)")
                continue

            # Check if file declares an unverified license
            if "UNVERIFIED" in src_lic:
                blocked_corpora.add(src_corpus or gf.stem)
            # Check against manifest training clearance if corpus is registered
            elif src_corpus and src_corpus in manifest_clearance and manifest_clearance[src_corpus] != "CLEARED":
                blocked_corpora.add(src_corpus)
            else:
                cleared_files.append(gf)
        except Exception:
            blocked_corpora.add(gf.stem)

    if blocked_corpora:
        blocked_list = ", ".join(sorted(list(blocked_corpora)))
        return (
            False,
            f"Model training blocked by dataset licensing gatekeeper: "
            f"Candidate gold files belong to unverified or blocked corpora [{blocked_list}]. "
            f"Under Prime Directive 7, model training is prohibited until licensing is cleared in dataset_manifest.json.",
            [],
        )

    return True, f"Found {len(cleared_files)} cleared production annotation files.", cleared_files


def load_argument_units_from_dict(
    data: Dict[str, Any],
    document_id: Optional[str] = None,
) -> List[ArgumentUnitSample]:
    """Parse argument units from a single annotation dictionary.

    Validates every unit against the frozen 6 labels. Fails loudly on invalid labels.
    """
    debate_id = str(data.get("debate_id", "unknown_debate"))
    doc_id = document_id or str(data.get("document_id", debate_id))

    raw_units = data.get("units") or data.get("argument_units") or []
    if not isinstance(raw_units, list):
        raise ValueError(f"Annotation file for debate '{debate_id}' has invalid units list.")

    samples: List[ArgumentUnitSample] = []
    num_units = len(raw_units)

    for i, u in enumerate(raw_units):
        text = u.get("unit_text") or u.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError(f"Missing or invalid text in unit '{u.get('unit_id')}'.")

        comp_label = u.get("component_label")
        if not comp_label:
            raise ValueError(f"Missing component_label in unit '{u.get('unit_id')}'.")

        # Context calculation (previous and next unit text within debate)
        prev_text = None
        if i > 0:
            prev_u = raw_units[i - 1]
            prev_text = prev_u.get("unit_text") or prev_u.get("text")

        next_text = None
        if i + 1 < num_units:
            next_u = raw_units[i + 1]
            next_text = next_u.get("unit_text") or next_u.get("text")

        speaker_id = str(u.get("speaker_id", "unknown_speaker"))
        turn_id = str(u.get("turn_id", f"turn_{u.get('turn_index', 0)}"))
        turn_index = int(u.get("turn_index", 0))
        unit_id = str(u.get("unit_id", f"u_{i:04d}"))

        sample = ArgumentUnitSample(
            text=text.strip(),
            component_label=str(comp_label).strip(),
            debate_id=str(u.get("debate_id", debate_id)),
            document_id=doc_id,
            speaker_id=speaker_id,
            turn_id=turn_id,
            turn_index=turn_index,
            unit_id=unit_id,
            previous_unit=prev_text.strip() if prev_text else None,
            current_unit=text.strip(),
            next_unit=next_text.strip() if next_text else None,
            speaker=speaker_id,
        )
        samples.append(sample)

    return samples


def load_argument_units(
    source_path: Path,
    include_pilot: bool = False,
) -> List[ArgumentUnitSample]:
    """Load argument units from a JSON file or directory of JSON files.

    Args:
        source_path: Path to a file or directory containing ARGUMAP annotations.
        include_pilot: If False, ignores files located in a 'pilot' directory.
                       Set to True only for demonstration or test fixtures.

    Returns:
        List of validated ArgumentUnitSample instances.

    Raises:
        ValueError: If any component label is invalid or files are corrupted.
        FileNotFoundError: If source_path does not exist.
    """
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    files: List[Path] = []
    if path.is_file():
        files = [path]
    else:
        for f in path.glob("**/*.json"):
            if f.name.endswith(".schema.json") or "schema" in f.name.lower():
                continue
            if not include_pilot and ("pilot" in f.parts or "demo" in f.stem.lower()):
                continue
            files.append(f)

    all_samples: List[ArgumentUnitSample] = []
    for json_file in sorted(files):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = load_argument_units_from_dict(data, document_id=json_file.stem)
        all_samples.extend(samples)

    return all_samples
