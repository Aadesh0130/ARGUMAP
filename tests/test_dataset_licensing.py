"""Tests for ARGUMAP dataset licensing, provenance, and training gatekeeper.

Verifies:
1. Strict schema compliance of data/dataset_manifest.json with training clearance fields.
2. Flagging of UK Hansard pilot text as UNVERIFIED/BLOCKED due to synthetic/adapted dialogue
   (Dr. Sarah Wollaston was not an MP in 2024; verbatim text absent from official Hansard).
3. Flagging of Kennedy-Nixon 1960 transcript as UNVERIFIED/BLOCKED (campaign debates and commercial
   network broadcasts are not U.S. Government works under 17 U.S.C. § 105; text is adapted).
4. Preservation of US2016 as UNVERIFIED/BLOCKED (CPD proprietary rights; fair use limited to local annotation).
5. Strict blocking of NoDerivatives (ND) datasets (ElecDeb60To20).
6. Raw file integrity and SHA-256 provenance against data/raw/provenance.json.
7. Training gatekeeper enforcement: model training is strictly blocked unless datasets are explicitly
   CLEARED with verified primary evidence, rejecting blind reliance on license-name strings.
"""

import json
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset.validate_dataset_manifest import validate_manifest


@pytest.fixture
def manifest_data():
    manifest_path = PROJECT_ROOT / "data" / "dataset_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def provenance_data():
    prov_path = PROJECT_ROOT / "data" / "raw" / "provenance.json"
    with open(prov_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestDatasetLicensingAudit:
    """Tests for dataset provenance, rights analysis, and training clearance."""

    def test_manifest_is_valid_after_clearance_audit(self):
        manifest_path = PROJECT_ROOT / "data" / "dataset_manifest.json"
        is_valid, errors, warnings = validate_manifest(manifest_path)
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_uk_hansard_flagged_unverified_and_blocked(self, manifest_data):
        """Verify UK Hansard pilot text is not blindly trusted as OPL v3.0."""
        ds = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "uk_hansard"), None)
        assert ds is not None, "uk_hansard entry missing from manifest"
        assert ds["license_status"] == "UNVERIFIED"
        assert ds["training_clearance_status"] == "BLOCKED"
        assert "Wollaston" in ds["training_clearance_reason"]
        assert "parliament.uk" in ds["source"]

    def test_kennedy_nixon_flagged_unverified_and_blocked(self, manifest_data):
        """Verify Kennedy-Nixon is not blindly assumed to be 17 U.S.C. § 105 public domain."""
        ds = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "kennedy_nixon_1960"), None)
        assert ds is not None, "kennedy_nixon_1960 entry missing from manifest"
        assert ds["license_status"] == "UNVERIFIED"
        assert ds["training_clearance_status"] == "BLOCKED"
        assert "17 U.S.C." in ds["training_clearance_reason"]
        assert "senate.gov" in ds["source"]

    def test_us2016_licensing_remains_unverified_and_blocked(self, manifest_data):
        """Verify US2016 remains UNVERIFIED and BLOCKED due to CPD rights."""
        ds = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "us2016"), None)
        assert ds is not None, "us2016 entry missing from manifest"
        assert ds["license_status"] == "UNVERIFIED"
        assert ds["training_clearance_status"] == "BLOCKED"
        assert "CPD" in ds["notes"]
        assert "fair use" in ds["notes"].lower()

    def test_elecdeb60to20_noderivatives_blocked(self, manifest_data):
        """Verify ElecDeb60To20 is flagged with NoDerivatives and blocked from model training."""
        ds = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "elecdeb60to20"), None)
        assert ds is not None
        assert ds["license"] == "CC BY-NC-ND 4.0"
        assert ds["training_clearance_status"] == "BLOCKED"
        assert "NoDerivatives" in ds["training_clearance_reason"] or "ND" in ds["training_clearance_reason"]

    def test_provenance_checksums_and_paths(self, provenance_data):
        """Verify that all raw provenance files exist with matching SHA-256."""
        import hashlib
        for doc in provenance_data["documents"]:
            local_path = PROJECT_ROOT / doc["local_path"]
            assert local_path.exists(), f"Raw file missing: {local_path}"
            hasher = hashlib.sha256()
            with open(local_path, "rb") as f:
                hasher.update(f.read())
            calculated = hasher.hexdigest()
            assert calculated == doc["checksum_sha256"], (
                f"Checksum mismatch for {doc['document_id']}: expected {doc['checksum_sha256']}, got {calculated}"
            )

    def test_model_training_gatekeeper_blocks_all_pilot_datasets(self, manifest_data):
        """Ensure training gatekeeper verifies explicit clearance states, not license strings alone."""
        pilot_dataset_ids = {"uk_hansard", "kennedy_nixon_1960", "us2016"}
        pilot_datasets = [d for d in manifest_data["datasets"] if d["dataset_id"] in pilot_dataset_ids]
        assert len(pilot_datasets) == 3, "Expected exactly 3 pilot datasets"

        # Check explicit training_clearance_status
        for ds in pilot_datasets:
            ds_id = ds["dataset_id"]
            clearance = ds.get("training_clearance_status")
            assert clearance == "BLOCKED", (
                f"Pilot dataset {ds_id} must have training_clearance_status 'BLOCKED', got '{clearance}'"
            )

        # Gatekeeper rule: Can train only if every active dataset is explicitly CLEARED with evidence
        cleared_pilot = [
            d["dataset_id"] for d in pilot_datasets
            if d.get("training_clearance_status") == "CLEARED"
            and d.get("license_status") == "VERIFIED"
            and d.get("training_clearance_evidence")
        ]
        assert len(cleared_pilot) == 0, "No pilot dataset is cleared for model training"

    def test_uk_hansard_lords_2023_provenance_and_clearance(self, manifest_data, provenance_data):
        """Verify that uk_hansard_lords_2023 has verified provenance, OPL v3.0 license, and matching checksum."""
        # Manifest check
        ds = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "uk_hansard_lords_2023"), None)
        assert ds is not None, "uk_hansard_lords_2023 entry missing from manifest"
        assert ds["license_status"] == "VERIFIED"
        assert ds["training_clearance_status"] == "CLEARED"
        assert ds["license"] == "Open Parliament Licence v3.0"
        assert "5432715E-F305-4EC1-8A79-B9A0C6402BFF" in ds["source"]
        assert ds.get("attribution") == "Contains Parliamentary information licensed under the Open Parliament Licence v3.0."

        # Provenance check
        doc = next((d for d in provenance_data["documents"] if d["document_id"] == "hansard_lords_ai_debate_2023"), None)
        assert doc is not None, "hansard_lords_ai_debate_2023 missing from provenance.json"
        assert doc["license_status"] == "VERIFIED"
        assert doc["source_license"] == "Open Parliament Licence v3.0"
        assert doc["turn_count"] == 29
        assert doc["speaker_count"] == 28

        local_path = PROJECT_ROOT / doc["local_path"]
        assert local_path.exists(), f"Raw file missing: {local_path}"

    def test_source_separation_distinguishes_authentic_from_legacy_synthetic(self, manifest_data, provenance_data):
        """Ensure clean separation between legacy synthetic pilot and authentic Hansard transcript."""
        legacy_manifest = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "uk_hansard"), None)
        authentic_manifest = next((d for d in manifest_data["datasets"] if d["dataset_id"] == "uk_hansard_lords_2023"), None)
        assert legacy_manifest is not None and authentic_manifest is not None

        # Verify strict separation of clearance states
        assert legacy_manifest["training_clearance_status"] == "BLOCKED"
        assert legacy_manifest["license_status"] == "UNVERIFIED"
        assert authentic_manifest["training_clearance_status"] == "CLEARED"
        assert authentic_manifest["license_status"] == "VERIFIED"

        # Verify legacy raw file is preserved
        legacy_doc = next((d for d in provenance_data["documents"] if d["document_id"] == "uk_hansard_ai_debate_2024"), None)
        assert legacy_doc is not None
        assert (PROJECT_ROOT / legacy_doc["local_path"]).exists()

    def test_annotation_integrity_and_legacy_archive(self):
        """Verify that legacy synthetic annotations are archived and cannot contaminate training."""
        legacy_dir = PROJECT_ROOT / "data" / "annotations" / "legacy_synthetic"
        assert legacy_dir.exists(), "Legacy synthetic archive directory missing"
        assert (legacy_dir / "debate_001_annotator_A.json").exists()
        assert (legacy_dir / "debate_001_annotator_B.json").exists()
        assert (legacy_dir / "debate_001_gold.json").exists()
        assert (legacy_dir / "README.md").exists()

        # Gold directory must contain zero cleared files for uk_hansard_lords_2023
        gold_dir = PROJECT_ROOT / "data" / "annotations" / "gold"
        lords_gold = list(gold_dir.glob("*lords*"))
        assert len(lords_gold) == 0, "No gold annotation file should exist for uk_hansard_lords_2023 yet"

    def test_training_gatekeeper_blocks_training_until_gold_annotations_validated(self):
        """Verify check_gold_dataset_readiness continues to block training until gold annotations exist."""
        from ml.data.dataset_loader import check_gold_dataset_readiness
        is_ready, reason, files = check_gold_dataset_readiness(PROJECT_ROOT / "data" / "annotations")
        assert not is_ready
        assert "blocked" in reason.lower() or "no production" in reason.lower()

    def test_gatekeeper_rejects_nominal_license_strings_without_evidence(self, tmp_path):
        """Ensure gatekeeper rejects datasets that nominal claim 'Public Domain' without clearance evidence."""
        mock_manifest = {
            "schema_version": "1.0.0",
            "datasets": [
                {
                    "dataset_id": "nominal_pd",
                    "name": "Nominal Public Domain",
                    "source": "https://archive.org/example",
                    "paper": "Unknown (1960)",
                    "year": 1960,
                    "domain": "Historical Debate",
                    "component_labels": ["Claim"],
                    "relation_labels": ["Support"],
                    "speaker_information": True,
                    "dialogue_structure": "Debate",
                    "license": "Public Domain",
                    "license_status": "VERIFIED",
                    "download_status": "DOWNLOADED",
                    "training_clearance_status": "CLEARED",  # Illegally set without evidence
                    "training_clearance_evidence": "",  # Empty evidence!
                    "intended_use": "Test",
                    "notes": "Testing gatekeeper",
                }
            ],
        }
        p = tmp_path / "mock_manifest.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(mock_manifest, f)

        is_valid, errors, _ = validate_manifest(p)
        assert not is_valid
        assert any("requires non-empty 'training_clearance_evidence'" in e for e in errors)

