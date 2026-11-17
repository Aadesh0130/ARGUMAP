"""PyTorch Dataset wrapper for ARGUMAP argument propositions."""

from typing import Any, Dict, List, Optional, Sequence
import torch
from torch.utils.data import Dataset

from ml.data.dataset_loader import ArgumentUnitSample
from ml.data.label_encoder import ComponentLabelEncoder


class ArgumentUnitDataset(Dataset):
    """PyTorch Dataset for single-proposition or context-aware argument classification.

    Prepares tokenized sequences compatible with Transformer sequence classifiers.
    Exposes contextual discourse slots (previous_unit, current_unit, next_unit, speaker).
    """

    def __init__(
        self,
        samples: Sequence[ArgumentUnitSample],
        tokenizer: Any,
        max_length: int = 256,
        is_test: bool = False,
        use_context: bool = False,
    ) -> None:
        self.samples = list(samples)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.is_test = is_test
        self.use_context = use_context
        self.label_encoder = ComponentLabelEncoder()

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]

        if self.use_context:
            # Context-aware representation ready for future iterations
            prev = sample.previous_unit or ""
            nxt = sample.next_unit or ""
            text = f"{prev} [SEP] {sample.text} [SEP] {nxt}"
        else:
            # Main Step 7 focus: current proposition text
            text = sample.text

        encoded = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        item: Dict[str, Any] = {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "unit_id": sample.unit_id,
            "debate_id": sample.debate_id,
            "turn_index": sample.turn_index,
        }

        if "token_type_ids" in encoded:
            item["token_type_ids"] = encoded["token_type_ids"].squeeze(0)

        if not self.is_test:
            label_id = self.label_encoder.encode(sample.component_label)
            item["labels"] = torch.tensor(label_id, dtype=torch.long)

        return item
