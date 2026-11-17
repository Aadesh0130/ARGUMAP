"""US2016 Debate Corpus Converter.

Converts US2016 televised presidential debate transcript records into
ARGUMAP NormalizedUnits with speaker attribution, preserving native labels.
"""

from pathlib import Path
from typing import List, Dict, Any
from .base_converter import BaseCorpusConverter, NormalizedUnit, ProvenanceRecord


class US2016Converter(BaseCorpusConverter):
    """Converter for the US2016 Presidential Debates corpus (Visser et al. / Menini et al.)."""

    def __init__(self):
        super().__init__(corpus_id="us2016", conversion_version="1.0.0")

    def load_raw(self, raw_path: Path) -> List[Dict[str, Any]]:
        """Parses US2016 JSON/text structure."""
        import json
        if not raw_path.exists():
            return []
        with open(raw_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def convert(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedUnit]:
        """Transforms raw debate turns/propositions into NormalizedUnits."""
        normalized_units = []

        for item in raw_data:
            doc_id = item.get("debate_id", "us2016_debate")
            turn_id = item.get("turn_id", "turn_0")
            speaker = item.get("speaker", "Unknown")
            unit_id = item.get("unit_id", "u_0")
            native_label = item.get("native_label", "Assertion")
            text = item.get("text", "")

            provenance = ProvenanceRecord(
                source_corpus="us2016",
                source_document_id=doc_id,
                source_license="UNVERIFIED",
                source_url="https://corpora.aifdb.org/US2016",
                source_label=native_label,
                conversion_version=self.conversion_version,
            )

            unit = NormalizedUnit(
                source_corpus="us2016",
                document_id=doc_id,
                speaker_id=speaker,
                turn_id=turn_id,
                unit_id=f"us2016_{doc_id}_{unit_id}",
                text=text,
                source_label=native_label,  # Preserves IAT native label!
                source_relation=item.get("native_relation"),
                metadata={
                    "genre": "televised_debate",
                    "multi_party": True,
                },
                provenance=provenance,
            )
            normalized_units.append(unit)

        return normalized_units
