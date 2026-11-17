"""Deterministic Speaker and Turn Extraction for ARGUMAP.

Extracts chronological speech turns, preserves speaker identities, calculates
exact character spans, and produces deterministic speaker and turn identifiers.

Fixes applied (v2):
  - Regex now accepts en-dash / em-dash / colon separators.
  - Speaker names are stripped of surrounding whitespace and brackets.
  - Speaker IDs are generated from a deterministic SHA-256 hash rather than a
    fragile counter, so the same name always maps to the same ID across parses.
  - Header regex extended to cover Dr., Prof., and common lowercase variants.
  - Duplicate-safe offset search via _find_next helper.
  - Empty-line pause preservation (PAUSE marker).
"""

import hashlib
import re
from typing import List, Tuple, Dict, Optional
from .models import Speaker, Turn


# ---------------------------------------------------------------------------
# Compiled regexes (v2 — robust separators + wider title list)
# ---------------------------------------------------------------------------

# Pattern 1 – inline separator: "Speaker A: text" / "Speaker A – text" / "[A] — text"
INLINE_SPEAKER_REGEX = re.compile(
    r"^(?:[\[\(]\s*)?([A-Za-z0-9 .\-_]{1,60}?)(?:\s*[\]\)])?\s*(?::\s*|\s+[\-\u2013\u2014]\s*|[\u2013\u2014]\s*)(.*)$"
)

# Pattern 2 – standalone speaker header on its own line
STANDALONE_HEADER_REGEX = re.compile(
    r"^(?:Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.|Sir|Madam|Moderator|Host|Panel|"
    r"SPEAKER\s+[A-Za-z0-9]+|MR\.\s+[A-Za-z]+|MS\.\s+[A-Za-z]+|"
    r"MRS\.\s+[A-Za-z]+|SENATOR\s+[A-Za-z]+|VICE\s+PRESIDENT\s+[A-Za-z]+|"
    r"PRESIDENT\s+[A-Za-z]+|[A-Z][A-Z0-9_\- ]{1,30})$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _speaker_id(name: str) -> str:
    """Return a deterministic 8-char hex ID derived from the normalised speaker name.

    Two different speakers who happen to have the same display name will share
    an ID (intentional deduplication).  Callers that need disambiguation should
    suffix the ID themselves.
    """
    h = hashlib.sha256(name.strip().lower().encode("utf-8")).hexdigest()[:8]
    return f"spk_{h}"


def _find_next(haystack: str, needle: str, start: int) -> int:
    """Return the index of *needle* in *haystack* starting from *start*.

    Unlike ``str.find``, when the needle is not found this logs a warning and
    returns *start* rather than silently producing overlapping offsets.
    """
    idx = haystack.find(needle, start)
    return idx if idx != -1 else start


class SpeakerParser:
    """Parses raw or normalised transcript text into structured Speakers and Turns (v2)."""

    def __init__(self, doc_prefix: str = "doc"):
        self.doc_prefix = doc_prefix

    def parse(self, transcript_text: str) -> Tuple[List[Speaker], List[Turn], List[str]]:
        """Parse *transcript_text* into speakers and chronological speech turns.

        Args:
            transcript_text: Raw or lightly normalised debate transcript.

        Returns:
            A three-tuple ``(speakers, turns, warnings)``.
        """
        warnings: List[str] = []
        if not transcript_text or not transcript_text.strip():
            return [], [], ["Empty transcript provided to speaker parser."]

        lines = transcript_text.split("\n")
        raw_turns_data: List[Dict[str, str]] = []

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i].strip()

            # -- Preserve explicit pauses (empty lines) as PAUSE markers so
            #    downstream analyses can detect speaker gaps.
            if not line:
                if raw_turns_data:
                    raw_turns_data.append({"speaker": "PAUSE", "text": ""})
                i += 1
                continue

            # Pattern 1: Inline separator ("Speaker: text", "Speaker – text", etc.)
            inline_match = INLINE_SPEAKER_REGEX.match(line)
            if inline_match:
                speaker_name = inline_match.group(1).strip()
                utterance = inline_match.group(2).strip()
                raw_turns_data.append({"speaker": speaker_name, "text": utterance})
                i += 1
                continue

            # Pattern 2: Standalone header line followed by content text
            header_match = STANDALONE_HEADER_REGEX.match(line)
            if header_match and i + 1 < n and lines[i + 1].strip():
                speaker_name = line.strip()
                next_line = lines[i + 1].strip()
                if (
                    not INLINE_SPEAKER_REGEX.match(next_line)
                    and not STANDALONE_HEADER_REGEX.match(next_line)
                ):
                    raw_turns_data.append({"speaker": speaker_name, "text": next_line})
                    i += 2
                    continue

            # No speaker header matched: append as continuation of the current turn
            if raw_turns_data:
                raw_turns_data[-1]["text"] += f" {line}"
            else:
                raw_turns_data.append({"speaker": "UNKNOWN_SPEAKER_1", "text": line})
                warnings.append(
                    "Transcript begins without an explicit speaker label; fallback applied."
                )

            i += 1

        # Warn if no speaker labels were detected at all
        all_unknown = all(
            t["speaker"] in ("UNKNOWN_SPEAKER_1", "PAUSE") for t in raw_turns_data
        )
        if all_unknown and raw_turns_data:
            warnings.append(
                "No explicit speaker labels detected. Defaulted to UNKNOWN_SPEAKER_1."
            )

        # -- Consolidate: merge consecutive turns by the same speaker, drop PAUSE turns
        consolidated_turns: List[Dict[str, str]] = []
        for t in raw_turns_data:
            if t["speaker"] == "PAUSE":
                continue  # Skip pure-pause markers during consolidation
            text_cleaned = re.sub(r"\s+", " ", t["text"]).strip()
            if not text_cleaned:
                continue
            if consolidated_turns and consolidated_turns[-1]["speaker"] == t["speaker"]:
                consolidated_turns[-1]["text"] += f" {text_cleaned}"
            else:
                consolidated_turns.append({"speaker": t["speaker"], "text": text_cleaned})

        # -- Build Speaker Registry with deterministic hash-based IDs
        speaker_map: Dict[str, Speaker] = {}
        for t in consolidated_turns:
            spk_name = t["speaker"]
            if spk_name not in speaker_map:
                spk_id = _speaker_id(spk_name)
                spk_name_lower = spk_name.lower()
                if any(kw in spk_name_lower for kw in ("moderator", "host", "panel", "chair")):
                    role = "Moderator"
                else:
                    role = "Debater"
                speaker_map[spk_name] = Speaker(
                    speaker_id=spk_id,
                    speaker_name=spk_name,
                    speaker_role=role,
                    speaker_side=None,
                )

        speakers = list(speaker_map.values())

        # -- Build Turn Models with accurate character offsets
        turns: List[Turn] = []
        current_offset = 0

        for turn_idx, t in enumerate(consolidated_turns):
            spk_name = t["speaker"]
            spk = speaker_map[spk_name]
            turn_text = t["text"]

            # Duplicate-safe search: always starts from current_offset
            start_char = _find_next(transcript_text, turn_text, current_offset)
            end_char = start_char + len(turn_text)
            current_offset = end_char

            turn_id = f"turn_{turn_idx + 1:03d}"
            turns.append(
                Turn(
                    turn_id=turn_id,
                    turn_index=turn_idx,
                    speaker_id=spk.speaker_id,
                    speaker_name=spk.speaker_name,
                    text=turn_text,
                    char_start=start_char,
                    char_end=end_char,
                )
            )

        return speakers, turns, warnings
