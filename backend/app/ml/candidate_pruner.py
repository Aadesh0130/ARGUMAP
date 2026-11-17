"""
Candidate pair pruner for argument relation discovery.

Generates ordered (source → target) candidate pairs from a list of argument
units and assigns a preliminary relation label using simple heuristic rules.
The output feeds the graph builder without requiring a trained relation model.
"""

from __future__ import annotations

__all__ = ["CandidatePairPruner"]


class CandidatePairPruner:
    """Generate and label candidate argument-unit pairs for relation prediction.

    Usage::

        pruner = CandidatePairPruner()
        pairs = pruner.generate_pairs(units, window=10)
        relations = pruner.assign_relations(pairs)
    """

    # Relation rule table: (source_type, target_types) → (relation, confidence)
    _RELATION_RULES: list[tuple[str | tuple[str, ...], tuple[str, ...], str, float]] = [
        ("REBUTTAL",                    ("COUNTERARGUMENT",),           "RESPONDS_TO",  0.75),
        (("PREMISE", "EVIDENCE"),       ("CLAIM", "PREMISE"),           "SUPPORTS",     0.72),
        ("COUNTERARGUMENT",             ("CLAIM", "PREMISE"),           "ATTACKS",      0.70),
    ]

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def generate_pairs(
        self,
        units: list[dict],
        window: int = 10,
    ) -> list[tuple[dict, dict]]:
        """Generate ordered candidate pairs from a sequence of argument units.

        Args:
            units: Sequence of unit dicts with keys ``unit_id``,
                ``turn_order``, ``speaker_id``, and ``component_type``.
                The position of each unit in the list is treated as its
                *unit_index*.
            window: Maximum allowed difference in ``turn_order`` between
                the two units of a pair.  Defaults to 10.

        Returns:
            List of ``(unit_A, unit_B)`` tuples where A precedes B in the
            original sequence.
        """
        pairs: list[tuple[dict, dict]] = []

        for idx_a, unit_a in enumerate(units):
            for idx_b in range(idx_a + 1, len(units)):
                unit_b = units[idx_b]

                # Rule 1: A must precede B by index (guaranteed by loop structure)
                # Rule 2: turn_order window
                if abs(unit_a["turn_order"] - unit_b["turn_order"]) > window:
                    continue

                # Rule 3: skip same-speaker same-turn pairs
                if (
                    unit_a["speaker_id"] == unit_b["speaker_id"]
                    and unit_a["turn_order"] == unit_b["turn_order"]
                ):
                    continue

                # Rule 4: skip pairs where BOTH are OTHER
                if (
                    unit_a["component_type"] == "OTHER"
                    and unit_b["component_type"] == "OTHER"
                ):
                    continue

                pairs.append((unit_a, unit_b))

        return pairs

    def assign_relations(
        self,
        pairs: list[tuple[dict, dict]],
    ) -> list[dict]:
        """Assign a relation label to each candidate pair.

        Args:
            pairs: List of ``(unit_A, unit_B)`` tuples as returned by
                :meth:`generate_pairs`.

        Returns:
            List of relation dicts (``NO_RELATION`` pairs are filtered out)::

                {
                    "source_id":    str,
                    "target_id":    str,
                    "relation_type": str,
                    "confidence":   float,
                }
        """
        results: list[dict] = []

        for unit_a, unit_b in pairs:
            type_a = unit_a["component_type"]
            type_b = unit_b["component_type"]

            relation, confidence = self._lookup_relation(type_a, type_b)

            if relation == "NO_RELATION":
                continue

            results.append(
                {
                    "source_id": unit_a["unit_id"],
                    "target_id": unit_b["unit_id"],
                    "relation_type": relation,
                    "confidence": confidence,
                }
            )

        return results

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _lookup_relation(
        self,
        type_a: str,
        type_b: str,
    ) -> tuple[str, float]:
        """Return ``(relation_type, confidence)`` for the given component types."""
        for src_types, tgt_types, relation, conf in self._RELATION_RULES:
            # src_types may be a single string or a tuple of strings
            if isinstance(src_types, str):
                src_match = type_a == src_types
            else:
                src_match = type_a in src_types

            if src_match and type_b in tgt_types:
                return relation, conf

        return "NO_RELATION", 0.60
