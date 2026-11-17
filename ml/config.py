"""Configuration management for ARGUMAP Machine Learning modules.

Defines reproducible hyperparameter configurations for:
- Data splitting (debate-level)
- TF-IDF + Logistic Regression baseline
- Transformer encoder classifier
- Hardware detection (CUDA / CPU)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_available_device() -> str:
    """Detect available compute device (CUDA or CPU).

    Returns:
        'cuda' if PyTorch and a CUDA-capable device are available, else 'cpu'.
    """
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


@dataclass
class DatasetSplitConfig:
    """Configuration for debate-level train/validation/test splitting."""
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    random_seed: int = 42

    def __post_init__(self) -> None:
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-4:
            raise ValueError(
                f"Split ratios must sum to 1.0 (got {self.train_ratio} + "
                f"{self.val_ratio} + {self.test_ratio} = {total})"
            )
        if any(r <= 0 for r in (self.train_ratio, self.val_ratio, self.test_ratio)):
            raise ValueError("All split ratios must be strictly positive.")


@dataclass
class TFIDFConfig:
    """Hyperparameter configuration for TF-IDF + Logistic Regression baseline."""
    ngram_range: Tuple[int, int] = (1, 2)
    min_df: int = 2
    max_features: int = 10000
    sublinear_tf: bool = True
    C: float = 1.0
    class_weight: Optional[str] = "balanced"
    max_iter: int = 1000
    random_state: int = 42
    solver: str = "lbfgs"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "ngram_range": list(self.ngram_range),
            "min_df": self.min_df,
            "max_features": self.max_features,
            "sublinear_tf": self.sublinear_tf,
            "C": self.C,
            "class_weight": self.class_weight,
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "solver": self.solver,
        }


@dataclass
class TransformerConfig:
    """Hyperparameter configuration for Transformer sequence classifier."""
    model_name: str = "roberta-base"
    max_length: int = 256
    batch_size: int = 16
    learning_rate: float = 2e-5
    epochs: int = 3
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    random_seed: int = 42
    output_dir: str = "models/component_classifier"
    device: str = field(default_factory=get_available_device)
    use_class_weights: bool = True

    def __post_init__(self) -> None:
        if self.max_length <= 0:
            raise ValueError(f"max_length must be positive (got {self.max_length})")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive (got {self.batch_size})")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive (got {self.learning_rate})")
        if self.epochs <= 0:
            raise ValueError(f"epochs must be positive (got {self.epochs})")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model_name": self.model_name,
            "max_length": self.max_length,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "weight_decay": self.weight_decay,
            "warmup_ratio": self.warmup_ratio,
            "random_seed": self.random_seed,
            "output_dir": self.output_dir,
            "device": self.device,
            "use_class_weights": self.use_class_weights,
        }


@dataclass
class ExperimentRecord:
    """Lightweight metadata tracking for reproducible experiment runs."""
    experiment_id: str
    model_name: str
    dataset_version: str
    dataset_split_seed: int
    hyperparameters: Dict[str, Any]
    training_date: str
    device: str
    number_of_train_samples: int
    number_of_validation_samples: int
    number_of_test_samples: int
    metrics: Dict[str, Any]
    status: str = "COMPLETED"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "model_name": self.model_name,
            "dataset_version": self.dataset_version,
            "dataset_split_seed": self.dataset_split_seed,
            "hyperparameters": self.hyperparameters,
            "training_date": self.training_date,
            "device": self.device,
            "number_of_train_samples": self.number_of_train_samples,
            "number_of_validation_samples": self.number_of_validation_samples,
            "number_of_test_samples": self.number_of_test_samples,
            "metrics": self.metrics,
            "status": self.status,
            "notes": self.notes,
        }
