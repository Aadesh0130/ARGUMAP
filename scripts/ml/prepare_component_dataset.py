"""CLI utility: Prepare component classification dataset and debate-level splits.

Enforces dataset integrity:
- Reports DATASET NOT READY FOR TRAINING if only pilot/demo data exists.
- Executes debate-level grouped split (70/15/15) when real gold data is provided.
"""

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.config import DatasetSplitConfig
from ml.data.dataset_loader import (
    check_gold_dataset_readiness,
    load_argument_units,
)
from ml.data.dataset_splitter import DebateLevelSplitter
from ml.evaluation.metrics import compute_class_distribution
from ml.evaluation.reports import format_dataset_distribution_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare ARGUMAP component classification dataset and debate-level splits."
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
        default=Path("data/splits"),
        help="Path to output split records directory.",
    )
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train split ratio.")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Validation split ratio.")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test split ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic split.")
    parser.add_argument(
        "--allow-pilot",
        action="store_true",
        help="Allow loading pilot demo data (FOR FIXTURE TESTING ONLY).",
    )

    args = parser.parse_args()

    # 1. Check dataset readiness
    is_ready, reason, gold_files = check_gold_dataset_readiness(args.annotations_dir)
    if not is_ready and not args.allow_pilot:
        print(format_dataset_distribution_report({}, is_ready=False, unready_reason=reason))
        return 1

    # 2. Load units
    samples = load_argument_units(args.annotations_dir, include_pilot=args.allow_pilot)
    if not samples:
        print(format_dataset_distribution_report({}, is_ready=False, unready_reason="No samples found."))
        return 1

    # 3. Class distribution report
    dist_info = compute_class_distribution(samples)
    print(format_dataset_distribution_report(dist_info, is_ready=True))

    # 4. Perform debate-level split
    split_config = DatasetSplitConfig(
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.seed,
    )
    splitter = DebateLevelSplitter(split_config)

    try:
        splits = splitter.split(samples)
    except ValueError as e:
        print(f"\n[ERROR] Splitting failed: {e}")
        return 1

    print("\nDebate-Level Partition Summary:")
    summary = splits.get_summary()
    for k, v in summary.items():
        print(f"  {k:<16}: {v}")

    # 5. Save splits if requested
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_split_seed": args.seed,
        "train_units_count": len(splits.train),
        "val_units_count": len(splits.val),
        "test_units_count": len(splits.test),
        "train_debates": sorted(list(splits.train_debates)),
        "val_debates": sorted(list(splits.val_debates)),
        "test_debates": sorted(list(splits.test_debates)),
    }
    with open(args.output_dir / "component_splits_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSaved split manifest to: {args.output_dir / 'component_splits_manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
