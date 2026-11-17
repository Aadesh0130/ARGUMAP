"""Unit and integration tests for ARGUMAP Task 1: Component Classification.

Tests strictly enforce:
- Frozen 6-class component taxonomy
- Rejection of invalid labels (no silent repair)
- Debate-level grouped non-leaking splitting
- Data distribution and evaluation metrics with frozen label ordering
- Deterministic TF-IDF baseline training and serialization
- Transformer dataset and module initialization on CPU (without network downloads)
- Graceful halting with status BLOCKED when real gold dataset is absent
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List
import numpy as np
import pytest
import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.config import (
    DatasetSplitConfig,
    ExperimentRecord,
    TFIDFConfig,
    TransformerConfig,
    get_available_device,
)
from ml.data.label_encoder import (
    FROZEN_COMPONENT_LABELS,
    ComponentLabelEncoder,
    validate_component_label,
)
from ml.data.dataset_loader import (
    ArgumentUnitSample,
    check_gold_dataset_readiness,
    load_argument_units,
    load_argument_units_from_dict,
)
from ml.data.dataset_splitter import DebateLevelSplitter, DatasetSplits
from ml.preprocessing.text_features import TFIDFFeatureExtractor
from ml.baseline.tfidf_classifier import TFIDFBaselineClassifier
from ml.baseline.train_baseline import run_baseline_training
from ml.transformer.dataset import ArgumentUnitDataset
from ml.transformer.classifier import ArgumentComponentTransformer
from ml.transformer.train import compute_class_weights, run_transformer_training
from ml.evaluation.metrics import (
    compute_class_distribution,
    compute_component_metrics,
)
from ml.evaluation.reports import (
    format_dataset_distribution_report,
    format_metrics_report,
)


# --- 1. Label Encoder & Taxonomy Tests ---


def test_label_encoder_strict_frozen_labels() -> None:
    encoder = ComponentLabelEncoder()
    assert encoder.get_labels() == [
        "CLAIM",
        "PREMISE",
        "EVIDENCE",
        "COUNTERARGUMENT",
        "REBUTTAL",
        "OTHER",
    ]
    assert encoder.num_classes == 6

    # Test bidirectional encoding
    for idx, lbl in enumerate(FROZEN_COMPONENT_LABELS):
        assert encoder.encode(lbl) == idx
        assert encoder.decode(idx) == lbl

    batch_encoded = encoder.encode_batch(["CLAIM", "PREMISE", "OTHER"])
    assert batch_encoded == [0, 1, 5]
    assert encoder.decode_batch([0, 1, 5]) == ["CLAIM", "PREMISE", "OTHER"]


def test_label_encoder_rejects_invalid_labels() -> None:
    encoder = ComponentLabelEncoder()
    invalid_labels = [
        "MAJOR_CLAIM",
        "SUPPORT",
        "WARRANT",
        "claim",  # lowercase must fail
        "UNKNOWN",
        "",
        "OTHER_LABEL",
    ]
    for inv in invalid_labels:
        with pytest.raises(ValueError, match="Invalid argument component label"):
            encoder.encode(inv)

        with pytest.raises(ValueError, match="Invalid argument component label"):
            validate_component_label(inv)

    with pytest.raises(ValueError, match="Invalid label ID"):
        encoder.decode(999)


def test_argument_unit_sample_validates_label() -> None:
    # Valid sample
    sample = ArgumentUnitSample(
        text="Carbon pricing directly reduces industrial emissions.",
        component_label="CLAIM",
        debate_id="debate_01",
        document_id="doc_01",
        speaker_id="Alice",
        turn_id="turn_1",
        turn_index=0,
        unit_id="u_01",
    )
    assert sample.component_label == "CLAIM"
    assert sample.current_unit == sample.text
    assert sample.speaker == "Alice"

    # Invalid label fails loudly
    with pytest.raises(ValueError, match="Invalid argument component label"):
        ArgumentUnitSample(
            text="Invalid premise.",
            component_label="INVALID_LABEL",
            debate_id="debate_01",
            document_id="doc_01",
            speaker_id="Alice",
            turn_id="turn_1",
            turn_index=0,
            unit_id="u_02",
        )

    # Empty or whitespace-only text fails loudly
    with pytest.raises(ValueError, match="cannot be empty or whitespace"):
        ArgumentUnitSample(
            text="   ",
            component_label="CLAIM",
            debate_id="debate_01",
            document_id="doc_01",
            speaker_id="Alice",
            turn_id="turn_1",
            turn_index=0,
            unit_id="u_03",
        )


# --- 2. Dataset Loader Tests ---


def test_dataset_loader_reads_valid_annotation(tmp_path: Path) -> None:
    sample_data = {
        "debate_id": "test_debate_101",
        "document_id": "test_doc_101",
        "units": [
            {
                "unit_id": "u_1",
                "unit_text": "We must invest in public transit",
                "component_label": "CLAIM",
                "speaker_id": "Speaker_A",
                "turn_id": "turn_0",
                "turn_index": 0,
            },
            {
                "unit_id": "u_2",
                "unit_text": "because congestion costs cities billions annually.",
                "component_label": "PREMISE",
                "speaker_id": "Speaker_A",
                "turn_id": "turn_0",
                "turn_index": 0,
            },
        ],
    }
    file_path = tmp_path / "valid_annotation.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    samples = load_argument_units(file_path)
    assert len(samples) == 2
    assert samples[0].text == "We must invest in public transit"
    assert samples[0].component_label == "CLAIM"
    assert samples[0].debate_id == "test_debate_101"
    assert samples[0].speaker_id == "Speaker_A"
    assert samples[0].next_unit == "because congestion costs cities billions annually."
    assert samples[1].previous_unit == "We must invest in public transit"


def test_dataset_loader_rejects_corrupted_labels(tmp_path: Path) -> None:
    corrupted_data = {
        "debate_id": "test_debate_err",
        "units": [
            {
                "unit_id": "u_err",
                "unit_text": "Some text",
                "component_label": "ATTACK",  # Relation label used as component label
                "speaker_id": "Speaker_X",
                "turn_id": "turn_0",
                "turn_index": 0,
            }
        ],
    }
    file_path = tmp_path / "corrupted_annotation.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(corrupted_data, f)

    with pytest.raises(ValueError, match="Invalid argument component label"):
        load_argument_units(file_path)


def test_check_gold_dataset_readiness_distinguishes_pilot(tmp_path: Path) -> None:
    # 1. Empty directory
    is_ready, reason, files = check_gold_dataset_readiness(tmp_path)
    assert not is_ready
    assert "No production ARGUMAP gold annotations found" in reason

    # 2. Directory with only pilot demo file
    pilot_dir = tmp_path / "pilot"
    pilot_dir.mkdir()
    with open(pilot_dir / "sample_annotation.json", "w", encoding="utf-8") as f:
        json.dump({"debate_id": "demo", "units": []}, f)

    is_ready, reason, files = check_gold_dataset_readiness(tmp_path)
    assert not is_ready
    assert "demonstration artifacts only" in reason

    # 3. Directory with real gold file (explicitly licensed)
    with open(tmp_path / "debate_gold_001.json", "w", encoding="utf-8") as f:
        json.dump({"debate_id": "gold_01", "source_corpus": "cleared_corpus", "source_license": "MIT", "units": []}, f)

    is_ready, reason, files = check_gold_dataset_readiness(tmp_path)
    assert is_ready
    assert len(files) == 1

    # 4. Directory with real gold file but unverified license -> must be BLOCKED
    blocked_dir = tmp_path / "blocked_gold"
    blocked_dir.mkdir()
    with open(blocked_dir / "debate_gold_002.json", "w", encoding="utf-8") as f:
        json.dump({"debate_id": "gold_02", "source_corpus": "uk_hansard", "source_license": "UNVERIFIED", "units": []}, f)

    is_ready_b, reason_b, files_b = check_gold_dataset_readiness(blocked_dir)
    assert not is_ready_b
    assert "blocked by dataset licensing gatekeeper" in reason_b
    assert len(files_b) == 0


# --- 3. Debate-Level Splitter Tests ---


def _create_synthetic_units() -> List[ArgumentUnitSample]:
    """Helper to create a multi-debate fixture for testing splitters and models."""
    debates = [f"debate_{i}" for i in range(1, 7)]  # 6 debates
    labels = ["CLAIM", "PREMISE", "EVIDENCE", "COUNTERARGUMENT", "REBUTTAL", "OTHER"]
    samples: List[ArgumentUnitSample] = []

    for d_idx, d in enumerate(debates):
        speaker = f"Speaker_{d_idx % 3}"
        for u_idx in range(6):
            lbl = labels[(d_idx + u_idx) % len(labels)]
            samples.append(
                ArgumentUnitSample(
                    text=f"Proposition {u_idx} in {d} discussing topic {d_idx}",
                    component_label=lbl,
                    debate_id=d,
                    document_id=d,
                    speaker_id=speaker,
                    turn_id=f"turn_{u_idx // 2}",
                    turn_index=u_idx // 2,
                    unit_id=f"u_{d}_{u_idx}",
                )
            )
    return samples


def test_debate_level_splitter_prevents_leakage() -> None:
    samples = _create_synthetic_units()
    config = DatasetSplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, random_seed=42)
    splitter = DebateLevelSplitter(config)

    splits = splitter.split(samples)

    # 1. No overlap between debate IDs
    assert len(splits.train_debates & splits.val_debates) == 0
    assert len(splits.train_debates & splits.test_debates) == 0
    assert len(splits.val_debates & splits.test_debates) == 0

    # 2. Total units preserved
    total_split_units = len(splits.train) + len(splits.val) + len(splits.test)
    assert total_split_units == len(samples)

    # 3. Determinism: same seed yields identical partition
    splits_repeat = splitter.split(samples)
    assert splits.train_debates == splits_repeat.train_debates
    assert splits.val_debates == splits_repeat.val_debates
    assert splits.test_debates == splits_repeat.test_debates


def test_debate_level_splitter_rejects_too_few_debates() -> None:
    samples = _create_synthetic_units()
    # Restrict to only 2 debates
    restricted_samples = [s for s in samples if s.debate_id in ("debate_1", "debate_2")]

    splitter = DebateLevelSplitter(DatasetSplitConfig())
    with pytest.raises(ValueError, match="requires at least 3 unique debates"):
        splitter.split(restricted_samples)


# --- 4. Class Distribution & Metrics Tests ---


def test_compute_class_distribution() -> None:
    samples = _create_synthetic_units()
    dist = compute_class_distribution(samples)

    assert dist["total_units"] == 36
    assert dist["total_debates"] == 6
    assert dist["total_speakers"] == 3

    # All 6 classes should have 6 items each
    for lbl in FROZEN_COMPONENT_LABELS:
        assert dist["class_distribution"][lbl]["count"] == 6
        assert dist["class_distribution"][lbl]["percentage"] == pytest.approx(16.67, abs=0.1)


def test_compute_component_metrics_and_confusion_matrix_ordering() -> None:
    # Canonical label order: CLAIM(0), PREMISE(1), EVIDENCE(2), COUNTERARGUMENT(3), REBUTTAL(4), OTHER(5)
    y_true = ["CLAIM", "CLAIM", "PREMISE", "EVIDENCE", "REBUTTAL", "OTHER"]
    y_pred = ["CLAIM", "PREMISE", "PREMISE", "EVIDENCE", "REBUTTAL", "OTHER"]

    metrics = compute_component_metrics(y_true, y_pred)

    assert metrics["label_order"] == FROZEN_COMPONENT_LABELS
    assert metrics["accuracy"] == pytest.approx(5 / 6)
    assert metrics["macro_f1"] > 0.7
    assert metrics["per_class"]["CLAIM"]["precision"] == 1.0
    assert metrics["per_class"]["CLAIM"]["recall"] == 0.5
    assert metrics["per_class"]["CLAIM"]["support"] == 2

    # Confusion matrix shape must be 6x6
    cm = metrics["confusion_matrix"]
    assert len(cm) == 6
    assert all(len(row) == 6 for row in cm)

    # Row 0 (CLAIM): 1 predicted as CLAIM (col 0), 1 predicted as PREMISE (col 1)
    assert cm[0][0] == 1
    assert cm[0][1] == 1
    assert sum(cm[0]) == 2


# --- 5. TF-IDF Baseline Model Tests ---


def test_tfidf_feature_extractor_pipeline(tmp_path: Path) -> None:
    texts = [
        "The policy creates economic prosperity and innovation.",
        "However, excessive subsidies cause market distortions.",
        "According to empirical evidence from 2024, inflation declined.",
    ]
    extractor = TFIDFFeatureExtractor(TFIDFConfig(ngram_range=(1, 2), min_df=1))
    features = extractor.fit_transform(texts)

    assert features.shape[0] == 3
    assert extractor.vocabulary_size > 5

    # Test serialization
    model_path = tmp_path / "test_vectorizer.joblib"
    extractor.save(model_path)
    loaded = TFIDFFeatureExtractor.load(model_path)
    assert loaded.vocabulary_size == extractor.vocabulary_size
    re_features = loaded.transform(texts)
    assert np.allclose(features.toarray(), re_features.toarray())


def test_tfidf_baseline_classifier_fit_predict_and_persistence(tmp_path: Path) -> None:
    samples = _create_synthetic_units()
    config = TFIDFConfig(ngram_range=(1, 1), min_df=1, random_state=42)

    classifier = TFIDFBaselineClassifier(config)
    classifier.fit(samples)
    assert classifier.is_trained

    # Predict on units
    preds = classifier.predict(samples[:3])
    assert len(preds) == 3
    assert all(p in FROZEN_COMPONENT_LABELS for p in preds)

    # Predict on raw strings
    str_preds = classifier.predict(["Empirical study confirms economic gain."])
    assert len(str_preds) == 1
    assert str_preds[0] in FROZEN_COMPONENT_LABELS

    # Predict probabilities
    probs = classifier.predict_proba(samples[:3])
    assert probs.shape == (3, 6)
    assert np.allclose(probs.sum(axis=1), 1.0)

    # Persistence
    out_dir = tmp_path / "baseline_model"
    classifier.save(out_dir)

    loaded = TFIDFBaselineClassifier.load(out_dir)
    assert loaded.is_trained
    loaded_preds = loaded.predict(samples[:3])
    assert loaded_preds == preds


# --- 6. Transformer Configuration & Dataset Tests (Offline) ---


def test_transformer_config_validation_and_device() -> None:
    cfg = TransformerConfig(model_name="roberta-base", batch_size=8, epochs=2)
    assert cfg.device in ("cpu", "cuda")
    assert cfg.model_name == "roberta-base"

    # Validation errors
    with pytest.raises(ValueError, match="max_length must be positive"):
        TransformerConfig(max_length=0)
    with pytest.raises(ValueError, match="batch_size must be positive"):
        TransformerConfig(batch_size=-1)
    with pytest.raises(ValueError, match="epochs must be positive"):
        TransformerConfig(epochs=0)


class MockTokenizer:
    """Mock Hugging Face tokenizer for offline testing without downloading models."""

    def __init__(self) -> None:
        self.pad_token_id = 0

    def __call__(
        self,
        text: Any,
        max_length: int = 16,
        padding: Any = True,
        truncation: bool = True,
        return_tensors: str = "pt",
    ) -> Dict[str, torch.Tensor]:
        if isinstance(text, str):
            texts = [text]
            single = True
        else:
            texts = list(text)
            single = False

        batch_size = len(texts)
        input_ids = torch.ones((batch_size, max_length), dtype=torch.long)
        attention_mask = torch.ones((batch_size, max_length), dtype=torch.long)

        if single:
            return {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }


def test_argument_unit_dataset_offline() -> None:
    samples = _create_synthetic_units()[:4]
    mock_tok = MockTokenizer()

    # 1. Single-unit mode
    dataset = ArgumentUnitDataset(samples, mock_tok, max_length=16, is_test=False, use_context=False)
    assert len(dataset) == 4
    item = dataset[0]
    assert "input_ids" in item
    assert "attention_mask" in item
    assert "labels" in item
    assert item["input_ids"].shape == torch.Size([16])
    assert item["labels"].item() in range(6)

    # 2. Context-aware mode
    ctx_dataset = ArgumentUnitDataset(samples, mock_tok, max_length=16, is_test=False, use_context=True)
    ctx_item = ctx_dataset[0]
    assert ctx_item["input_ids"].shape == torch.Size([16])


class MockSequenceClassifier(nn.Module):
    """Minimal mock transformer classifier for testing pipeline logic offline."""

    def __init__(self, num_labels: int = 6) -> None:
        super().__init__()
        self.fc = nn.Linear(16, num_labels)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, **kwargs: Any) -> Any:
        float_ids = input_ids.float()
        logits = self.fc(float_ids)
        # Return object with logits attribute
        from types import SimpleNamespace
        return SimpleNamespace(logits=logits)


def test_transformer_wrapper_forward_and_predict_offline() -> None:
    mock_model = MockSequenceClassifier(num_labels=6)
    mock_tok = MockTokenizer()
    cfg = TransformerConfig(device="cpu", max_length=16, batch_size=2)

    transformer = ArgumentComponentTransformer(
        config=cfg,
        model=mock_model,
        tokenizer=mock_tok,
    )
    samples = _create_synthetic_units()[:3]

    # Predict proba
    probs = transformer.predict_proba(samples)
    assert probs.shape == (3, 6)
    assert np.allclose(probs.sum(axis=1), 1.0)

    # Predict labels
    preds = transformer.predict(samples)
    assert len(preds) == 3
    assert all(p in FROZEN_COMPONENT_LABELS for p in preds)


def test_class_weights_computation() -> None:
    samples = _create_synthetic_units()
    weights = compute_class_weights(samples, num_classes=6)

    assert isinstance(weights, torch.Tensor)
    assert weights.shape == torch.Size([6])
    assert pytest.approx(float(weights.mean().item()), abs=1e-3) == 1.0


# --- 7. Missing Dataset Integrity & Halt Tests ---


def test_training_halts_when_gold_data_unavailable(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_annotations"
    empty_dir.mkdir()
    out_dir = tmp_path / "out"

    # Baseline training must halt with BLOCKED
    res_b = run_baseline_training(empty_dir, out_dir / "b")
    assert res_b["status"] == "BLOCKED"
    assert "No production ARGUMAP gold annotations found" in res_b["reason"]
    assert (out_dir / "b" / "experiment_record.json").exists()

    # Transformer training must halt with BLOCKED
    res_t = run_transformer_training(empty_dir, out_dir / "t")
    assert res_t["status"] == "BLOCKED"
    assert "No production ARGUMAP gold annotations found" in res_t["reason"]
    assert (out_dir / "t" / "experiment_record.json").exists()


def test_run_baseline_training_blocks_real_annotations_gold_directory(tmp_path: Path) -> None:
    """Ensure training halts when run against data/annotations due to UNVERIFIED pilot data."""
    real_annotations = PROJECT_ROOT / "data" / "annotations"
    out_dir = tmp_path / "baseline_run_attempt"

    res = run_baseline_training(real_annotations, out_dir)
    assert res["status"] == "BLOCKED"
    assert "blocked by dataset licensing gatekeeper" in res["reason"]
    assert (out_dir / "experiment_record.json").exists()

    with open(out_dir / "experiment_record.json", "r", encoding="utf-8") as f:
        rec = json.load(f)
    assert rec["status"] == "BLOCKED"
    assert rec["dataset_version"] == "ARGUMAP_GOLD_UNAVAILABLE"


def test_run_baseline_training_records_held_out_test_metrics(tmp_path: Path) -> None:
    """Ensure that baseline training on a mock dataset computes both validation and held-out test metrics."""
    # Create a synthetic dataset with 6 debates (allowing 70/15/15 split: train, val, test)
    mock_ann_dir = tmp_path / "mock_annotations"
    mock_ann_dir.mkdir()

    debates = [f"debate_{i}" for i in range(1, 7)]
    labels = ["CLAIM", "PREMISE", "EVIDENCE", "COUNTERARGUMENT", "REBUTTAL", "OTHER"]

    for d_idx, d in enumerate(debates):
        units = []
        for u_idx in range(6):
            lbl = labels[(d_idx + u_idx) % len(labels)]
            units.append({
                "unit_id": f"u_{d}_{u_idx}",
                "unit_text": f"Argument proposition {u_idx} in {d} discussing topic {d_idx}",
                "component_label": lbl,
                "speaker_id": f"Speaker_{d_idx % 2}",
                "turn_id": f"turn_{u_idx // 2}",
                "turn_index": u_idx // 2,
            })
        with open(mock_ann_dir / f"{d}.json", "w", encoding="utf-8") as f:
            json.dump({
                "debate_id": d,
                "source_corpus": "cleared_mock_corpus",
                "source_license": "MIT",
                "units": units,
            }, f)

    out_dir = tmp_path / "baseline_trained_output"
    cfg = TFIDFConfig(ngram_range=(1, 1), min_df=1, random_state=42)
    split_cfg = DatasetSplitConfig(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2, random_seed=42)

    res = run_baseline_training(
        mock_ann_dir,
        out_dir,
        split_config=split_cfg,
        tfidf_config=cfg,
        allow_pilot_for_testing=False,
    )

    assert res["status"] == "COMPLETED"
    assert "val_metrics" in res
    assert "test_metrics" in res
    assert res["test_metrics"] is not None

    test_m = res["test_metrics"]
    assert "accuracy" in test_m
    assert "macro_f1" in test_m
    assert "confusion_matrix" in test_m
    assert "per_class" in test_m

    # Verify experiment record holds both val and test metrics
    with open(out_path := out_dir / "experiment_record.json", "r", encoding="utf-8") as f:
        exp_data = json.load(f)

    assert exp_data["status"] == "COMPLETED"
    assert "val_macro_f1" in exp_data["metrics"]
    assert "test_macro_f1" in exp_data["metrics"]
    assert "test_confusion_matrix" in exp_data["metrics"]


def test_report_formatting_helpers() -> None:
    # Distribution unready report
    unready = format_dataset_distribution_report({}, is_ready=False, unready_reason="Pending annotations")
    assert "DATASET NOT READY FOR TRAINING" in unready
    assert "Pending annotations" in unready

    # Metrics report
    mock_metrics = {
        "accuracy": 0.85,
        "macro_f1": 0.82,
        "macro_precision": 0.83,
        "macro_recall": 0.81,
        "weighted_f1": 0.84,
        "label_order": FROZEN_COMPONENT_LABELS,
        "per_class": {
            lbl: {"precision": 0.8, "recall": 0.8, "f1": 0.8, "support": 10}
            for lbl in FROZEN_COMPONENT_LABELS
        },
        "confusion_matrix": [[10 if i == j else 0 for j in range(6)] for i in range(6)],
    }
    report_text = format_metrics_report(mock_metrics, model_name="Test Model")
    assert "PRIMARY METRIC" in report_text
    assert "CLAIM" in report_text
    assert "Confusion Matrix" in report_text
