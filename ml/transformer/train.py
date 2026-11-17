"""Training orchestration for Transformer sequence classification on ARGUMAP."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import torch
from torch.utils.data import DataLoader

from ml.config import DatasetSplitConfig, ExperimentRecord, TransformerConfig
from ml.data.dataset_loader import (
    ArgumentUnitSample,
    check_gold_dataset_readiness,
    load_argument_units,
)
from ml.data.dataset_splitter import DebateLevelSplitter
from ml.data.label_encoder import FROZEN_COMPONENT_LABELS, ComponentLabelEncoder
from ml.evaluation.metrics import (
    compute_class_distribution,
    compute_component_metrics,
)
from ml.evaluation.reports import format_dataset_distribution_report
from ml.transformer.classifier import ArgumentComponentTransformer
from ml.transformer.dataset import ArgumentUnitDataset


def compute_class_weights(
    samples: Sequence[ArgumentUnitSample],
    num_classes: int = len(FROZEN_COMPONENT_LABELS),
) -> torch.Tensor:
    """Compute balanced class weights for CrossEntropyLoss to address class imbalance.

    Weight for class c: w_c = N / (K * N_c) with minimum floor to prevent division by zero.
    """
    encoder = ComponentLabelEncoder()
    labels = [encoder.encode(s.component_label) for s in samples]
    counts = np.bincount(labels, minlength=num_classes)
    total_samples = len(samples)

    weights = np.zeros(num_classes, dtype=np.float32)
    for c in range(num_classes):
        if counts[c] > 0:
            weights[c] = total_samples / (num_classes * counts[c])
        else:
            weights[c] = 1.0  # Default neutral weight if unrepresented

    # Normalize weights so mean is 1.0
    weights = weights / np.mean(weights)
    return torch.tensor(weights, dtype=torch.float32)


def run_transformer_training(
    annotations_dir: Path,
    output_dir: Path,
    transformer_config: Optional[TransformerConfig] = None,
    split_config: Optional[DatasetSplitConfig] = None,
    manifest_path: Optional[Path] = None,
    allow_pilot_for_testing: bool = False,
) -> Dict[str, Any]:
    """Execute Transformer training workflow.

    Enforces data integrity:
    If no real gold annotations are available or candidate corpora are blocked,
    halts immediately with status BLOCKED.
    Does NOT train on unverified data or report fake accuracy.
    """
    annotations_path = Path(annotations_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    t_config = transformer_config or TransformerConfig()
    s_config = split_config or DatasetSplitConfig()

    # 1. Check dataset readiness and licensing clearance
    is_ready, reason, _ = check_gold_dataset_readiness(annotations_path, manifest_path=manifest_path)
    if not is_ready and not allow_pilot_for_testing:
        blocked_record = ExperimentRecord(
            experiment_id="transformer_roberta_blocked",
            model_name=t_config.model_name,
            dataset_version="ARGUMAP_GOLD_UNAVAILABLE",
            dataset_split_seed=s_config.random_seed,
            hyperparameters=t_config.to_dict(),
            training_date=datetime.now(timezone.utc).isoformat(),
            device=t_config.device,
            number_of_train_samples=0,
            number_of_validation_samples=0,
            number_of_test_samples=0,
            metrics={},
            status="BLOCKED",
            notes=f"Training halted: {reason}",
        )
        with open(out_path / "experiment_record.json", "w", encoding="utf-8") as f:
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
            "reason": "No argument unit samples available.",
            "experiment_record": None,
        }

    # 3. Class distribution check
    dist_info = compute_class_distribution(samples)
    dist_report = format_dataset_distribution_report(dist_info, is_ready=True)

    # 4. Debate-level split
    splitter = DebateLevelSplitter(s_config)
    splits = splitter.split(samples)

    # 5. Class imbalance weighting
    class_weights = None
    if t_config.use_class_weights:
        class_weights = compute_class_weights(splits.train)

    # 6. Instantiate transformer model and tokenizer
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    tokenizer = AutoTokenizer.from_pretrained(t_config.model_name)
    hf_model = AutoModelForSequenceClassification.from_pretrained(
        t_config.model_name,
        num_labels=len(FROZEN_COMPONENT_LABELS),
    )
    model = ArgumentComponentTransformer(
        config=t_config,
        class_weights=class_weights,
        model=hf_model,
        tokenizer=tokenizer,
    )
    model.to(model.device)

    # 7. Create PyTorch datasets and loaders
    train_dataset = ArgumentUnitDataset(splits.train, tokenizer, max_length=t_config.max_length)
    val_dataset = ArgumentUnitDataset(splits.val, tokenizer, max_length=t_config.max_length)

    train_loader = DataLoader(train_dataset, batch_size=t_config.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=t_config.batch_size, shuffle=False)

    # 8. Optimizer
    from torch.optim import AdamW

    optimizer = AdamW(model.parameters(), lr=t_config.learning_rate, weight_decay=t_config.weight_decay)

    # 9. Training loop
    best_val_macro_f1 = -1.0
    for epoch in range(1, t_config.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(model.device)
            attention_mask = batch["attention_mask"].to(model.device)
            labels = batch["labels"].to(model.device)
            token_type_ids = batch.get("token_type_ids")
            if token_type_ids is not None:
                token_type_ids = token_type_ids.to(model.device)

            outputs = model(input_ids, attention_mask, token_type_ids, labels=labels)
            loss = outputs["loss"]
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        # Validation evaluation
        model.eval()
        val_preds_list: List[str] = []
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(model.device)
                attention_mask = batch["attention_mask"].to(model.device)
                token_type_ids = batch.get("token_type_ids")
                if token_type_ids is not None:
                    token_type_ids = token_type_ids.to(model.device)

                outputs = model(input_ids, attention_mask, token_type_ids)
                preds = torch.argmax(outputs["logits"], dim=-1).cpu().tolist()
                val_preds_list.extend(model.label_encoder.decode_batch(preds))

        val_true = [s.component_label for s in splits.val]
        val_metrics = compute_component_metrics(val_true, val_preds_list)

        if val_metrics["macro_f1"] > best_val_macro_f1:
            best_val_macro_f1 = val_metrics["macro_f1"]
            model.save_pretrained(out_path)

    # 10. Record experiment
    exp_record = ExperimentRecord(
        experiment_id=f"transformer_{t_config.model_name.replace('/', '_')}_{int(datetime.now(timezone.utc).timestamp())}",
        model_name=t_config.model_name,
        dataset_version="ARGUMAP_V1",
        dataset_split_seed=s_config.random_seed,
        hyperparameters=t_config.to_dict(),
        training_date=datetime.now(timezone.utc).isoformat(),
        device=t_config.device,
        number_of_train_samples=len(splits.train),
        number_of_validation_samples=len(splits.val),
        number_of_test_samples=len(splits.test),
        metrics={
            "val_accuracy": val_metrics["accuracy"],
            "val_macro_f1": val_metrics["macro_f1"],
            "val_weighted_f1": val_metrics["weighted_f1"],
            "val_per_class": val_metrics["per_class"],
        },
        status="COMPLETED",
        notes="Model checkpoint saved to output_dir.",
    )

    with open(out_path / "experiment_record.json", "w", encoding="utf-8") as f:
        json.dump(exp_record.to_dict(), f, indent=2)

    return {
        "status": "COMPLETED",
        "splits_summary": splits.get_summary(),
        "distribution_report": dist_report,
        "val_metrics": val_metrics,
        "experiment_record": exp_record.to_dict(),
    }
