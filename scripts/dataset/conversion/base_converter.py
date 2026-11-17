"""Base Converter and Intermediate Representation for ARGUMAP Datasets.

Enforces:
1. Strict preservation of native upstream labels (no silent re-labeling).
2. Complete provenance tracking (traceability back to original document and license).
3. Standardized intermediate representation for downstream analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional
import json


@dataclass
class ProvenanceRecord:
    """Detailed scientific provenance for an argument unit."""
    source_corpus: str
    source_document_id: str
    source_license: str
    source_url: str
    source_label: str
    conversion_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedUnit:
    """Standardized intermediate representation for argument units."""
    source_corpus: str
    document_id: str
    speaker_id: str
    turn_id: str
    unit_id: str
    text: str
    source_label: str
    source_relation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Optional[ProvenanceRecord] = None

    def __post_init__(self):
        if self.provenance is None:
            self.provenance = ProvenanceRecord(
                source_corpus=self.source_corpus,
                source_document_id=self.document_id,
                source_license=self.metadata.get("source_license", "UNVERIFIED"),
                source_url=self.metadata.get("source_url", ""),
                source_label=self.source_label,
            )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.provenance:
            data["provenance"] = self.provenance.to_dict()
        return data


class BaseCorpusConverter(ABC):
    """Abstract base class for external corpus converters."""

    def __init__(self, corpus_id: str, conversion_version: str = "1.0.0"):
        self.corpus_id = corpus_id
        self.conversion_version = conversion_version

    @abstractmethod
    def load_raw(self, raw_path: Path) -> Any:
        """Loads and parses raw upstream data."""
        pass

    @abstractmethod
    def convert(self, raw_data: Any) -> List[NormalizedUnit]:
        """Converts raw data into a list of NormalizedUnits, strictly preserving source labels."""
        pass

    def export_intermediate(self, units: List[NormalizedUnit], output_path: Path) -> None:
        """Exports normalized units to an intermediate JSONL or JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for unit in units:
                f.write(json.dumps(unit.to_dict(), ensure_ascii=False) + "\n")
