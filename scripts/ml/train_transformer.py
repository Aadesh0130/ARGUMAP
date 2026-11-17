"""CLI utility: Train Transformer sequence classifier on ARGUMAP component taxonomy."""

import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.config import DatasetSplitConfig, TransformerConfig
from ml.evaluation.reports import format_metrics_report
from ml.transformer.train import run_transformer_training


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fine-tune Transformer classifier for ARGUMAP component classification."
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
        default=Path("models/component_classifier"),
        help="Path to save trained transformer checkpoint and metadata.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="roberta-base",
        help="Pretrained Hugging Face transformer model identifier.",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size.")
    parser.add_argument("--learning-rate", type=float, default=2e-5, help="Learning rate.")
    parser.add_argument("--max-length", type=int, default=256, help="Maximum sequence token length.")
    parser.add_argument("--seed", type=int, default=42, help="Random state seed.")
    parser.add_argument(
        "--allow-pilot",
        action="store_true",
        help="Allow loading pilot demo data (FOR FIXTURE TESTING ONLY).",
    )

    args = parser.parse_args()

    transformer_cfg = TransformerConfig(
        model_name=args.model_name,
        max_length=args.max_length,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        random_seed=args.seed,
        output_dir=str(args.output_dir),
    )
    split_cfg = DatasetSplitConfig(random_seed=args.seed)

    print("=" * 68)
    print(f"ARGUMAP Transformer Classifier Training ({args.model_name})")
    print(f"Detected Device: {transformer_cfg.device.upper()}")
    print("=" * 68)

    results = run_transformer_training(
        annotations_dir=args.annotations_dir,
        output_dir=args.output_dir,
        transformer_config=transformer_cfg,
        split_config=split_cfg,
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
    print(format_metrics_report(results["val_metrics"], model_name=f"Transformer ({args.model_name})"))
    print(f"\nModel checkpoint persisted to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
