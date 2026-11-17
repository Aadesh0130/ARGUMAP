"""Conservative Proposition / Clause Segmentation for ARGUMAP.

Implements conservative argumentative proposition segmentation aligned with
ANNOTATION_GUIDELINES.md:
- Sentence-level units are the primary default.
- Splitting into sub-sentence propositions occurs strictly for clear,
  independently meaningful coordinated clauses.
- Preserves exact character spans relative to the parent turn text.
- component_label remains strictly None.
"""

import re
from typing import List, Dict, Any
from .models import ArgumentUnit


# Coordinating conjunction patterns separating independent argumentative clauses
# e.g., "Clause A, and Clause B", "Clause A, but Clause B", "Clause A; however, Clause B"
COORDINATE_CLAUSE_SPLIT_REGEX = re.compile(
    r"^(?P<left>.+?)(?:,\s+(?:and|but|yet)|;\s*(?:however|moreover|furthermore|therefore),?)\s+(?P<right>.+)$",
    re.IGNORECASE | re.DOTALL
)

DEPENDENT_START_WORDS = {
    "because", "although", "though", "if", "when", "since", "unless", "while",
    "whereas", "wherein", "whereby", "as", "after", "before", "until",
    "in", "on", "at", "for", "with", "by", "without", "to", "from",
    "also", "too", "especially", "including",
}


class PropositionSegmenter:
    """Segments sentences into discrete argumentative proposition units."""

    @staticmethod
    def _is_independent_clause(clause_text: str) -> bool:
        """Determines if a candidate clause has sufficient length and independent structure."""
        words = clause_text.strip().split()
        if len(words) < 4:
            return False

        first_word = words[0].lower().strip(",.;:\"'")
        if first_word in DEPENDENT_START_WORDS:
            return False

        return True

    def segment_turn(
        self,
        document_id: str,
        turn_id: str,
        speaker_id: str,
        turn_index: int,
        turn_text: str,
        sentences: List[Dict[str, Any]],
        unit_offset_counter: int = 1,
    ) -> List[ArgumentUnit]:
        """Segments a turn's sentences into ArgumentUnit propositions.
        
        Preserves:
        - Exact character offsets matching turn_text[char_start:char_end] == unit.text
        - component_label == None
        """
        units: List[ArgumentUnit] = []
        current_unit_idx = unit_offset_counter

        for sent in sentences:
            sent_text = sent["text"]
            sent_start = sent["char_start"]
            sent_end = sent["char_end"]
            sent_idx = sent["sentence_index"]

            # Evaluate for conservative independent clause splitting
            match = COORDINATE_CLAUSE_SPLIT_REGEX.match(sent_text)
            should_split = False

            if match:
                left_clause = match.group("left").strip()
                right_clause = match.group("right").strip()

                if self._is_independent_clause(left_clause) and self._is_independent_clause(right_clause):
                    should_split = True

            if should_split and match:
                left_clause = match.group("left").strip()
                right_clause = match.group("right").strip()

                # Locate left clause span in turn_text
                left_start = turn_text.find(left_clause, sent_start)
                left_end = left_start + len(left_clause)

                # Locate right clause span in turn_text
                right_start = turn_text.find(right_clause, left_end)
                right_end = right_start + len(right_clause)

                # Unit 1 (Left clause)
                u1 = ArgumentUnit(
                    unit_id=f"u_{current_unit_idx:03d}",
                    document_id=document_id,
                    turn_id=turn_id,
                    speaker_id=speaker_id,
                    turn_index=turn_index,
                    unit_index=len(units),
                    text=left_clause,
                    char_start=left_start,
                    char_end=left_end,
                    sentence_index=sent_idx,
                    component_label=None,
                )
                units.append(u1)
                current_unit_idx += 1

                # Unit 2 (Right clause)
                u2 = ArgumentUnit(
                    unit_id=f"u_{current_unit_idx:03d}",
                    document_id=document_id,
                    turn_id=turn_id,
                    speaker_id=speaker_id,
                    turn_index=turn_index,
                    unit_index=len(units),
                    text=right_clause,
                    char_start=right_start,
                    char_end=right_end,
                    sentence_index=sent_idx,
                    component_label=None,
                )
                units.append(u2)
                current_unit_idx += 1

            else:
                # Default: Entire sentence is 1 argument unit
                u = ArgumentUnit(
                    unit_id=f"u_{current_unit_idx:03d}",
                    document_id=document_id,
                    turn_id=turn_id,
                    speaker_id=speaker_id,
                    turn_index=turn_index,
                    unit_index=len(units),
                    text=sent_text,
                    char_start=sent_start,
                    char_end=sent_end,
                    sentence_index=sent_idx,
                    component_label=None,
                )
                units.append(u)
                current_unit_idx += 1

        return units
