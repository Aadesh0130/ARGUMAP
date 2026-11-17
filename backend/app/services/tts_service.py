"""
tts_service.py — Text-to-Speech Service for ARGUMAP (optional voice layer).

Generates spoken MP3 audio from plain text using gTTS (Google TTS).
Falls back gracefully when gTTS is not installed so the rest of the
application continues to function without the voice feature.

Usage
-----
    from app.services.tts_service import tts_service

    path = tts_service.synthesize("Speaker A claims that climate policy is overdue.")
    # returns absolute path to the .mp3 file, or raises TTSUnavailableError
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Availability check — gTTS is an optional dependency
# ---------------------------------------------------------------------------
try:
    from gtts import gTTS  # type: ignore
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False


class TTSUnavailableError(RuntimeError):
    """Raised when gTTS is not installed and TTS synthesis is requested."""


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------

_TTS_DIR = Path(__file__).parents[2] / "static" / "tts"


class TTSService:
    """Lightweight wrapper around gTTS for ARGUMAP voice output."""

    def __init__(self, output_dir: Optional[Path] = None, lang: str = "en"):
        self._dir = output_dir or _TTS_DIR
        self._lang = lang
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @property
    def available(self) -> bool:
        """True when gTTS is installed and TTS synthesis can proceed."""
        return _GTTS_AVAILABLE

    def synthesize(self, text: str, lang: Optional[str] = None) -> str:
        """Convert *text* to speech and save as an MP3 file.

        Parameters
        ----------
        text:
            Plain text to be spoken.  Markdown and HTML are NOT stripped
            automatically — callers should pass clean text.
        lang:
            BCP-47 language code (e.g. ``"en"``, ``"hi"``).  Defaults to
            the value set at construction time.

        Returns
        -------
        str
            Absolute path to the generated ``.mp3`` file.

        Raises
        ------
        TTSUnavailableError
            When the ``gtts`` package is not installed.
        ValueError
            When *text* is empty.
        """
        if not _GTTS_AVAILABLE:
            raise TTSUnavailableError(
                "gTTS is not installed. Run: pip install gtts>=2.5.0"
            )
        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text.")

        effective_lang = lang or self._lang
        # Deterministic filename so identical text reuses cached audio
        digest = hashlib.sha256(f"{effective_lang}:{text}".encode()).hexdigest()[:16]
        filename = f"tts_{digest}.mp3"
        out_path = self._dir / filename

        if not out_path.exists():
            tts = gTTS(text=text.strip(), lang=effective_lang)
            tts.save(str(out_path))

        return str(out_path)

    def synthesize_analysis(
        self,
        speakers: list[dict],
        arguments: list[dict],
        insights: list[dict],
        lang: Optional[str] = None,
    ) -> str:
        """Generate a spoken summary of an analysis result.

        Builds a natural-language narrative from the structured analysis
        payload (speakers, argument units, insights) and synthesizes it.

        Returns
        -------
        str
            Absolute path to the generated ``.mp3`` file.
        """
        lines: list[str] = []

        if speakers:
            names = ", ".join(s.get("name", "Unknown") for s in speakers)
            lines.append(f"This debate involves {len(speakers)} speaker(s): {names}.")

        if arguments:
            type_counts: dict[str, int] = {}
            for arg in arguments:
                ct = arg.get("component_type", "OTHER")
                type_counts[ct] = type_counts.get(ct, 0) + 1
            breakdown = "; ".join(f"{v} {k.lower()}(s)" for k, v in type_counts.items())
            lines.append(
                f"The analysis identified {len(arguments)} argument unit(s): {breakdown}."
            )

        if insights:
            warnings = [i for i in insights if i.get("severity") == "WARNING"]
            if warnings:
                lines.append(
                    f"There are {len(warnings)} structural warning(s). "
                    + " ".join(w.get("message", "") for w in warnings[:3])
                )
            else:
                lines.append("No structural warnings were detected.")

        narrative = " ".join(lines) or "No analysis data available."
        return self.synthesize(narrative, lang=lang)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

tts_service = TTSService()
