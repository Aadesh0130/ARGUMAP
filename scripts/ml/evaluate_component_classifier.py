"""CLI utility: Evaluate trained component classification model on test partition."""

import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.data.dataset_loader import check_gold_dataset_readiness, load_argument_units
from ml.baseline.tfidf_classifier import TFIDFBaselineClassifier
from ml.evaluation.metrics import compute_component_metrics
from ml.evaluation.reports import format_metrics_report
from ml.transformer.classifier import ArgumentComponentTransformer


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate ARGUMAP component classifier on test argument units."
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        required=True,
        help="Directory containing trained model artifacts.",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        choices=["baseline", "transformer"],
        required=True,
        help="Type of model to evaluate ('baseline' or 'transformer').",
    )
    parser.add_argument(
        "--test-data",
        type=Path,
        default=Path("data/annotations"),
        help="Path to test annotations directory or JSON file.",
    )
    parser.add_argument(
        "--allow-pilot",
        action="store_true",
        help="Allow evaluating on pilot demo data (FOR FIXTURE TESTING ONLY).",
    )

    args = parser.parse_args()

    # Check test dataset readiness
    is_ready, reason, _ = check_gold_dataset_readiness(args.test_data)
    if not is_ready and not args.allow_pilot:
        print("=" * 68)
        print("ARGUMAP Component Classifier Evaluation")
        print("=" * 68)
        print("Evaluation status: BLOCKED")
        print(f"Reason: {reason}")
        return 1

    # Load test units
    test_samples = load_argument_units(args.test_data, include_pilot=args.allow_pilot)
    if not test_samples:
        print("Evaluation status: BLOCKED")
        print("Reason: No test argument units available.")
        return 1

    print("=" * 68)
    print(f"ARGUMAP Evaluation ({args.model_type.upper()}) on {len(test_samples)} units")
    print("=" * 68)

    y_true = [s.component_label for s in test_samples]

    if args.model_type == "baseline":
        classifier = TFIDFBaselineClassifier.load(args.model_dir)
        y_pred = classifier.predict(test_samples)
        model_name = "TF-IDF + Logistic Regression Baseline"
    else:
        transformer = ArgumentComponentTransformer.load_pretrained(args.model_dir)
        y_pred = transformer.predict(test_samples)
        model_name = f"Transformer ({transformer.config.model_name})"

    metrics = compute_component_metrics(y_true, y_pred)
    print(format_metrics_report(metrics, model_name=model_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
