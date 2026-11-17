"""
analysis_service.py — Full Argument Analysis Pipeline for ARGUMAP.

Orchestrates:
  1. Speaker, turn, sentence & proposition segmentation via PreprocessingPipeline
  2. Component classification via RuleBasedComponentClassifier
  3. Relation inference via window-based heuristics
  4. Graph construction via NetworkX MultiDiGraph
  5. Structural insight detection via StructuralAnalysisEngine

The service is intentionally stateless; every call receives a plain transcript
string and returns a fully populated AnalysisPipelineResult.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

import networkx as nx

from app.analysis.engine import StructuralAnalysisEngine
from app.ml.rule_classifier import RuleBasedComponentClassifier
from app.nlp.models import Speaker, Turn, PreprocessingResult
from app.nlp.pipeline import PreprocessingPipeline, default_pipeline


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class ArgumentUnit:
    unit_id: str
    turn_id: str
    speaker_id: str
    speaker_name: str
    turn_order: int
    text: str
    component_type: str   # CLAIM | PREMISE | EVIDENCE | COUNTERARGUMENT | REBUTTAL | OTHER
    confidence: float
    start_char: int
    end_char: int


@dataclass
class Relation:
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str    # SUPPORTS | ATTACKS | RESPONDS_TO | NO_RELATION
    confidence: float


@dataclass
class AnalysisPipelineResult:
    speakers: List[Speaker]
    turns: List[Turn]
    arguments: List[ArgumentUnit]
    relations: List[Relation]
    insights: List[dict]
    warnings: List[str]
    model_version: str = RuleBasedComponentClassifier.MODEL_VERSION


# ---------------------------------------------------------------------------
# Relation inference helpers
# ---------------------------------------------------------------------------

_ATTACK_TYPES = {"COUNTERARGUMENT", "REBUTTAL"}
_SUPPORT_TYPES = {"PREMISE", "EVIDENCE"}

# Within-window relation inference: look back N units
_RELATION_WINDOW = 4


def _infer_relation(source: ArgumentUnit, target: ArgumentUnit) -> Tuple[str, float]:
    """Heuristically infer the relation from *source* → *target*.

    Rules (priority order):
      1. REBUTTAL → COUNTERARGUMENT          : RESPONDS_TO (0.80)
      2. COUNTERARGUMENT → CLAIM/PREMISE     : ATTACKS     (0.78)
      3. PREMISE/EVIDENCE → CLAIM            : SUPPORTS    (0.75)
      4. Same speaker: consecutive CLAIM→CLAIM: SUPPORTS  (0.60)
      5. Cross-speaker any attack type → any : ATTACKS     (0.55)
      6. default                             : NO_RELATION (0.50)
    """
    stype = source.component_type
    ttype = target.component_type
    same_speaker = source.speaker_id == target.speaker_id

    if stype == "REBUTTAL" and ttype == "COUNTERARGUMENT":
        return "RESPONDS_TO", 0.80
    if stype == "COUNTERARGUMENT" and ttype in ("CLAIM", "PREMISE"):
        return "ATTACKS", 0.78
    if stype in _SUPPORT_TYPES and ttype == "CLAIM":
        return "SUPPORTS", 0.75
    if same_speaker and stype == "CLAIM" and ttype == "CLAIM":
        return "SUPPORTS", 0.60
    if not same_speaker and stype in _ATTACK_TYPES:
        return "ATTACKS", 0.55
    return "NO_RELATION", 0.50


# ---------------------------------------------------------------------------
# Main service class
# ---------------------------------------------------------------------------

class AnalysisService:
    """Runs the full ARGUMAP analysis pipeline on a raw transcript string."""

    def __init__(
        self,
        pipeline: Optional[PreprocessingPipeline] = None,
        classifier: Optional[RuleBasedComponentClassifier] = None,
        engine: Optional[StructuralAnalysisEngine] = None,
    ):
        self._pipeline = pipeline or default_pipeline
        self._classifier = classifier or RuleBasedComponentClassifier()
        self._engine = engine or StructuralAnalysisEngine()

    # ------------------------------------------------------------------ #
    # Public entry-point                                                   #
    # ------------------------------------------------------------------ #

    def run(
        self,
        transcript: str,
        document_id: Optional[str] = None,
    ) -> AnalysisPipelineResult:
        """Execute the full pipeline and return a populated result object.

        Parameters
        ----------
        transcript:
            Raw debate / discussion text with speaker labels.
        document_id:
            Optional identifier for the debate document.

        Returns
        -------
        AnalysisPipelineResult
        """
        # Step 1 – Preprocessing (Normalization, Speaker/Turn parsing, Sentence & Proposition segmentation)
        preprocessed: PreprocessingResult = self._pipeline.process(
            transcript_text=transcript,
            document_id=document_id,
        )

        speakers = preprocessed.speakers
        turns = preprocessed.turns
        warnings: List[str] = list(preprocessed.validation.warnings)
        if preprocessed.validation.errors:
            warnings.extend(preprocessed.validation.errors)

        if not turns or not preprocessed.units:
            if not turns:
                warnings.append("No speech turns could be extracted.")
            return AnalysisPipelineResult(
                speakers=speakers,
                turns=turns,
                arguments=[],
                relations=[],
                insights=[],
                warnings=warnings,
                model_version=RuleBasedComponentClassifier.MODEL_VERSION,
            )

        # Step 2 – Classify extracted argument units
        arguments = self._classify_units(preprocessed.units, turns, speakers)

        # Step 3 – Infer relations
        relations = self._infer_relations(arguments)

        # Step 4 – Build graph & detect structural reasoning insights
        graph = self._build_graph(arguments, relations)
        speaker_map: Dict[str, str] = {
            spk.speaker_id: spk.speaker_name for spk in speakers
        }
        insights = self._engine.analyze(graph, speaker_map)

        return AnalysisPipelineResult(
            speakers=speakers,
            turns=turns,
            arguments=arguments,
            relations=relations,
            insights=insights,
            warnings=warnings,
            model_version=RuleBasedComponentClassifier.MODEL_VERSION,
        )

    # ------------------------------------------------------------------ #
    # Step 2 – classify                                                    #
    # ------------------------------------------------------------------ #

    def _classify_units(
        self,
        raw_units: list,
        turns: List[Turn],
        speakers: List[Speaker],
    ) -> List[ArgumentUnit]:
        """Classify each extracted proposition unit using the rule-based classifier."""
        turn_map: Dict[str, Turn] = {t.turn_id: t for t in turns}
        speaker_map: Dict[str, str] = {s.speaker_id: s.speaker_name for s in speakers}

        classified_units: List[ArgumentUnit] = []
        for unit in raw_units:
            label, confidence = self._classifier.predict(unit.text)

            parent_turn = turn_map.get(unit.turn_id)
            speaker_name = (
                parent_turn.speaker_name
                if parent_turn
                else speaker_map.get(unit.speaker_id, "Speaker")
            )
            turn_order = (
                (parent_turn.turn_index + 1)
                if parent_turn
                else (unit.turn_index + 1)
            )

            classified_units.append(
                ArgumentUnit(
                    unit_id=unit.unit_id,
                    turn_id=unit.turn_id,
                    speaker_id=unit.speaker_id,
                    speaker_name=speaker_name,
                    turn_order=turn_order,
                    text=unit.text,
                    component_type=label,
                    confidence=confidence,
                    start_char=unit.char_start,
                    end_char=unit.char_end,
                )
            )
        return classified_units

    # ------------------------------------------------------------------ #
    # Step 3 – relation inference                                          #
    # ------------------------------------------------------------------ #

    def _infer_relations(self, arguments: List[ArgumentUnit]) -> List[Relation]:
        """Infer pairwise relations using a backward-window heuristic.

        Guarantees:
        - Only valid argument IDs are referenced.
        - Zero self-referencing edges.
        - Zero duplicate directed pairs.
        """
        relations: List[Relation] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for i, source in enumerate(arguments):
            window_start = max(0, i - _RELATION_WINDOW)
            for target in arguments[window_start:i]:
                # Avoid self-referencing relations
                if source.unit_id == target.unit_id:
                    continue

                # Avoid duplicate relations between the same pair
                pair_key = (source.unit_id, target.unit_id)
                if pair_key in seen_pairs:
                    continue

                rel_type, conf = _infer_relation(source, target)
                if rel_type == "NO_RELATION":
                    continue

                seen_pairs.add(pair_key)
                rel_id = f"rel_{hashlib.sha256(f'{source.unit_id}:{target.unit_id}'.encode()).hexdigest()[:8]}"
                relations.append(
                    Relation(
                        relation_id=rel_id,
                        source_id=source.unit_id,
                        target_id=target.unit_id,
                        relation_type=rel_type,
                        confidence=conf,
                    )
                )
        return relations

    # ------------------------------------------------------------------ #
    # Step 4 – graph construction                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_graph(
        arguments: List[ArgumentUnit],
        relations: List[Relation],
    ) -> nx.MultiDiGraph:
        """Build a NetworkX MultiDiGraph from classified argument units."""
        G = nx.MultiDiGraph()
        for arg in arguments:
            G.add_node(
                arg.unit_id,
                text=arg.text,
                component_type=arg.component_type,
                speaker_id=arg.speaker_id,
                speaker_name=arg.speaker_name,
                confidence=arg.confidence,
                turn_order=arg.turn_order,
            )
        for rel in relations:
            G.add_edge(
                rel.source_id,
                rel.target_id,
                relation_type=rel.relation_type,
                confidence=rel.confidence,
            )
        return G


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

analysis_service = AnalysisService()
