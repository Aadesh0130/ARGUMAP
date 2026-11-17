"""Evaluation routines for fine-tuned Transformer component classifiers."""

from typing import Any, Dict, Sequence

from ml.data.dataset_loader import ArgumentUnitSample
from ml.evaluation.metrics import compute_component_metrics
from ml.evaluation.reports import format_metrics_report
from ml.transformer.classifier import ArgumentComponentTransformer


def evaluate_transformer_model(
    model: ArgumentComponentTransformer,
    test_samples: Sequence[ArgumentUnitSample],
    batch_size: int = 16,
) -> Dict[str, Any]:
    """Run model inference over test partition and compute ARGUMAP metrics.

    Preserves the test set evaluation integrity.
    """
    if not test_samples:
        raise ValueError("Cannot evaluate model on empty test partition.")

    y_true = [s.component_label for s in test_samples]
    y_pred = model.predict(test_samples, batch_size=batch_size)

    metrics = compute_component_metrics(y_true, y_pred)
    report_text = format_metrics_report(metrics, model_name=f"Transformer ({model.config.model_name})")

    return {
        "metrics": metrics,
        "report": report_text,
    }
