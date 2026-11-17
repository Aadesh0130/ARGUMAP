"""Argument Annotated Essays (AAE v2) Corpus Converter.

Converts AAE raw standoff annotations into ARGUMAP NormalizedUnits,
strictly preserving native labels ('MajorClaim', 'Claim', 'Premise') and recording provenance.
"""

from pathlib import Path
from typing import List, Dict, Any
from .base_converter import BaseCorpusConverter, NormalizedUnit, ProvenanceRecord


class AAEConverter(BaseCorpusConverter):
    """Converter for the Argument Annotated Essays v2 corpus (Stab & Gurevych, 2017)."""

    def __init__(self):
        super().__init__(corpus_id="aae", conversion_version="1.0.0")

    def load_raw(self, raw_path: Path) -> List[Dict[str, Any]]:
        """Parses AAE standoff annotation text files or mocked records for testing."""
        # Standalone parser reading tab-separated standoff records: ID, Label Start End, Text
        records = []
        if not raw_path.exists():
            return records

        with open(raw_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    unit_id = parts[0]
                    type_info = parts[1].split()
                    label = type_info[0]
                    text = parts[2]
                    records.append({
                        "unit_id": unit_id,
                        "label": label,
                        "text": text,
                        "doc_id": raw_path.stem
                    })
        return records

    def convert(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedUnit]:
        """Transforms raw records into NormalizedUnit objects preserving source labels."""
        normalized_units = []
        for item in raw_data:
            doc_id = item.get("doc_id", "aae_doc")
            unit_id = item.get("unit_id", "u_0")
            source_label = item.get("label", "Unknown")
            text = item.get("text", "")

            provenance = ProvenanceRecord(
                source_corpus="aae",
                source_document_id=doc_id,
                source_license="UNVERIFIED",
                source_url="https://www.ukp.tu-darmstadt.de/data/argument-mining/argument-annotated-essays-version-2/",
                source_label=source_label,
                conversion_version=self.conversion_version,
            )

            unit = NormalizedUnit(
                source_corpus="aae",
                document_id=doc_id,
                speaker_id="Author_Essay",
                turn_id=f"{doc_id}_turn_0",
                unit_id=f"aae_{doc_id}_{unit_id}",
                text=text,
                source_label=source_label,  # Strictly native AAE label!
                source_relation=None,
                metadata={
                    "genre": "persuasive_essay",
                    "monologic": True,
                },
                provenance=provenance,
            )
            normalized_units.append(unit)

        return normalized_units
