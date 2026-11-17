"""Deterministic Text Normalization for ARGUMAP.

Normalizes layout and formatting artifacts (line endings, excessive whitespace,
non-breaking spaces, unicode quotes) while strictly preserving punctuation,
capitalization, numbers, citations, and semantic tokens.
"""

import re
import unicodedata
from typing import Tuple


# Mapping for smart quotes and typographic dashes to standard unicode/ASCII
TYPOGRAPHIC_REPLACEMENTS = {
    "\u2018": "'",  # Left single quote
    "\u2019": "'",  # Right single quote / apostrophe
    "\u201c": '"',  # Left double quote
    "\u201d": '"',  # Right double quote
    "\u2014": " -- ",  # Em dash
    "\u2013": " - ",   # En dash
    "\u00a0": " ",     # Non-breaking space
    "\u2026": "...",   # Ellipsis
}


class TextNormalizer:
    """Provides deterministic, safe text normalization for debate transcripts."""

    @staticmethod
    def normalize_line_endings(text: str) -> str:
        """Converts Windows (CRLF) and legacy Mac (CR) line endings to Unix (LF)."""
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def normalize_unicode_punctuation(text: str) -> str:
        """Replaces idiosyncratic typographic characters with standardized forms."""
        # Unicode NFKC normalization decomposes compatibility characters
        normalized = unicodedata.normalize("NFKC", text)
        for original, replacement in TYPOGRAPHIC_REPLACEMENTS.items():
            normalized = normalized.replace(original, replacement)
        return normalized

    @staticmethod
    def collapse_whitespace(text: str) -> str:
        """Collapses runs of spaces and tabs while preserving newline boundaries."""
        # Collapse multiple spaces/tabs within lines
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            # Strip trailing space and collapse multiple internal spaces
            cleaned = re.sub(r"[ \t]+", " ", line).strip()
            cleaned_lines.append(cleaned)
        
        # Join lines back
        result = "\n".join(cleaned_lines)
        # Collapse more than 2 consecutive blank lines
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result

    @classmethod
    def normalize(cls, raw_text: str) -> str:
        """Executes the full safe deterministic normalization pipeline.
        
        Preserves:
        - All punctuation (periods, commas, colons, question marks, exclamation marks)
        - Full capitalization and casing
        - Numerical figures, percentages, dates
        - Quotation marks and parentheses
        """
        if not raw_text:
            return ""

        text = cls.normalize_line_endings(raw_text)
        text = cls.normalize_unicode_punctuation(text)
        text = cls.collapse_whitespace(text)
        return text.strip()


def normalize_transcript(text: str) -> str:
    """Convenience functional wrapper for TextNormalizer.normalize."""
    return TextNormalizer.normalize(text)
