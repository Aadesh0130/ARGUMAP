"""Debate-level grouped train/validation/test dataset splitter.

Guarantees zero debate-level leakage across splits by partitioning grouped
debate identifiers rather than randomly partitioning individual argument units.
"""

from dataclasses import dataclass
import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from ml.config import DatasetSplitConfig
from ml.data.dataset_loader import ArgumentUnitSample


@dataclass
class DatasetSplits:
    """Container holding partitioned argument unit samples and partition metadata."""
    train: List[ArgumentUnitSample]
    val: List[ArgumentUnitSample]
    test: List[ArgumentUnitSample]
    train_debates: Set[str]
    val_debates: Set[str]
    test_debates: Set[str]
    train_speakers: Set[str]
    val_speakers: Set[str]
    test_speakers: Set[str]

    def verify_no_debate_leakage(self) -> None:
        """Assert zero overlap between debate sets across all three partitions."""
        tv_overlap = self.train_debates & self.val_debates
        tt_overlap = self.train_debates & self.test_debates
        vt_overlap = self.val_debates & self.test_debates

        if tv_overlap:
            raise ValueError(f"Debate leakage detected between train and val: {tv_overlap}")
        if tt_overlap:
            raise ValueError(f"Debate leakage detected between train and test: {tt_overlap}")
        if vt_overlap:
            raise ValueError(f"Debate leakage detected between val and test: {vt_overlap}")

    def get_summary(self) -> Dict[str, Any]:
        """Summarize split counts."""
        return {
            "train_units": len(self.train),
            "val_units": len(self.val),
            "test_units": len(self.test),
            "train_debates": len(self.train_debates),
            "val_debates": len(self.val_debates),
            "test_debates": len(self.test_debates),
            "train_speakers": len(self.train_speakers),
            "val_speakers": len(self.val_speakers),
            "test_speakers": len(self.test_speakers),
        }


class DebateLevelSplitter:
    """Partitions argument units grouped strictly by debate identifier."""

    def __init__(self, config: Optional[DatasetSplitConfig] = None) -> None:
        self.config = config or DatasetSplitConfig()

    def split(
        self,
        samples: Sequence[ArgumentUnitSample],
        group_by: str = "debate_id",
    ) -> DatasetSplits:
        """Split samples deterministically by debate group.

        Args:
            samples: Sequence of ArgumentUnitSample objects.
            group_by: Field to group by ('debate_id' or 'document_id').

        Returns:
            DatasetSplits containing train, val, and test partitions.

        Raises:
            ValueError: If fewer than 3 unique debate groups exist when all
                        three partitions are requested with positive ratios.
        """
        if not samples:
            empty_set: Set[str] = set()
            return DatasetSplits([], [], [], empty_set, empty_set, empty_set, empty_set, empty_set, empty_set)

        # Group samples by debate ID
        debate_to_samples: Dict[str, List[ArgumentUnitSample]] = {}
        for s in samples:
            grp = getattr(s, group_by)
            debate_to_samples.setdefault(grp, []).append(s)

        unique_debates = sorted(list(debate_to_samples.keys()))
        n_debates = len(unique_debates)

        if n_debates < 3 and self.config.val_ratio > 0 and self.config.test_ratio > 0:
            raise ValueError(
                f"Debate-level splitting requires at least 3 unique debates to produce "
                f"train, val, and test splits without leakage (found {n_debates}: {unique_debates})."
            )

        # Deterministic shuffle
        rng = random.Random(self.config.random_seed)
        shuffled_debates = list(unique_debates)
        rng.shuffle(shuffled_debates)

        n_train = max(1, int(round(n_debates * self.config.train_ratio)))
        n_val = max(1, int(round(n_debates * self.config.val_ratio)))

        # Ensure bounds so that test has at least 1 debate if n_debates >= 3
        if n_train + n_val >= n_debates:
            n_train = max(1, n_debates - 2)
            n_val = 1

        train_debate_ids = set(shuffled_debates[:n_train])
        val_debate_ids = set(shuffled_debates[n_train:n_train + n_val])
        test_debate_ids = set(shuffled_debates[n_train + n_val:])

        # Collect units
        train_units: List[ArgumentUnitSample] = []
        val_units: List[ArgumentUnitSample] = []
        test_units: List[ArgumentUnitSample] = []

        for d_id, unit_list in debate_to_samples.items():
            if d_id in train_debate_ids:
                train_units.extend(unit_list)
            elif d_id in val_debate_ids:
                val_units.extend(unit_list)
            elif d_id in test_debate_ids:
                test_units.extend(unit_list)

        splits = DatasetSplits(
            train=train_units,
            val=val_units,
            test=test_units,
            train_debates=train_debate_ids,
            val_debates=val_debate_ids,
            test_debates=test_debate_ids,
            train_speakers={s.speaker_id for s in train_units},
            val_speakers={s.speaker_id for s in val_units},
            test_speakers={s.speaker_id for s in test_units},
        )
        splits.verify_no_debate_leakage()
        return splits
