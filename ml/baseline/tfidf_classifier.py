"""TF-IDF + Logistic Regression baseline classifier for ARGUMAP component taxonomy."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from ml.config import TFIDFConfig
from ml.data.dataset_loader import ArgumentUnitSample
from ml.data.label_encoder import FROZEN_COMPONENT_LABELS, ComponentLabelEncoder
from ml.preprocessing.text_features import TFIDFFeatureExtractor


class TFIDFBaselineClassifier:
    """Baseline classifier combining n-gram TF-IDF and multinomial Logistic Regression."""

    def __init__(self, config: Optional[TFIDFConfig] = None) -> None:
        self.config = config or TFIDFConfig()
        self.feature_extractor = TFIDFFeatureExtractor(self.config)
        self.label_encoder = ComponentLabelEncoder()
        self.classifier = LogisticRegression(
            C=self.config.C,
            class_weight=self.config.class_weight,
            random_state=self.config.random_state,
            max_iter=self.config.max_iter,
            solver=self.config.solver,
        )
        self.is_trained: bool = False

    def fit(self, samples: Sequence[ArgumentUnitSample]) -> "TFIDFBaselineClassifier":
        """Fit the TF-IDF feature extractor and Logistic Regression classifier."""
        if not samples:
            raise ValueError("Cannot train baseline classifier on empty sample collection.")

        texts = [s.text for s in samples]
        y_labels = [s.component_label for s in samples]

        # Check unique classes in training data
        unique_classes = sorted(list(set(y_labels)))
        if len(unique_classes) < 2:
            raise ValueError(
                f"Training requires at least 2 distinct classes to fit Logistic Regression (got {unique_classes})."
            )

        # Encode labels
        y_indices = self.label_encoder.encode_batch(y_labels)

        # Fit and transform features
        x_features = self.feature_extractor.fit_transform(texts)

        # Fit classifier
        self.classifier.fit(x_features, y_indices)
        self.is_trained = True
        return self

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

    def predict(
        self, samples_or_texts: Sequence[Union[ArgumentUnitSample, str]]
    ) -> List[str]:
        """Predict component label strings for given samples or texts."""
        if not self.is_trained:
            raise RuntimeError("Classifier must be trained before predicting.")
        texts = self._extract_texts(samples_or_texts)
        if not texts:
            return []
        x_features = self.feature_extractor.transform(texts)
        pred_indices = self.classifier.predict(x_features)
        return self.label_encoder.decode_batch(pred_indices)

    def predict_proba(
        self, samples_or_texts: Sequence[Union[ArgumentUnitSample, str]]
    ) -> np.ndarray:
        """Predict probability distribution over frozen labels."""
        if not self.is_trained:
            raise RuntimeError("Classifier must be trained before predicting probabilities.")
        texts = self._extract_texts(samples_or_texts)
        if not texts:
            return np.empty((0, self.label_encoder.num_classes))
        x_features = self.feature_extractor.transform(texts)
        probs = self.classifier.predict_proba(x_features)

        # Align probabilities if classifier only saw a subset of classes during fit
        if probs.shape[1] < self.label_encoder.num_classes:
            full_probs = np.zeros((len(texts), self.label_encoder.num_classes))
            for i, class_idx in enumerate(self.classifier.classes_):
                full_probs[:, class_idx] = probs[:, i]
            return full_probs
        return probs

    def save(self, output_dir: Union[str, Path]) -> None:
        """Serialize baseline model, feature extractor, configuration, and label mapping."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Save artifacts
        joblib.dump(self.classifier, out / "logistic_regression.joblib")
        self.feature_extractor.save(out / "tfidf_vectorizer.joblib")

        # Save config
        with open(out / "config.json", "w", encoding="utf-8") as f:
            json.dump(self.config.to_dict(), f, indent=2)

        # Save label mapping
        with open(out / "label_mapping.json", "w", encoding="utf-8") as f:
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
    def load(cls, model_dir: Union[str, Path]) -> "TFIDFBaselineClassifier":
        """Load trained baseline model from directory."""
        path = Path(model_dir)
        if not path.exists():
            raise FileNotFoundError(f"Model directory not found: {path}")

        config_file = path / "config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            config = TFIDFConfig(
                ngram_range=tuple(cfg_data.get("ngram_range", [1, 2])),
                min_df=cfg_data.get("min_df", 2),
                max_features=cfg_data.get("max_features", 10000),
                sublinear_tf=cfg_data.get("sublinear_tf", True),
                C=cfg_data.get("C", 1.0),
                class_weight=cfg_data.get("class_weight", "balanced"),
                max_iter=cfg_data.get("max_iter", 1000),
                random_state=cfg_data.get("random_state", 42),
                solver=cfg_data.get("solver", "lbfgs"),
            )
        else:
            config = TFIDFConfig()

        instance = cls(config)
        instance.classifier = joblib.load(path / "logistic_regression.joblib")
        instance.feature_extractor = TFIDFFeatureExtractor.load(path / "tfidf_vectorizer.joblib")
        instance.is_trained = True
        return instance
