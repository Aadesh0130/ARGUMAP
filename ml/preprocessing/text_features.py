"""Text feature extraction for ARGUMAP baseline classification models."""

from pathlib import Path
from typing import List, Optional, Sequence, Union
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from ml.config import TFIDFConfig


class TFIDFFeatureExtractor:
    """Configurable TF-IDF feature extractor for argument propositions."""

    def __init__(self, config: Optional[TFIDFConfig] = None) -> None:
        self.config = config or TFIDFConfig()
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.config.ngram_range,
            min_df=self.config.min_df,
            max_features=self.config.max_features,
            sublinear_tf=self.config.sublinear_tf,
        )
        self.is_fitted: bool = False

    def fit(self, texts: Sequence[str]) -> "TFIDFFeatureExtractor":
        """Fit the vectorizer on a sequence of argument proposition strings."""
        if not texts:
            raise ValueError("Cannot fit TFIDF vectorizer on empty text collection.")
        self.vectorizer.fit(texts)
        self.is_fitted = True
        return self

    def transform(self, texts: Sequence[str]):
        """Transform texts into TF-IDF sparse matrix."""
        if not self.is_fitted:
            raise RuntimeError("TFIDFFeatureExtractor must be fitted before transform.")
        return self.vectorizer.transform(texts)

    def fit_transform(self, texts: Sequence[str]):
        """Fit and transform in one step."""
        if not texts:
            raise ValueError("Cannot fit_transform TFIDF vectorizer on empty text collection.")
        sparse_mat = self.vectorizer.fit_transform(texts)
        self.is_fitted = True
        return sparse_mat

    @property
    def vocabulary_size(self) -> int:
        """Return the size of the learned vocabulary."""
        if not self.is_fitted:
            return 0
        return len(self.vectorizer.vocabulary_)

    def save(self, filepath: Union[str, Path]) -> None:
        """Persist fitted vectorizer to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "TFIDFFeatureExtractor":
        """Load persisted vectorizer from disk."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Vectorizer file not found: {path}")
        vectorizer = joblib.load(path)
        extractor = cls()
        extractor.vectorizer = vectorizer
        extractor.is_fitted = True
        return extractor
