"""Training pipeline orchestration for TF-IDF + Logistic Regression baseline."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

from ml.config import DatasetSplitConfig, ExperimentRecord, TFIDFConfig
from ml.data.dataset_loader import (
    check_gold_dataset_readiness,
    load_argument_units,
)
from ml.data.dataset_splitter import DebateLevelSplitter
from ml.baseline.tfidf_classifier import TFIDFBaselineClassifier
from ml.evaluation.metrics import (
    compute_class_distribution,
    compute_component_metrics,
)
from ml.evaluation.reports import (
    format_dataset_distribution_report,
    format_metrics_report,
)


def run_baseline_training(
    annotations_dir: Path,
    output_dir: Path,
    split_config: Optional[DatasetSplitConfig] = None,
    tfidf_config: Optional[TFIDFConfig] = None,
    manifest_path: Optional[Path] = None,
    allow_pilot_for_testing: bool = False,
) -> Dict[str, Any]:
    """Execute baseline training workflow.

    Enforces data integrity:
    If no real gold annotations are available or candidate corpora are blocked,
    returns status BLOCKED without training on unverified data or fabricating benchmark results.
    """
    annotations_path = Path(annotations_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    s_config = split_config or DatasetSplitConfig()
    m_config = tfidf_config or TFIDFConfig()

    # 1. Check gold dataset readiness and licensing clearance
    is_ready, reason, gold_files = check_gold_dataset_readiness(annotations_path, manifest_path=manifest_path)
    if not is_ready and not allow_pilot_for_testing:
        blocked_record = ExperimentRecord(
            experiment_id="baseline_tfidf_blocked",
            model_name="TF-IDF + Logistic Regression",
            dataset_version="ARGUMAP_GOLD_UNAVAILABLE",
            dataset_split_seed=s_config.random_seed,
            hyperparameters=m_config.to_dict(),
            training_date=datetime.now(timezone.utc).isoformat(),
            device="cpu",
            number_of_train_samples=0,
            number_of_validation_samples=0,
            number_of_test_samples=0,
            metrics={},
            status="BLOCKED",
            notes=f"Training halted: {reason}",
        )
        # Save experiment tracking record
        record_path = out_path / "experiment_record.json"
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(blocked_record.to_dict(), f, indent=2)

        return {
            "status": "BLOCKED",
            "reason": reason,
            "experiment_record": blocked_record.to_dict(),
        }

    # 2. Load dataset
    samples = load_argument_units(annotations_path, include_pilot=allow_pilot_for_testing)
    if not samples:
        return {
            "status": "BLOCKED",
            "reason": "No argument unit samples loaded.",
            "experiment_record": None,
        }

    # 3. Class distribution check
    dist_info = compute_class_distribution(samples)
    dist_report = format_dataset_distribution_report(dist_info, is_ready=True)

    # 4. Debate-level split
    splitter = DebateLevelSplitter(s_config)
    splits = splitter.split(samples)

    # 5. Train classifier
    classifier = TFIDFBaselineClassifier(m_config)
    classifier.fit(splits.train)

    # 6. Evaluate on validation set
    val_preds = classifier.predict(splits.val)
    val_true = [s.component_label for s in splits.val]
    val_metrics = compute_component_metrics(val_true, val_preds)

    # 7. Evaluate on held-out test set (if non-empty)
    test_metrics: Optional[Dict[str, Any]] = None
    if splits.test:
        test_preds = classifier.predict(splits.test)
        test_true = [s.component_label for s in splits.test]
        test_metrics = compute_component_metrics(test_true, test_preds)

    # 8. Persist trained model
    classifier.save(out_path)

    # 9. Record experiment with full metrics
    recorded_metrics: Dict[str, Any] = {
        "val_accuracy": val_metrics["accuracy"],
        "val_macro_f1": val_metrics["macro_f1"],
        "val_macro_precision": val_metrics["macro_precision"],
        "val_macro_recall": val_metrics["macro_recall"],
        "val_weighted_f1": val_metrics["weighted_f1"],
        "val_per_class": val_metrics["per_class"],
        "val_confusion_matrix": val_metrics["confusion_matrix"],
    }
    if test_metrics:
        recorded_metrics.update({
            "test_accuracy": test_metrics["accuracy"],
            "test_macro_f1": test_metrics["macro_f1"],
            "test_macro_precision": test_metrics["macro_precision"],
            "test_macro_recall": test_metrics["macro_recall"],
            "test_weighted_f1": test_metrics["weighted_f1"],
            "test_per_class": test_metrics["per_class"],
            "test_confusion_matrix": test_metrics["confusion_matrix"],
        })

    exp_record = ExperimentRecord(
        experiment_id=f"baseline_tfidf_{int(datetime.now(timezone.utc).timestamp())}",
        model_name="TF-IDF + Logistic Regression",
        dataset_version="ARGUMAP_V1",
        dataset_split_seed=s_config.random_seed,
        hyperparameters=m_config.to_dict(),
        training_date=datetime.now(timezone.utc).isoformat(),
        device="cpu",
        number_of_train_samples=len(splits.train),
        number_of_validation_samples=len(splits.val),
        number_of_test_samples=len(splits.test),
        metrics=recorded_metrics,
        status="COMPLETED",
        notes="Trained and evaluated on held-out partitions.",
    )

    with open(out_path / "experiment_record.json", "w", encoding="utf-8") as f:
        json.dump(exp_record.to_dict(), f, indent=2)

    return {
        "status": "COMPLETED",
        "splits_summary": splits.get_summary(),
        "distribution_report": dist_report,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "experiment_record": exp_record.to_dict(),
    }
