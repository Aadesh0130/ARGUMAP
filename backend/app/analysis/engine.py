"""
engine.py — Structural Analysis Engine for ARGUMAP.

Applies heuristic graph reasoning rules to detect structural patterns
in argument graphs built from debate / discussion transcripts.
"""

from __future__ import annotations

import networkx as nx


class StructuralAnalysisEngine:
    """Heuristic graph reasoning engine.

    Analyses a :class:`networkx.MultiDiGraph` whose nodes carry
    ``component_type`` and ``speaker_id`` attributes and whose edges
    carry a ``relation_type`` attribute, then returns a list of
    *insight* dicts describing structural observations or problems.
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        graph: nx.MultiDiGraph,
        speakers: dict[str, str],
    ) -> list[dict]:
        """Run all four heuristic rules and return the combined insight list.

        Parameters
        ----------
        graph:
            A NetworkX ``MultiDiGraph`` produced by ``ArgumentGraphBuilder``.
            Each node is keyed by its ``unit_id`` string and carries at
            least ``component_type``, ``speaker_id``, and ``text``
            attributes.  Each edge carries ``relation_type``.
        speakers:
            Mapping of ``speaker_id -> speaker_name`` used to produce
            human-readable messages.

        Returns
        -------
        list[dict]
            Ordered list of insight dicts.  Each dict has the shape::

                {
                    "id": "ins_1",
                    "type": "<INSIGHT_TYPE>",
                    "severity": "WARNING" | "INFO",
                    "message": "<human readable string>",
                    "related_argument_ids": ["<node_id>", ...],
                }
        """
        insights: list[dict] = []
        counter = 1

        def _next_id() -> str:
            nonlocal counter
            insight_id = f"ins_{counter}"
            counter += 1
            return insight_id

        # Pre-compute helper data structures once so the rules are O(E)
        # rather than O(N·E).
        incoming: dict[str, list[dict]] = {n: [] for n in graph.nodes}
        outgoing: dict[str, list[dict]] = {n: [] for n in graph.nodes}

        for src, tgt, data in graph.edges(data=True):
            outgoing[src].append({"target": tgt, "relation_type": data.get("relation_type", "")})
            incoming[tgt].append({"source": src, "relation_type": data.get("relation_type", "")})

        # ---- Rule 1: Unsupported Claims -------------------------------- #
        insights.extend(
            self._rule_unsupported_claims(graph, speakers, incoming, _next_id)
        )

        # ---- Rule 2: Unanswered Counterarguments ----------------------- #
        insights.extend(
            self._rule_unanswered_counterarguments(graph, speakers, incoming, _next_id)
        )

        # ---- Rule 3: Direct Clash -------------------------------------- #
        insights.extend(
            self._rule_direct_clash(graph, speakers, _next_id)
        )

        # ---- Rule 4: Orphan Evidence ----------------------------------- #
        insights.extend(
            self._rule_orphan_evidence(graph, outgoing, _next_id)
        )

        return insights

    def summarize(self, insights: list[dict]) -> dict:
        """Aggregate insight counts.

        Parameters
        ----------
        insights:
            The list returned by :meth:`analyze`.

        Returns
        -------
        dict
            ``{"total": int, "warnings": int, "infos": int}``
        """
        warnings = sum(1 for i in insights if i.get("severity") == "WARNING")
        infos = sum(1 for i in insights if i.get("severity") == "INFO")
        return {"total": len(insights), "warnings": warnings, "infos": infos}

    # ------------------------------------------------------------------ #
    # Private rule implementations
    # ------------------------------------------------------------------ #

    @staticmethod
    def _node_text(graph: nx.MultiDiGraph, node_id: str, max_len: int = 60) -> str:
        """Return node text truncated to *max_len* characters."""
        text: str = graph.nodes[node_id].get("text", node_id) or node_id
        return text[:max_len] if len(text) <= max_len else text[:max_len]

    @staticmethod
    def _speaker_name(graph: nx.MultiDiGraph, node_id: str, speakers: dict[str, str]) -> str:
        """Resolve the display name for the speaker of *node_id*."""
        spk_id: str = graph.nodes[node_id].get("speaker_id", "")
        return speakers.get(spk_id, spk_id or "Unknown Speaker")

    # ---- Rule 1 -------------------------------------------------------- #

    def _rule_unsupported_claims(
        self,
        graph: nx.MultiDiGraph,
        speakers: dict[str, str],
        incoming: dict[str, list[dict]],
        next_id,
    ) -> list[dict]:
        """Rule 1 — Unsupported Claims.

        A CLAIM node is *supported* when it has ≥ 1 incoming edge whose
        ``relation_type`` is ``"SUPPORTS"``.  Emit a WARNING per unsupported
        claim, or a single INFO when all claims are supported.
        """
        claim_nodes = [
            n for n in graph.nodes
            if graph.nodes[n].get("component_type") == "CLAIM"
        ]

        if not claim_nodes:
            return []

        unsupported: list[str] = []
        for node_id in claim_nodes:
            supported = any(
                e["relation_type"] == "SUPPORTS" for e in incoming[node_id]
            )
            if not supported:
                unsupported.append(node_id)

        results: list[dict] = []

        if unsupported:
            for node_id in unsupported:
                text = self._node_text(graph, node_id)
                speaker = self._speaker_name(graph, node_id, speakers)
                results.append(
                    {
                        "id": next_id(),
                        "type": "UNSUPPORTED_CLAIM",
                        "severity": "WARNING",
                        "message": (
                            f"Claim by {speaker} has no supporting premise or "
                            f"evidence: '{text}'"
                        ),
                        "related_argument_ids": [node_id],
                    }
                )
        else:
            results.append(
                {
                    "id": next_id(),
                    "type": "UNSUPPORTED_CLAIM",
                    "severity": "INFO",
                    "message": "All detected claims have supporting premises or evidence.",
                    "related_argument_ids": [],
                }
            )

        return results

    # ---- Rule 2 -------------------------------------------------------- #

    def _rule_unanswered_counterarguments(
        self,
        graph: nx.MultiDiGraph,
        speakers: dict[str, str],
        incoming: dict[str, list[dict]],
        next_id,
    ) -> list[dict]:
        """Rule 2 — Unanswered Counterarguments.

        A COUNTERARGUMENT node is *answered* when it has ≥ 1 incoming edge
        with ``relation_type`` in ``{"REBUTTAL", "RESPONDS_TO"}``.
        """
        counter_nodes = [
            n for n in graph.nodes
            if graph.nodes[n].get("component_type") == "COUNTERARGUMENT"
        ]

        if not counter_nodes:
            return []

        answer_types = {"REBUTTAL", "RESPONDS_TO"}
        unanswered: list[str] = []

        for node_id in counter_nodes:
            answered = any(
                e["relation_type"] in answer_types for e in incoming[node_id]
            )
            if not answered:
                unanswered.append(node_id)

        results: list[dict] = []

        if unanswered:
            for node_id in unanswered:
                text = self._node_text(graph, node_id)
                speaker = self._speaker_name(graph, node_id, speakers)
                results.append(
                    {
                        "id": next_id(),
                        "type": "UNANSWERED_COUNTERARGUMENT",
                        "severity": "WARNING",
                        "message": (
                            f"Counterargument by {speaker} has not been "
                            f"rebutted or responded to: '{text}'"
                        ),
                        "related_argument_ids": [node_id],
                    }
                )
        else:
            results.append(
                {
                    "id": next_id(),
                    "type": "UNANSWERED_COUNTERARGUMENT",
                    "severity": "INFO",
                    "message": "All counterarguments have detected responses.",
                    "related_argument_ids": [],
                }
            )

        return results

    # ---- Rule 3 -------------------------------------------------------- #

    def _rule_direct_clash(
        self,
        graph: nx.MultiDiGraph,
        speakers: dict[str, str],  # noqa: ARG002  (kept for signature uniformity)
        next_id,
    ) -> list[dict]:
        """Rule 3 — Direct Clash.

        Count edges whose ``relation_type`` is ``"ATTACKS"`` or
        ``"RESPONDS_TO"`` and whose source and target node belong to
        *different* speakers.
        """
        clash_types = {"ATTACKS", "RESPONDS_TO"}
        cross_speaker_count = 0

        for src, tgt, data in graph.edges(data=True):
            relation = data.get("relation_type", "")
            if relation not in clash_types:
                continue
            src_speaker = graph.nodes[src].get("speaker_id", "")
            tgt_speaker = graph.nodes[tgt].get("speaker_id", "")
            if src_speaker != tgt_speaker:
                cross_speaker_count += 1

        if cross_speaker_count > 0:
            message = (
                f"Direct dialectical engagement detected: "
                f"{cross_speaker_count} cross-speaker attack/response edge(s)."
            )
        else:
            message = "No direct cross-speaker attacks detected."

        return [
            {
                "id": next_id(),
                "type": "DIRECT_CLASH",
                "severity": "INFO",
                "message": message,
                "related_argument_ids": [],
            }
        ]

    # ---- Rule 4 -------------------------------------------------------- #

    def _rule_orphan_evidence(
        self,
        graph: nx.MultiDiGraph,
        outgoing: dict[str, list[dict]],
        next_id,
    ) -> list[dict]:
        """Rule 4 — Orphan Evidence.

        An EVIDENCE node is an *orphan* when it has no outgoing edge that
        points to a CLAIM or PREMISE node.
        """
        linked_targets = {"CLAIM", "PREMISE"}
        evidence_nodes = [
            n for n in graph.nodes
            if graph.nodes[n].get("component_type") == "EVIDENCE"
        ]

        results: list[dict] = []

        for node_id in evidence_nodes:
            is_linked = any(
                graph.nodes[e["target"]].get("component_type") in linked_targets
                for e in outgoing[node_id]
                if e["target"] in graph.nodes
            )
            if not is_linked:
                text = self._node_text(graph, node_id)
                results.append(
                    {
                        "id": next_id(),
                        "type": "ORPHAN_EVIDENCE",
                        "severity": "WARNING",
                        "message": (
                            f"Evidence unit has no detected link to any claim "
                            f"or premise: '{text}...'"
                        ),
                        "related_argument_ids": [node_id],
                    }
                )

        return results
