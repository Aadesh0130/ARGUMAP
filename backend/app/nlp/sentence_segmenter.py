"""Deterministic Sentence Segmentation for ARGUMAP.

Segments speech turns into sequential sentences, handles standard abbreviations,
initials, decimals, and quotation marks, while computing exact character offsets.
"""

import re
from typing import List, Dict, Any


# Standard English abbreviations that do NOT trigger sentence boundaries
COMMON_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr",
    "sen", "rep", "gov", "pres", "gen", "col", "capt", "sgt",
    "u.s", "u.k", "e.u", "u.n", "u.s.a",
    "e.g", "i.e", "etc", "vs", "al", "approx", "est",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "no", "fig", "sec", "vol",
}


class SentenceSegmenter:
    """Deterministic, offset-preserving sentence segmenter."""

    @staticmethod
    def is_abbreviation_or_number(text: str, period_idx: int) -> bool:
        """Determines if a period at period_idx is an abbreviation, decimal, or initial."""
        # 1. Check for decimal number: e.g. "3.14", "0.5%"
        if period_idx > 0 and period_idx + 1 < len(text):
            if text[period_idx - 1].isdigit() and text[period_idx + 1].isdigit():
                return True

        # 2. Check for ellipsis: e.g. "..."
        if period_idx > 0 and text[period_idx - 1] == ".":
            return True
        if period_idx + 1 < len(text) and text[period_idx + 1] == ".":
            return True

        # 3. Extract preceding word
        start = period_idx - 1
        while start >= 0 and (text[start].isalnum() or text[start] == "."):
            start -= 1
        preceding_word = text[start + 1:period_idx].lower()

        # Check against abbreviation dictionary
        if preceding_word in COMMON_ABBREVIATIONS:
            return True
        if f"{preceding_word}." in COMMON_ABBREVIATIONS:
            return True

        # 4. Check for single-letter initial (e.g., "John F. Kennedy")
        if len(preceding_word) == 1 and preceding_word.isalpha():
            return True

        return False

    def segment(self, turn_text: str) -> List[Dict[str, Any]]:
        """Segments a turn into sentences with exact character offsets.
        
        Returns:
            List of dicts: [
                {"sentence_index": 0, "text": "...", "char_start": 0, "char_end": 45},
                ...
            ]
        """
        if not turn_text or not turn_text.strip():
            return []

        sentences: List[Dict[str, Any]] = []
        n = len(turn_text)
        sent_start = 0
        i = 0

        while i < n:
            char = turn_text[i]

            # Look for terminal sentence punctuation
            if char in {".", "!", "?"}:
                # Check for abbreviation or decimal if period
                if char == "." and self.is_abbreviation_or_number(turn_text, i):
                    i += 1
                    continue

                # Handle closing quotes or brackets immediately after punctuation
                end_idx = i + 1
                while end_idx < n and turn_text[end_idx] in {'"', "'", "”", "’", ")", "]"}:
                    end_idx += 1

                # Check if this boundary is followed by whitespace + capital letter, or end of text
                is_boundary = False
                if end_idx >= n:
                    is_boundary = True
                elif turn_text[end_idx].isspace():
                    # Look ahead to see if the next non-space is uppercase, quote, or number
                    peek = end_idx
                    while peek < n and turn_text[peek].isspace():
                        peek += 1
                    if peek >= n or turn_text[peek].isupper() or turn_text[peek] in {'"', "'", "“"}:
                        is_boundary = True

                if is_boundary:
                    candidate_span = turn_text[sent_start:end_idx]
                    trimmed_text = candidate_span.strip()

                    if trimmed_text:
                        # Compute exact trimmed offsets
                        offset_in_span = candidate_span.find(trimmed_text)
                        actual_start = sent_start + offset_in_span
                        actual_end = actual_start + len(trimmed_text)

                        sentences.append({
                            "sentence_index": len(sentences),
                            "text": trimmed_text,
                            "char_start": actual_start,
                            "char_end": actual_end,
                        })

                    # Advance to next sentence start
                    sent_start = end_idx
                    while sent_start < n and turn_text[sent_start].isspace():
                        sent_start += 1
                    i = sent_start
                    continue

            i += 1

        # Any trailing remainder
        if sent_start < n:
            candidate_span = turn_text[sent_start:n]
            trimmed_text = candidate_span.strip()
            if trimmed_text:
                offset_in_span = candidate_span.find(trimmed_text)
                actual_start = sent_start + offset_in_span
                actual_end = actual_start + len(trimmed_text)

                sentences.append({
                    "sentence_index": len(sentences),
                    "text": trimmed_text,
                    "char_start": actual_start,
                    "char_end": actual_end,
                })

        return sentences
