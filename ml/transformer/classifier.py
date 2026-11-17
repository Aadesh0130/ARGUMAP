"""Transformer sequence classification model for ARGUMAP 6-class component classification."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import torch
import torch.nn as nn

from ml.config import TransformerConfig
from ml.data.dataset_loader import ArgumentUnitSample
from ml.data.label_encoder import FROZEN_COMPONENT_LABELS, ComponentLabelEncoder


class ArgumentComponentTransformer(nn.Module):
    """Transformer sequence classification model for ARGUMAP argument propositions.

    Supports roberta-base, deberta-v3, and other AutoModel architectures.
    Supports weighted cross-entropy loss to address class imbalance.
    """

    def __init__(
        self,
        config: Optional[TransformerConfig] = None,
        class_weights: Optional[torch.Tensor] = None,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
    ) -> None:
        super().__init__()
        self.config = config or TransformerConfig()
        self.label_encoder = ComponentLabelEncoder()
        self.num_classes = self.label_encoder.num_classes
        self.device_str = self.config.device
        self.device = torch.device(self.device_str)

        self.class_weights = class_weights
        if self.class_weights is not None:
            self.loss_fn = nn.CrossEntropyLoss(weight=self.class_weights.to(self.device))
        else:
            self.loss_fn = nn.CrossEntropyLoss()

        self.model = model
        self.tokenizer = tokenizer

    @classmethod
    def from_model_name(
        cls,
        config: Optional[TransformerConfig] = None,
        class_weights: Optional[torch.Tensor] = None,
    ) -> "ArgumentComponentTransformer":
        """Instantiate tokenizer and sequence classification model from Hugging Face model hub."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        cfg = config or TransformerConfig()
        tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            cfg.model_name,
            num_labels=len(FROZEN_COMPONENT_LABELS),
            id2label={i: lbl for i, lbl in enumerate(FROZEN_COMPONENT_LABELS)},
            label2id={lbl: i for i, lbl in enumerate(FROZEN_COMPONENT_LABELS)},
        )
        instance = cls(config=cfg, class_weights=class_weights, model=model, tokenizer=tokenizer)
        instance.to(instance.device)
        return instance

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """Forward pass through transformer encoder and classification head."""
        if self.model is None:
            raise RuntimeError("Model has not been initialized.")

        kwargs: Dict[str, Any] = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        if token_type_ids is not None:
            kwargs["token_type_ids"] = token_type_ids

        outputs = self.model(**kwargs)
        logits = outputs.logits if hasattr(outputs, "logits") else outputs[0]

        loss = None
        if labels is not None:
            loss = self.loss_fn(logits.view(-1, self.num_classes), labels.view(-1))

        return {
            "loss": loss,
            "logits": logits,
        }

    def _extract_texts(
        self, samples_or_texts: Sequence[Union[ArgumentUnitSample, str]]
    ) -> List[str]:
        texts: List[str] = []
        for item in samples_or_texts:
            if isinstance(item, ArgumentUnitSample):
                texts.append(item.text)
            elif isinstance(item, str):
                texts.append(item)
            else:
                raise TypeError(f"Expected ArgumentUnitSample or str, got {type(item)}")
        return texts

    def predict_proba(
        self,
        samples_or_texts: Sequence[Union[ArgumentUnitSample, str]],
        batch_size: Optional[int] = None,
    ) -> np.ndarray:
        """Predict class probability distribution for input texts."""
        if self.tokenizer is None or self.model is None:
            raise RuntimeError("Model and tokenizer must be initialized before predicting.")

        texts = self._extract_texts(samples_or_texts)
        if not texts:
            return np.empty((0, self.num_classes))

        bs = batch_size or self.config.batch_size
        self.eval()

        all_probs: List[np.ndarray] = []
        with torch.no_grad():
            for i in range(0, len(texts), bs):
                batch_texts = texts[i:i + bs]
                encoded = self.tokenizer(
                    batch_texts,
                    max_length=self.config.max_length,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                )
                input_ids = encoded["input_ids"].to(self.device)
                attention_mask = encoded["attention_mask"].to(self.device)
                token_type_ids = encoded.get("token_type_ids")
                if token_type_ids is not None:
                    token_type_ids = token_type_ids.to(self.device)

                out = self.forward(input_ids, attention_mask, token_type_ids)
                probs = torch.softmax(out["logits"], dim=-1).cpu().numpy()
                all_probs.append(probs)

        return np.vstack(all_probs)

    def predict(
        self,
        samples_or_texts: Sequence[Union[ArgumentUnitSample, str]],
        batch_size: Optional[int] = None,
    ) -> List[str]:
        """Predict component label strings for input texts."""
        probs = self.predict_proba(samples_or_texts, batch_size)
        if len(probs) == 0:
            return []
        pred_indices = np.argmax(probs, axis=1)
        return self.label_encoder.decode_batch(pred_indices.tolist())

    def save_pretrained(self, save_directory: Union[str, Path]) -> None:
        """Serialize transformer model, tokenizer, and ARGUMAP configuration."""
        save_path = Path(save_directory)
        save_path.mkdir(parents=True, exist_ok=True)

        if self.model is not None and hasattr(self.model, "save_pretrained"):
            self.model.save_pretrained(save_path)
        if self.tokenizer is not None and hasattr(self.tokenizer, "save_pretrained"):
            self.tokenizer.save_pretrained(save_path)

        # Save config and label mapping
        with open(save_path / "argumap_config.json", "w", encoding="utf-8") as f:
            json.dump(self.config.to_dict(), f, indent=2)

        with open(save_path / "label_mapping.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "labels": FROZEN_COMPONENT_LABELS,
                    "label_to_id": self.label_encoder.label_to_id,
                    "id_to_label": self.label_encoder.id_to_label,
                },
                f,
                indent=2,
            )

    @classmethod
    def load_pretrained(cls, load_directory: Union[str, Path]) -> "ArgumentComponentTransformer":
        """Load fine-tuned transformer and tokenizer from disk."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        path = Path(load_directory)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        cfg_file = path / "argumap_config.json"
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            config = TransformerConfig(
                model_name=cfg_data.get("model_name", "roberta-base"),
                max_length=cfg_data.get("max_length", 256),
                batch_size=cfg_data.get("batch_size", 16),
                learning_rate=cfg_data.get("learning_rate", 2e-5),
                epochs=cfg_data.get("epochs", 3),
                weight_decay=cfg_data.get("weight_decay", 0.01),
                warmup_ratio=cfg_data.get("warmup_ratio", 0.1),
                random_seed=cfg_data.get("random_seed", 42),
                output_dir=cfg_data.get("output_dir", str(path)),
                use_class_weights=cfg_data.get("use_class_weights", True),
            )
        else:
            config = TransformerConfig()

        tokenizer = AutoTokenizer.from_pretrained(str(path))
        model = AutoModelForSequenceClassification.from_pretrained(str(path))

        instance = cls(config=config, model=model, tokenizer=tokenizer)
        instance.to(instance.device)
        return instance
