#!/usr/bin/env python3
"""Dataset Statistics Reporter for ARGUMAP.

Computes comprehensive corpus descriptive metrics across validated annotation documents:
- Debate counts, speaker rosters, speech turns
- Argument unit counts and component class distributions
- Relation edge counts and relation type distributions
- Graph metrics: units per speaker and relations per debate

Strictly avoids fabricating synthetic numbers when data is absent.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter, defaultdict


class DatasetStatisticsCalculator:
    """Calculates factual descriptive statistics over parsed annotation files."""

    def __init__(self):
        self.debate_ids = set()
        self.speaker_ids = set()
        self.turn_ids = set()
        self.total_units = 0
        self.total_relations = 0
        self.component_counts = Counter()
        self.relation_counts = Counter()
        self.speaker_unit_counts = Counter()
        self.debate_unit_counts = Counter()
        self.debate_relation_counts = Counter()
        self.component_confidences = defaultdict(list)
        self.relation_confidences = defaultdict(list)

    def process_file(self, file_path: Path) -> bool:
        """Processes a single annotation JSON file."""
        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        debate_id = data.get("debate_id", file_path.stem)
        self.debate_ids.add(debate_id)

        units = data.get("units", [])
        for u in units:
            self.total_units += 1
            spk = u.get("speaker_id", "Unknown")
            self.speaker_ids.add(spk)
            self.speaker_unit_counts[spk] += 1
            self.debate_unit_counts[debate_id] += 1

            t_id = u.get("turn_id")
            if t_id:
                self.turn_ids.add(f"{debate_id}_{t_id}")

            label = u.get("component_label", "UNKNOWN")
            self.component_counts[label] += 1

            conf = u.get("confidence")
            if isinstance(conf, (int, float)):
                self.component_confidences[label].append(conf)

        relations = data.get("relations", [])
        for r in relations:
            self.total_relations += 1
            self.debate_relation_counts[debate_id] += 1
            rel_label = r.get("relation_label", "UNKNOWN")
            self.relation_counts[rel_label] += 1

            conf = r.get("confidence")
            if isinstance(conf, (int, float)):
                self.relation_confidences[rel_label].append(conf)

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured dictionary of calculated statistics."""
        comp_summary = {}
        for label, count in self.component_counts.items():
            pct = (count / self.total_units * 100.0) if self.total_units > 0 else 0.0
            confs = self.component_confidences.get(label, [])
            mean_conf = (sum(confs) / len(confs)) if confs else 0.0
            comp_summary[label] = {
                "count": count,
                "percentage": round(pct, 2),
                "mean_confidence": round(mean_conf, 4),
            }

        rel_summary = {}
        for label, count in self.relation_counts.items():
            pct = (count / self.total_relations * 100.0) if self.total_relations > 0 else 0.0
            confs = self.relation_confidences.get(label, [])
            mean_conf = (sum(confs) / len(confs)) if confs else 0.0
            rel_summary[label] = {
                "count": count,
                "percentage": round(pct, 2),
                "mean_confidence": round(mean_conf, 4),
            }

        return {
            "total_debates": len(self.debate_ids),
            "total_speakers": len(self.speaker_ids),
            "total_turns": len(self.turn_ids),
            "total_units": self.total_units,
            "total_relations": self.total_relations,
            "component_distribution": comp_summary,
            "relation_distribution": rel_summary,
            "units_per_speaker": dict(self.speaker_unit_counts),
            "relations_per_debate": dict(self.debate_relation_counts),
        }

    def print_report(self) -> None:
        """Prints a human-readable summary table."""
        summary = self.get_summary()

        print("=" * 60)
        print("          ARGUMAP DATASET DESCRIPTIVE STATISTICS          ")
        print("=" * 60)

        if summary["total_debates"] == 0:
            print("\n[NOTE] No debate annotation records found. Statistics cannot be calculated.")
            print("To analyze data, supply path(s) to validated annotation files.")
            print("=" * 60)
            return

        print(f"Total Debates:   {summary['total_debates']}")
        print(f"Total Speakers:  {summary['total_speakers']}")
        print(f"Total Turns:     {summary['total_turns']}")
        print(f"Total Units:     {summary['total_units']}")
        print(f"Total Relations: {summary['total_relations']}")
        print("-" * 60)

        print("\n--- Component Label Distribution ---")
        print(f"{'Label':<18} | {'Count':<8} | {'Percent':<8} | {'Mean Conf':<10}")
        print("-" * 52)
        for label, stats in sorted(summary["component_distribution"].items(), key=lambda x: -x[1]["count"]):
            print(f"{label:<18} | {stats['count']:<8} | {stats['percentage']:>6.2f}% | {stats['mean_confidence']:>9.4f}")

        print("\n--- Relation Label Distribution ---")
        print(f"{'Label':<18} | {'Count':<8} | {'Percent':<8} | {'Mean Conf':<10}")
        print("-" * 52)
        for label, stats in sorted(summary["relation_distribution"].items(), key=lambda x: -x[1]["count"]):
            print(f"{label:<18} | {stats['count']:<8} | {stats['percentage']:>6.2f}% | {stats['mean_confidence']:>9.4f}")

        print("\n--- Units Per Speaker ---")
        for spk, count in sorted(summary["units_per_speaker"].items(), key=lambda x: -x[1]):
            print(f"  • {spk}: {count} unit(s)")

        print("=" * 60)


def main() -> int:
    paths = sys.argv[1:]
    calc = DatasetStatisticsCalculator()

    if not paths:
        # Default check in data/annotations/
        default_dir = Path(__file__).resolve().parents[2] / "data" / "annotations"
        target_files = list(default_dir.rglob("*.json"))
        # Exclude schema files from statistics
        target_files = [f for f in target_files if "schema" not in f.name.lower()]
    else:
        target_files = []
        for p in paths:
            path_obj = Path(p)
            if path_obj.is_dir():
                target_files.extend([f for f in path_obj.rglob("*.json") if "schema" not in f.name.lower()])
            elif path_obj.exists():
                target_files.append(path_obj)

    print(f"Processing {len(target_files)} annotation file(s)...")
    for f in target_files:
        calc.process_file(f)

    calc.print_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
