"""Tests for AI-Assisted Provisional Annotation Workflow.

Verifies:
1. Revalidation of input invariants and fail-safe error handling
2. Strict protection and immutability of candidate_relations_full.json
3. Schema preservation and isolation of human gold fields from AI suggestions
4. Complete coverage of all four frozen relation labels (SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION)
5. Robust handling of malformed model responses and invalid labels
6. Checkpointing and resume behavior across interrupted batch executions
7. Retry handling and transient failure recovery
8. Reverse-pair disagreement reporting without forcing artificial symmetry
9. Separate metric tracking for override vs standard candidate pairs
"""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotation.ai_provisional_annotator import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    AI_REVIEW_STATUS_PROVISIONAL,
    AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW,
    AI_REVIEW_STATUS_PENDING,
    AI_REVIEW_STATUS_ERROR,
    CONFIDENCE_HUMAN_REVIEW_THRESHOLD,
    AIProvisionalPipeline,
    InputValidationError,
    MockModelProvider,
    PredictionResult,
    UnconfiguredQueueProvider,
    validate_input_dataset,
)


@pytest.fixture(scope="module")
def input_dataset():
    assert DEFAULT_INPUT_PATH.exists()
    with open(DEFAULT_INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def provisional_dataset():
    assert DEFAULT_OUTPUT_PATH.exists()
    with open(DEFAULT_OUTPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestInputValidationAndProtection:
    """Verifies input validation invariants and protection of the original file."""

    def test_original_input_validation_passes(self, input_dataset):
        is_valid, errors = validate_input_dataset(input_dataset, expected_count=1260)
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_protection_of_original_file(self):
        """Verifies candidate_relations_full.json is strictly read-only and never modified."""
        with open(DEFAULT_INPUT_PATH, "rb") as f:
            original_bytes = f.read()
        original_hash = hashlib.sha256(original_bytes).hexdigest()

        # Run pipeline in a temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_out = Path(tmp_dir) / "test_out.json"
            pipeline = AIProvisionalPipeline(
                input_path=DEFAULT_INPUT_PATH,
                output_path=temp_out,
                provider=UnconfiguredQueueProvider(),
            )
            pipeline.run()

        # Verify hash of candidate_relations_full.json has not changed
        with open(DEFAULT_INPUT_PATH, "rb") as f:
            post_bytes = f.read()
        post_hash = hashlib.sha256(post_bytes).hexdigest()

        assert original_hash == post_hash, "Original candidate_relations_full.json was modified!"

    def test_input_validation_fails_on_wrong_count(self, input_dataset):
        corrupted = copy.deepcopy(input_dataset[:-1])  # 1259 records
        is_valid, errors = validate_input_dataset(corrupted, expected_count=1260)
        assert not is_valid
        assert any("Expected exactly 1260 records" in e for e in errors)

    def test_input_validation_fails_on_duplicate_pair_id(self, input_dataset):
        corrupted = copy.deepcopy(input_dataset)
        corrupted[1]["pair_id"] = corrupted[0]["pair_id"]
        is_valid, errors = validate_input_dataset(corrupted)
        assert not is_valid
        assert any("Duplicate pair_id" in e for e in errors)

    def test_input_validation_fails_on_self_loop(self, input_dataset):
        corrupted = copy.deepcopy(input_dataset)
        corrupted[0]["target_unit_id"] = corrupted[0]["source_unit_id"]
        is_valid, errors = validate_input_dataset(corrupted)
        assert not is_valid
        assert any("Self-referencing loop" in e for e in errors)

    def test_input_validation_fails_on_missing_reverse_pair(self, input_dataset):
        corrupted = copy.deepcopy(input_dataset)
        # Change second unit so pair's reverse no longer matches
        corrupted[0]["target_unit_id"] = "u_9999"
        is_valid, errors = validate_input_dataset(corrupted)
        assert not is_valid
        assert any("Missing reverse directed pair" in e for e in errors)

    def test_input_validation_fails_if_human_labels_not_null(self, input_dataset):
        corrupted = copy.deepcopy(input_dataset)
        corrupted[0]["label"] = "SUPPORTS"
        is_valid, errors = validate_input_dataset(corrupted)
        assert not is_valid
        assert any("Expected label to be null" in e for e in errors)


class TestSchemaPreservationAndFieldIsolation:
    """Verifies that all original fields are preserved and AI suggestions are isolated."""

    def test_record_count_and_pair_id_match(self, input_dataset, provisional_dataset):
        assert len(provisional_dataset) == len(input_dataset) == 1260
        for in_r, prov_r in zip(input_dataset, provisional_dataset):
            assert in_r["pair_id"] == prov_r["pair_id"]

    def test_original_fields_unaltered(self, input_dataset, provisional_dataset):
        original_keys = [
            "pair_id",
            "source_unit_id",
            "source_text",
            "target_unit_id",
            "target_text",
            "source_speaker",
            "target_speaker",
            "source_turn",
            "target_turn",
            "is_override",
            "notes",
            "note",
            "annotation_status",
            "label",
            "relation_label",
            "same_speaker",
            "cross_turn",
            "turn_distance",
            "confidence",
            "annotator_id",
            "guideline_version",
        ]
        for in_r, prov_r in zip(input_dataset, provisional_dataset):
            for k in original_keys:
                assert in_r[k] == prov_r[k], f"Field '{k}' altered in pair {in_r['pair_id']}"

    def test_human_fields_remain_unannotated(self, provisional_dataset):
        for r in provisional_dataset:
            assert r["label"] is None
            assert r["relation_label"] is None
            assert r["confidence"] is None
            assert r["annotation_status"] == "UNANNOTATED"

    def test_ai_provisional_fields_present(self, provisional_dataset):
        ai_keys = [
            "ai_suggested_label",
            "ai_rationale",
            "ai_confidence",
            "ai_review_status",
            "ai_model_or_method",
            "ai_annotation_version",
        ]
        for r in provisional_dataset:
            for k in ai_keys:
                assert k in r, f"Missing AI field '{k}' in pair {r.get('pair_id')}"


class TestClassificationAndProviders:
    """Verifies classification logic across all four frozen labels, errors, and mock engines."""

    def test_all_four_frozen_labels_supported(self, input_dataset):
        """Verifies that mock classification can output all 4 frozen relation labels."""
        custom_map = {
            input_dataset[0]["pair_id"]: ("SUPPORTS", 0.92, "Source justifies target claim", AI_REVIEW_STATUS_PROVISIONAL),
            input_dataset[1]["pair_id"]: ("ATTACKS", 0.88, "Source contradicts target premise", AI_REVIEW_STATUS_PROVISIONAL),
            input_dataset[2]["pair_id"]: ("RESPONDS_TO", 0.75, "Source addresses target inquiry", AI_REVIEW_STATUS_PROVISIONAL),
            input_dataset[3]["pair_id"]: ("NO_RELATION", 0.95, "Unrelated topical propositions", AI_REVIEW_STATUS_PROVISIONAL),
        }
        provider = MockModelProvider(custom_mapping=custom_map)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_in = Path(tmp_dir) / "in.json"
            temp_out = Path(tmp_dir) / "out.json"

            # Use 4-pair subset (plus their reverse pairs for structural completeness)
            test_subset = copy.deepcopy(input_dataset[:8])
            with open(temp_in, "w", encoding="utf-8") as f:
                json.dump(test_subset, f)

            pipeline = AIProvisionalPipeline(
                input_path=temp_in,
                output_path=temp_out,
                provider=provider,
                batch_size=4,
            )
            # Override load_and_validate to accept small test subset
            pipeline.load_and_validate_input = lambda: test_subset

            records, report = pipeline.run()

            assert records[0]["ai_suggested_label"] == "SUPPORTS"
            assert records[1]["ai_suggested_label"] == "ATTACKS"
            assert records[2]["ai_suggested_label"] == "RESPONDS_TO"
            assert records[3]["ai_suggested_label"] == "NO_RELATION"

            assert report["label_distribution"]["SUPPORTS"] >= 1
            assert report["label_distribution"]["ATTACKS"] >= 1
            assert report["label_distribution"]["RESPONDS_TO"] >= 1
            assert report["label_distribution"]["NO_RELATION"] >= 1

    def test_malformed_model_response_handling(self, input_dataset):
        """When provider returns an invalid label, item is marked for review and logged as error."""
        provider = MockModelProvider(simulate_malformed=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_in = Path(tmp_dir) / "in.json"
            temp_out = Path(tmp_dir) / "out.json"
            test_subset = copy.deepcopy(input_dataset[:4])
            with open(temp_in, "w", encoding="utf-8") as f:
                json.dump(test_subset, f)

            pipeline = AIProvisionalPipeline(
                input_path=temp_in,
                output_path=temp_out,
                provider=provider,
            )
            pipeline.load_and_validate_input = lambda: test_subset

            records, report = pipeline.run()

            for r in records:
                assert r["ai_suggested_label"] == "INVALID_LABEL_UNKNOWN"
                assert r["ai_review_status"] == AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW

            assert report["errors_count"] == 4

    def test_retry_handling_on_transient_failure(self, input_dataset):
        """Verifies that transient errors are retried up to max_retries and succeed."""
        provider = MockModelProvider(default_label="SUPPORTS", simulate_failure_count=2)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_in = Path(tmp_dir) / "in.json"
            temp_out = Path(tmp_dir) / "out.json"
            test_subset = copy.deepcopy(input_dataset[:2])

            pipeline = AIProvisionalPipeline(
                input_path=temp_in,
                output_path=temp_out,
                provider=provider,
                max_retries=3,
                retry_delay_seconds=0.01,
            )
            pipeline.load_and_validate_input = lambda: test_subset

            records, report = pipeline.run()

            assert records[0]["ai_suggested_label"] == "SUPPORTS"
            assert report["retries_count"] == 2
            assert report["errors_count"] == 0


class TestResumeAndBatchCheckpointing:
    """Verifies that processing can be paused and resumed cleanly without duplicate work."""

    def test_resume_from_partial_checkpoint(self, input_dataset):
        test_subset = copy.deepcopy(input_dataset[:6])

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_in = Path(tmp_dir) / "in.json"
            temp_out = Path(tmp_dir) / "out.json"

            # 1. First run with batch_size=2, but stopped after 2 items
            provider = MockModelProvider(default_label="NO_RELATION")
            pipeline_1 = AIProvisionalPipeline(
                input_path=temp_in,
                output_path=temp_out,
                provider=provider,
                batch_size=2,
            )
            pipeline_1.load_and_validate_input = lambda: test_subset

            # Manually run first 2 items
            initialized = pipeline_1.initialize_or_resume_output(test_subset)
            for idx in [0, 1]:
                res = provider.classify_pair(initialized[idx])
                initialized[idx]["ai_suggested_label"] = res.suggested_label
                initialized[idx]["ai_review_status"] = res.review_status
            pipeline_1._atomic_write(temp_out, initialized)

            # Verify checkpoint has 2 labeled and 4 pending
            with open(temp_out, "r", encoding="utf-8") as f:
                saved = json.load(f)
            assert sum(1 for r in saved if r["ai_suggested_label"] is not None) == 2
            assert sum(1 for r in saved if r["ai_suggested_label"] is None) == 4

            # 2. Second pipeline instance resumes
            pipeline_2 = AIProvisionalPipeline(
                input_path=temp_in,
                output_path=temp_out,
                provider=provider,
                batch_size=2,
            )
            pipeline_2.load_and_validate_input = lambda: test_subset

            resumed_records, report = pipeline_2.run()

            # All 6 should now be completed
            assert len(resumed_records) == 6
            assert all(r["ai_suggested_label"] == "NO_RELATION" for r in resumed_records)
            assert report["total_processed"] == 6
            assert report["total_remaining"] == 0


class TestDisagreementsAndPartitionStats:
    """Verifies reverse-pair disagreement reporting and partition statistics."""

    def test_reverse_disagreements_without_forcing_symmetry(self, input_dataset):
        """An earlier premise supporting a later claim vs later claim attacking premise."""
        p_forward = input_dataset[0]  # u_0010 -> u_0011
        p_reverse = next(
            p for p in input_dataset
            if p["source_unit_id"] == p_forward["target_unit_id"]
            and p["target_unit_id"] == p_forward["source_unit_id"]
        )

        custom_map = {
            p_forward["pair_id"]: ("SUPPORTS", 0.90, "Grounds supporting conclusion", AI_REVIEW_STATUS_PROVISIONAL),
            p_reverse["pair_id"]: ("RESPONDS_TO", 0.80, "Clarifying response", AI_REVIEW_STATUS_PROVISIONAL),
        }
        provider = MockModelProvider(custom_mapping=custom_map)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_in = Path(tmp_dir) / "in.json"
            temp_out = Path(tmp_dir) / "out.json"
            test_subset = [copy.deepcopy(p_forward), copy.deepcopy(p_reverse)]

            pipeline = AIProvisionalPipeline(
                input_path=temp_in,
                output_path=temp_out,
                provider=provider,
            )
            pipeline.load_and_validate_input = lambda: test_subset

            records, report = pipeline.run()

            assert report["reverse_disagreements_count"] == 1
            disagreement = report["reverse_disagreements_sample"][0]
            assert disagreement["forward_label"] == "SUPPORTS"
            assert disagreement["reverse_label"] == "RESPONDS_TO"

    def test_override_vs_standard_partition_statistics(self, provisional_dataset):
        """Verifies exact split between 486 override candidates and 774 standard candidates."""
        override_count = sum(1 for p in provisional_dataset if p["is_override"])
        standard_count = sum(1 for p in provisional_dataset if not p["is_override"])

        assert override_count == 486
        assert standard_count == 774
        assert override_count + standard_count == 1260
