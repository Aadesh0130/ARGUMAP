"""Label Mapping Registry and Governance System.

Enforces the project prime directive:
External labels MUST NEVER be silently converted into ARGUMAP labels
without explicit manual review, adjudication, and approval.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple, Any
import json
from pathlib import Path


class UnmappedLabelError(Exception):
    """Raised when an external source label has no registered candidate mapping."""
    pass


class UnapprovedMappingError(Exception):
    """Raised when an external label mapping exists but has NOT been explicitly approved."""
    pass


@dataclass
class LabelMappingRule:
    source_corpus: str
    source_label: str
    candidate_argumap_label: str
    is_approved: bool = False
    reviewer: Optional[str] = None
    approval_date: Optional[str] = None
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MappingRegistry:
    """Central registry and gatekeeper for label transformations."""

    def __init__(self):
        self._rules: Dict[Tuple[str, str], LabelMappingRule] = {}

    def register_candidate_rule(
        self,
        source_corpus: str,
        source_label: str,
        candidate_argumap_label: str,
        is_approved: bool = False,
        reviewer: Optional[str] = None,
        approval_date: Optional[str] = None,
        rationale: str = "",
    ) -> None:
        """Registers a candidate label mapping."""
        key = (source_corpus.lower(), source_label.strip())
        self._rules[key] = LabelMappingRule(
            source_corpus=source_corpus.lower(),
            source_label=source_label.strip(),
            candidate_argumap_label=candidate_argumap_label,
            is_approved=is_approved,
            reviewer=reviewer,
            approval_date=approval_date,
            rationale=rationale,
        )

    def get_argumap_label(self, source_corpus: str, source_label: str) -> str:
        """Resolves an external source label to an ARGUMAP label.
        
        Raises:
            UnmappedLabelError: If the source label is not registered.
            UnapprovedMappingError: If the rule has not been formally approved.
        """
        key = (source_corpus.lower(), source_label.strip())
        if key not in self._rules:
            raise UnmappedLabelError(
                f"No mapping rule registered for corpus '{source_corpus}' and label '{source_label}'."
            )

        rule = self._rules[key]
        if not rule.is_approved:
            raise UnapprovedMappingError(
                f"Label mapping for '{source_corpus}:{source_label}' -> '{rule.candidate_argumap_label}' "
                f"is UNAPPROVED. Silent relabeling is prohibited. Rationale: {rule.rationale}"
            )

        return rule.candidate_argumap_label

    def export_rules(self, output_path: Path) -> None:
        """Exports mapping rules to JSON for team review and audit."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.to_dict() for r in self._rules.values()]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_rules(self, config_path: Path) -> None:
        """Loads rules from an audited JSON configuration file."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            self.register_candidate_rule(**item)
