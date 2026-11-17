#!/usr/bin/env python3
"""Dataset Manifest Validator for ARGUMAP.

Validates data/dataset_manifest.json against structure, field completeness,
provenance tracking, and strict license verification rules.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple


REQUIRED_TOP_LEVEL_FIELDS = ["schema_version", "datasets"]
REQUIRED_DATASET_FIELDS = [
    "dataset_id",
    "name",
    "source",
    "paper",
    "year",
    "domain",
    "component_labels",
    "relation_labels",
    "speaker_information",
    "dialogue_structure",
    "license",
    "license_status",
    "download_status",
    "intended_use",
    "notes",
]

ALLOWED_LICENSE_STATUSES = {"VERIFIED", "UNVERIFIED"}
ALLOWED_DOWNLOAD_STATUSES = {"NOT_DOWNLOADED", "DOWNLOADED", "UNAVAILABLE"}
ALLOWED_CLEARANCE_STATUSES = {"CLEARED", "BLOCKED", "REVIEW_REQUIRED"}


def validate_manifest(manifest_path: Path) -> Tuple[bool, List[str], List[str]]:
    """Validates the dataset manifest file.
    
    Returns:
        (is_valid, errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not manifest_path.exists():
        errors.append(f"Manifest file not found: {manifest_path}")
        return False, errors, warnings

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        errors.append(f"Failed to parse JSON in {manifest_path}: {e}")
        return False, errors, warnings

    if not isinstance(data, dict):
        errors.append(f"Manifest root must be a JSON object, got {type(data).__name__}.")
        return False, errors, warnings

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            errors.append(f"Missing required top-level field: '{field}'")

    datasets = data.get("datasets", [])
    if not isinstance(datasets, list):
        errors.append(f"Field 'datasets' must be a list, got {type(datasets).__name__}.")
        return False, errors, warnings

    if len(datasets) == 0:
        warnings.append("Manifest contains 0 registered datasets.")

    seen_ids = set()

    for idx, ds in enumerate(datasets):
        prefix = f"Dataset #{idx + 1}"
        if not isinstance(ds, dict):
            errors.append(f"{prefix}: Item must be a JSON object.")
            continue

        ds_id = ds.get("dataset_id")
        if ds_id:
            prefix = f"Dataset '{ds_id}'"
            if ds_id in seen_ids:
                errors.append(f"{prefix}: Duplicate dataset_id detected.")
            seen_ids.add(ds_id)
        else:
            errors.append(f"{prefix}: Missing required field 'dataset_id'.")

        for req_field in REQUIRED_DATASET_FIELDS:
            if req_field not in ds:
                errors.append(f"{prefix}: Missing required field '{req_field}'.")

        # License status check
        lic_status = ds.get("license_status")
        if lic_status not in ALLOWED_LICENSE_STATUSES:
            errors.append(
                f"{prefix}: Invalid license_status '{lic_status}'. Must be one of {ALLOWED_LICENSE_STATUSES}."
            )

        # Download status check
        dl_status = ds.get("download_status")
        if dl_status not in ALLOWED_DOWNLOAD_STATUSES:
            errors.append(
                f"{prefix}: Invalid download_status '{dl_status}'. Must be one of {ALLOWED_DOWNLOAD_STATUSES}."
            )

        # Training clearance check (evidence-backed training gatekeeper)
        clearance_status = ds.get("training_clearance_status")
        if clearance_status is not None:
            if clearance_status not in ALLOWED_CLEARANCE_STATUSES:
                errors.append(
                    f"{prefix}: Invalid training_clearance_status '{clearance_status}'. Must be one of {ALLOWED_CLEARANCE_STATUSES}."
                )
            if clearance_status == "CLEARED":
                if lic_status == "UNVERIFIED":
                    errors.append(
                        f"{prefix}: Cannot have training_clearance_status 'CLEARED' when license_status is 'UNVERIFIED'."
                    )
                if not ds.get("training_clearance_evidence"):
                    errors.append(
                        f"{prefix}: training_clearance_status 'CLEARED' requires non-empty 'training_clearance_evidence'."
                    )
                lic_str = str(ds.get("license", ""))
                if "ND" in lic_str or "NoDerivatives" in lic_str:
                    errors.append(
                        f"{prefix}: Datasets with NoDerivatives license restrictions cannot be CLEARED for model training."
                    )

        # Labels check
        comp_labels = ds.get("component_labels")
        if not isinstance(comp_labels, list) or len(comp_labels) == 0:
            errors.append(f"{prefix}: 'component_labels' must be a non-empty list.")

        rel_labels = ds.get("relation_labels")
        if not isinstance(rel_labels, list) or len(rel_labels) == 0:
            errors.append(f"{prefix}: 'relation_labels' must be a non-empty list.")

        # Speaker info check
        spk_info = ds.get("speaker_information")
        if not isinstance(spk_info, bool) and not isinstance(spk_info, str):
            errors.append(f"{prefix}: 'speaker_information' must be a boolean or descriptive string.")

        # Year check
        year = ds.get("year")
        if not isinstance(year, int) or year < 1950 or year > 2030:
            errors.append(f"{prefix}: 'year' must be a valid 4-digit integer between 1950 and 2030.")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def main() -> int:
    default_path = Path(__file__).resolve().parents[2] / "data" / "dataset_manifest.json"
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    print(f"=== Validating ARGUMAP Dataset Manifest: {manifest_path} ===")
    is_valid, errors, warnings = validate_manifest(manifest_path)

    for w in warnings:
        print(f"[WARN] {w}")

    if not is_valid:
        print(f"\nFAILED: {len(errors)} validation error(s) found:")
        for e in errors:
            print(f"  [ERROR] {e}")
        return 1

    print("\nSUCCESS: Dataset manifest is valid and strictly compliant with provenance requirements.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
