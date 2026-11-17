"""CLI utility: Train TF-IDF + Logistic Regression baseline component classifier."""

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.config import DatasetSplitConfig, TFIDFConfig
from ml.baseline.train_baseline import run_baseline_training
from ml.evaluation.reports import format_metrics_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train TF-IDF + Logistic Regression baseline for ARGUMAP component classification."
    )
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=Path("data/annotations"),
        help="Path to annotations directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/baseline_tfidf"),
        help="Path to save trained baseline model and metadata.",
    )
    parser.add_argument("--C", type=float, default=1.0, help="Inverse regularization strength.")
    parser.add_argument(
        "--class-weight",
        type=str,
        default="balanced",
        help="Class weight strategy ('balanced' or 'none').",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random state seed.")
    parser.add_argument(
        "--allow-pilot",
        action="store_true",
        help="Allow loading pilot demo data (FOR FIXTURE TESTING ONLY).",
    )

    args = parser.parse_args()

    tfidf_cfg = TFIDFConfig(
        C=args.C,
        class_weight=None if args.class_weight.lower() == "none" else args.class_weight,
        random_state=args.seed,
    )
    split_cfg = DatasetSplitConfig(random_seed=args.seed)

    print("=" * 68)
    print("ARGUMAP Baseline Model Training (TF-IDF + Logistic Regression)")
    print("=" * 68)

    results = run_baseline_training(
        annotations_dir=args.annotations_dir,
        output_dir=args.output_dir,
        split_config=split_cfg,
        tfidf_config=tfidf_cfg,
        allow_pilot_for_testing=args.allow_pilot,
    )

    if results["status"] == "BLOCKED":
        print(f"\nTraining status: BLOCKED")
        print(f"Reason: {results['reason']}")
        print(f"Experiment record written to: {args.output_dir / 'experiment_record.json'}")
        return 1

    print("\nTraining status: COMPLETED")
    print("\n" + results.get("distribution_report", ""))
    print("\nValidation Performance:")
    print(format_metrics_report(results["val_metrics"], model_name="TF-IDF Baseline"))
    print(f"\nModel and artifacts persisted to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
