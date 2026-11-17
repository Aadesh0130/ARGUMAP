"""
Rule-based argument component classifier.

This is a heuristic bridge classifier used while gold-label data is being
collected for the full ML pipeline. It can be replaced by a trained model
without changing the calling interface.
"""

from __future__ import annotations

import hashlib
import random
import re

__all__ = ["RuleBasedComponentClassifier"]


class RuleBasedComponentClassifier:
    """Classify argument units into component types using hand-crafted rules.

    Rules are checked in priority order:
        EVIDENCE → COUNTERARGUMENT → REBUTTAL → PREMISE → CLAIM → OTHER

    Attributes:
        MODEL_VERSION: Version tag for the rule set.
    """

    MODEL_VERSION = "v1-rule-heuristic"

    # ------------------------------------------------------------------ #
    # Compiled patterns                                                    #
    # ------------------------------------------------------------------ #

    # EVIDENCE
    _RE_EVIDENCE_PERCENT = re.compile(r"\d+(\.\d+)?\s*%", re.IGNORECASE)
    _RE_EVIDENCE_STUDY = re.compile(
        r"\b(study|research|report|survey|data|statistics|found|showed|demonstrated)\b",
        re.IGNORECASE,
    )
    _RE_EVIDENCE_CITATION = re.compile(
        r"(according to|as cited|per the|et al\.?|journal|published)",
        re.IGNORECASE,
    )
    _RE_EVIDENCE_LARGE_NUM = re.compile(
        r"\b\d[\d,.]*\s*(million|billion|trillion)\b"
        r"|(million|billion|trillion)\s*[\w\s]{0,20}\d[\d,.]*",
        re.IGNORECASE,
    )
    _RE_EVIDENCE_YEAR_START = re.compile(r"^(in|a)\s+20\d{2}\b", re.IGNORECASE)

    # COUNTERARGUMENT
    _RE_COUNTER_START = re.compile(
        r"^.{0,30}(however|but|yet|on the other hand|nevertheless|despite"
        r"|contrary|opponents|critics|against|challenge)\b",
        re.IGNORECASE | re.DOTALL,
    )
    _RE_COUNTER_NEGATIVE = re.compile(
        r"\b(fails to|does not|cannot|won'?t|would not|ignores|overlooks|undermines)\b",
        re.IGNORECASE,
    )
    _RE_COUNTER_SUPPORT = re.compile(
        r"\b(supports?|proves?|demonstrates?|confirms?|validates?|evidence shows)\b",
        re.IGNORECASE,
    )

    # REBUTTAL
    _RE_REBUTTAL_CONCERN = re.compile(
        r"\b(this risk|this concern|this problem|this issue)\b",
        re.IGNORECASE,
    )
    _RE_REBUTTAL_CONTRARY = re.compile(
        r"\b(in fact|actually|on the contrary|while it is true)\b",
        re.IGNORECASE,
    )
    _RE_REBUTTAL_ADDRESSED = re.compile(
        r"\b(can be addressed|can be mitigated|can be reduced|can be managed)\b",
        re.IGNORECASE,
    )
    _RE_REBUTTAL_RESPONSE = re.compile(
        r"\b(responds to|addresses|refutes|counters)\b",
        re.IGNORECASE,
    )

    # PREMISE
    _RE_PREMISE = re.compile(
        r"\b(because|since|therefore|thus|hence|as a result|given that|due to"
        r"|enables|allows|provides|ensures)\b",
        re.IGNORECASE,
    )

    # CLAIM
    _RE_CLAIM_MODAL = re.compile(
        r"\b(should|must|ought to|is essential|is critical|is necessary|will|would)\b",
        re.IGNORECASE,
    )
    _RE_CLAIM_OPINION = re.compile(
        r"\b(argue|believe|contend|assert|maintain|propose|support)\b",
        re.IGNORECASE,
    )

    # OTHER — greetings / procedural
    _RE_OTHER_GREETING = re.compile(
        r"\b(thank you|good morning|good afternoon|please|welcome|today we"
        r"|i am here|my name)\b",
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------ #
    # Jitter helper                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _jitter(base: float, text: str) -> float:
        """Return *base* ± 0.03, deterministic based on a hash of *text*."""
        seed = int(hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest(), 16)
        rng = random.Random(seed)
        return round(base + rng.uniform(-0.03, 0.03), 4)

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def predict(self, text: str) -> tuple[str, float]:
        """Classify a single argument unit text.

        Args:
            text: Raw text of the argument unit.

        Returns:
            A ``(component_label, confidence_score)`` tuple.
        """
        label, base = self._classify(text)
        return label, self._jitter(base, text)

    def predict_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        """Classify a list of argument unit texts.

        Args:
            texts: List of raw argument unit strings.

        Returns:
            List of ``(component_label, confidence_score)`` pairs in the same
            order as *texts*.
        """
        return [self.predict(t) for t in texts]

    # ------------------------------------------------------------------ #
    # Internal rule engine                                                 #
    # ------------------------------------------------------------------ #

    def _classify(self, text: str) -> tuple[str, float]:
        """Apply rules in priority order and return ``(label, base_confidence)``."""

        # --- 1. EVIDENCE (0.82) ----------------------------------------
        if (
            self._RE_EVIDENCE_PERCENT.search(text)
            or self._RE_EVIDENCE_STUDY.search(text)
            or self._RE_EVIDENCE_CITATION.search(text)
            or self._RE_EVIDENCE_LARGE_NUM.search(text)
            or self._RE_EVIDENCE_YEAR_START.search(text)
        ):
            return "EVIDENCE", 0.82

        # --- 2. COUNTERARGUMENT (0.78) ----------------------------------
        counter_match = self._RE_COUNTER_START.search(
            text
        ) or self._RE_COUNTER_NEGATIVE.search(text)
        if counter_match:
            # Discount if strong support words are also present
            if not self._RE_COUNTER_SUPPORT.search(text):
                return "COUNTERARGUMENT", 0.78

        # --- 3. REBUTTAL (0.76) -----------------------------------------
        if (
            self._RE_REBUTTAL_CONCERN.search(text)
            or self._RE_REBUTTAL_CONTRARY.search(text)
            or self._RE_REBUTTAL_ADDRESSED.search(text)
            or self._RE_REBUTTAL_RESPONSE.search(text)
        ):
            return "REBUTTAL", 0.76

        # --- 4. PREMISE (0.74) ------------------------------------------
        if self._RE_PREMISE.search(text):
            return "PREMISE", 0.74

        # --- 5. CLAIM (0.70) --------------------------------------------
        word_count = len(text.split())
        if (
            self._RE_CLAIM_MODAL.search(text)
            or self._RE_CLAIM_OPINION.search(text)
            or word_count < 25
        ):
            # Require at least 5 words to avoid falling through to OTHER
            if word_count >= 5:
                return "CLAIM", 0.70

        # --- 6. OTHER (0.60) — default fallback -------------------------
        return "OTHER", 0.60
