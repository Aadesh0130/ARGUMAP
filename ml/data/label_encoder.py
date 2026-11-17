"""Label encoding and validation for ARGUMAP 6-class component classification.

Frozen taxonomy:
    CLAIM
    PREMISE
    EVIDENCE
    COUNTERARGUMENT
    REBUTTAL
    OTHER
"""

from typing import Dict, List, Sequence


FROZEN_COMPONENT_LABELS: List[str] = [
    "CLAIM",
    "PREMISE",
    "EVIDENCE",
    "COUNTERARGUMENT",
    "REBUTTAL",
    "OTHER",
]

_LABEL_TO_ID: Dict[str, int] = {
    label: idx for idx, label in enumerate(FROZEN_COMPONENT_LABELS)
}
_ID_TO_LABEL: Dict[int, str] = {
    idx: label for idx, label in enumerate(FROZEN_COMPONENT_LABELS)
}


def validate_component_label(label: str) -> None:
    """Validate that a label belongs strictly to the frozen ARGUMAP taxonomy.

    Args:
        label: The string component label to validate.

    Raises:
        ValueError: If label is not in FROZEN_COMPONENT_LABELS.
    """
    if label not in _LABEL_TO_ID:
        allowed = ", ".join(FROZEN_COMPONENT_LABELS)
        raise ValueError(
            f"Invalid argument component label '{label}'. "
            f"Must be one of the frozen ARGUMAP classes: [{allowed}]."
        )


class ComponentLabelEncoder:
    """Deterministic bidirectional label encoder for ARGUMAP component taxonomy."""

    def __init__(self) -> None:
        self.labels: List[str] = list(FROZEN_COMPONENT_LABELS)
        self.label_to_id: Dict[str, int] = dict(_LABEL_TO_ID)
        self.id_to_label: Dict[int, str] = dict(_ID_TO_LABEL)
        self.num_classes: int = len(self.labels)

    def encode(self, label: str) -> int:
        """Encode a single component string label to integer ID.

        Fails loudly on invalid labels.
        """
        validate_component_label(label)
        return self.label_to_id[label]

    def decode(self, label_id: int) -> str:
        """Decode an integer class ID to string component label."""
        if label_id not in self.id_to_label:
            raise ValueError(
                f"Invalid label ID '{label_id}'. Must be in range 0..{self.num_classes - 1}."
            )
        return self.id_to_label[label_id]

    def encode_batch(self, labels: Sequence[str]) -> List[int]:
        """Encode a batch of string labels, validating each."""
        return [self.encode(lbl) for lbl in labels]

    def decode_batch(self, label_ids: Sequence[int]) -> List[str]:
        """Decode a batch of integer label IDs."""
        return [self.decode(idx) for idx in label_ids]

    @classmethod
    def get_labels(cls) -> List[str]:
        """Return a copy of the canonical frozen label sequence."""
        return list(FROZEN_COMPONENT_LABELS)
