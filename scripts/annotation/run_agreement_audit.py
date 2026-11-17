"""ARGUMAP Annotation Quality Audit — run_agreement_audit.py

Runs component and relation inter-annotator agreement audits across all
pilot debates.  Validates annotation data integrity, reports agreement
metrics, and produces a combined JSON report plus readable console summary.

Usage:
    python scripts/annotation/run_agreement_audit.py [--output-dir DIR]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotation.calculate_component_agreement import (
    compute_cohens_kappa,
    compute_krippendorffs_alpha_nominal,
)
from scripts.annotation.calculate_relation_agreement import (
    FROZEN_RELATION_LABELS,
    compute_relation_agreement_shared_only,
)

# ---------------------------------------------------------------------------
# Frozen taxonomies (authoritative source: PROJECT_SPEC.md §6)
# ---------------------------------------------------------------------------
FROZEN_COMPONENT_LABELS: List[str] = [
    "CLAIM",
    "PREMISE",
    "EVIDENCE",
    "COUNTERARGUMENT",
    "REBUTTAL",
    "OTHER",
]

FROZEN_RELATION_LABELS_LIST: List[str] = [
    "SUPPORTS",
    "ATTACKS",
    "RESPONDS_TO",
    "NO_RELATION",
]

PILOT_DEBATES: List[str] = ["001", "002", "003"]
PILOT_DIR = PROJECT_ROOT / "data" / "annotations" / "pilot"

# Thresholds from ANNOTATION_GUIDELINES.md §4
COMPONENT_KAPPA_THRESHOLD = 0.70
RELATION_KAPPA_THRESHOLD = 0.65


# ============================================================================
# Validation helpers
# ============================================================================

def validate_annotation_file(filepath: Path) -> Dict[str, Any]:
    """Validate a single annotation JSON file.

    Returns a dict with:
        valid (bool), errors (list[str]), warnings (list[str]),
        unit_count (int), relation_count (int), unit_ids (list[str])
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not filepath.exists():
        return {
            "valid": False,
            "errors": [f"File not found: {filepath}"],
            "warnings": [],
            "unit_count": 0,
            "relation_count": 0,
            "unit_ids": [],
        }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "valid": False,
            "errors": [f"JSON parse error in {filepath.name}: {exc}"],
            "warnings": [],
            "unit_count": 0,
            "relation_count": 0,
            "unit_ids": [],
        }

    # Top-level required keys
    for key in ("debate_id", "title", "units", "relations"):
        if key not in data:
            errors.append(f"Missing top-level key: '{key}'")

    units = data.get("units", [])
    relations = data.get("relations", [])

    # --- Unit validation ---
    unit_ids: List[str] = []
    seen_unit_ids: Set[str] = set()

    for i, unit in enumerate(units):
        uid = unit.get("unit_id")
        if not uid:
            errors.append(f"Unit at index {i} missing 'unit_id'")
            continue

        # Duplicate unit ID check
        if uid in seen_unit_ids:
            errors.append(f"Duplicate unit_id: '{uid}'")
        seen_unit_ids.add(uid)
        unit_ids.append(uid)

        # Component label validation
        label = unit.get("component_label")
        if not label:
            errors.append(f"Unit '{uid}' missing 'component_label'")
        elif label not in FROZEN_COMPONENT_LABELS:
            errors.append(
                f"Unit '{uid}' has invalid component_label '{label}'. "
                f"Must be one of {FROZEN_COMPONENT_LABELS}"
            )

        # Required unit fields
        for field in ("unit_text", "speaker_id", "turn_id"):
            if not unit.get(field):
                errors.append(f"Unit '{uid}' missing required field '{field}'")

        # Confidence bounds
        conf = unit.get("confidence")
        if conf is not None and not (0.0 <= conf <= 1.0):
            errors.append(f"Unit '{uid}' confidence {conf} out of range [0.0, 1.0]")

    # --- Relation validation ---
    seen_rel_pairs: Set[Tuple[str, str]] = set()

    for i, rel in enumerate(relations):
        src = rel.get("source_unit_id")
        tgt = rel.get("target_unit_id")

        if not src or not tgt:
            errors.append(f"Relation at index {i} missing source or target unit ID")
            continue

        # Relation endpoint references valid units
        if src not in seen_unit_ids:
            errors.append(
                f"Relation ({src} -> {tgt}) references unknown source unit '{src}'"
            )
        if tgt not in seen_unit_ids:
            errors.append(
                f"Relation ({src} -> {tgt}) references unknown target unit '{tgt}'"
            )

        # Self-loop check
        if src == tgt:
            errors.append(f"Relation self-loop detected: ({src} -> {tgt})")

        # Duplicate relation pair check
        pair = (src, tgt)
        if pair in seen_rel_pairs:
            errors.append(f"Duplicate relation pair: ({src} -> {tgt})")
        seen_rel_pairs.add(pair)

        # Relation label validation
        rlabel = rel.get("relation_label")
        if not rlabel:
            errors.append(f"Relation ({src} -> {tgt}) missing 'relation_label'")
        elif rlabel not in FROZEN_RELATION_LABELS_LIST:
            errors.append(
                f"Relation ({src} -> {tgt}) has invalid relation_label '{rlabel}'. "
                f"Must be one of {FROZEN_RELATION_LABELS_LIST}"
            )

        # Confidence bounds
        conf = rel.get("confidence")
        if conf is not None and not (0.0 <= conf <= 1.0):
            errors.append(
                f"Relation ({src} -> {tgt}) confidence {conf} out of range [0.0, 1.0]"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "unit_count": len(units),
        "relation_count": len(relations),
        "unit_ids": unit_ids,
    }


def check_cross_annotator_alignment(
    data_a: Dict[str, Any],
    data_b: Dict[str, Any],
    debate_id: str,
) -> Dict[str, Any]:
    """Check alignment between annotator A and B for the same debate.

    Reports:
    - Matched vs. unmatched unit IDs
    - Relation pair overlap statistics
    """
    units_a = data_a.get("units", [])
    units_b = data_b.get("units", [])

    ids_a = set(u["unit_id"] for u in units_a if u.get("unit_id"))
    ids_b = set(u["unit_id"] for u in units_b if u.get("unit_id"))

    shared_ids = ids_a & ids_b
    only_a = ids_a - ids_b
    only_b = ids_b - ids_a

    rels_a = data_a.get("relations", [])
    rels_b = data_b.get("relations", [])

    pairs_a = set(
        (r["source_unit_id"], r["target_unit_id"])
        for r in rels_a
        if r.get("source_unit_id") and r.get("target_unit_id")
    )
    pairs_b = set(
        (r["source_unit_id"], r["target_unit_id"])
        for r in rels_b
        if r.get("source_unit_id") and r.get("target_unit_id")
    )

    shared_pairs = pairs_a & pairs_b
    only_a_pairs = pairs_a - pairs_b
    only_b_pairs = pairs_b - pairs_a

    # Count NO_RELATION labels
    no_rel_a = sum(1 for r in rels_a if r.get("relation_label") == "NO_RELATION")
    no_rel_b = sum(1 for r in rels_b if r.get("relation_label") == "NO_RELATION")

    n_shared = len(shared_ids)
    n_possible_directed = n_shared * (n_shared - 1) if n_shared > 1 else 0

    return {
        "debate_id": debate_id,
        "shared_unit_ids": len(shared_ids),
        "only_annotator_A_units": sorted(only_a),
        "only_annotator_B_units": sorted(only_b),
        "annotator_A_relation_count": len(rels_a),
        "annotator_B_relation_count": len(rels_b),
        "shared_relation_pairs": len(shared_pairs),
        "only_annotator_A_pairs": sorted(
            [f"{s}->{t}" for s, t in only_a_pairs]
        ),
        "only_annotator_B_pairs": sorted(
            [f"{s}->{t}" for s, t in only_b_pairs]
        ),
        "annotator_A_NO_RELATION_count": no_rel_a,
        "annotator_B_NO_RELATION_count": no_rel_b,
        "possible_directed_pairs_from_shared_units": n_possible_directed,
        "annotated_pair_coverage_pct": round(
            100.0 * len(pairs_a | pairs_b) / n_possible_directed, 2
        )
        if n_possible_directed > 0
        else 0.0,
    }


# ============================================================================
# Main audit
# ============================================================================

def run_full_audit(output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Run the complete annotation quality audit across all pilot debates."""
    if output_dir is None:
        output_dir = PILOT_DIR

    report: Dict[str, Any] = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "frozen_component_labels": FROZEN_COMPONENT_LABELS,
        "frozen_relation_labels": FROZEN_RELATION_LABELS_LIST,
        "component_kappa_threshold": COMPONENT_KAPPA_THRESHOLD,
        "relation_kappa_threshold": RELATION_KAPPA_THRESHOLD,
        "debates": {},
        "overall_status": "PENDING",
        "blockers": [],
    }

    console_lines: List[str] = [
        "=" * 76,
        "ARGUMAP — Annotation Quality Audit Report",
        f"Timestamp: {report['audit_timestamp']}",
        "=" * 76,
    ]

    all_component_pass = True
    any_relation_valid = False
    all_files_valid = True

    for debate_num in PILOT_DEBATES:
        debate_key = f"debate_{debate_num}"
        file_a = PILOT_DIR / f"debate_{debate_num}_annotator_A.json"
        file_b = PILOT_DIR / f"debate_{debate_num}_annotator_B.json"

        console_lines.append(f"\n--- {debate_key} ---")

        debate_report: Dict[str, Any] = {
            "files": {
                "annotator_A": str(file_a),
                "annotator_B": str(file_b),
            },
            "file_validation": {},
            "cross_annotator_alignment": {},
            "component_agreement": {},
            "relation_agreement": {},
        }

        # ------------------------------------------------------------------
        # Step 1: File validation
        # ------------------------------------------------------------------
        val_a = validate_annotation_file(file_a)
        val_b = validate_annotation_file(file_b)
        debate_report["file_validation"]["annotator_A"] = val_a
        debate_report["file_validation"]["annotator_B"] = val_b

        if not val_a["valid"]:
            console_lines.append(f"  [FAIL] annotator_A validation: {val_a['errors']}")
            all_files_valid = False
        else:
            console_lines.append(
                f"  [PASS] annotator_A: {val_a['unit_count']} units, "
                f"{val_a['relation_count']} relations"
            )

        if not val_b["valid"]:
            console_lines.append(f"  [FAIL] annotator_B validation: {val_b['errors']}")
            all_files_valid = False
        else:
            console_lines.append(
                f"  [PASS] annotator_B: {val_b['unit_count']} units, "
                f"{val_b['relation_count']} relations"
            )

        if not (val_a["valid"] and val_b["valid"]):
            debate_report["component_agreement"] = {
                "status": "SKIPPED",
                "reason": "File validation failed",
            }
            debate_report["relation_agreement"] = {
                "status": "SKIPPED",
                "reason": "File validation failed",
            }
            report["debates"][debate_key] = debate_report
            continue

        # Load data for agreement calculations
        with open(file_a, "r", encoding="utf-8") as f:
            data_a = json.load(f)
        with open(file_b, "r", encoding="utf-8") as f:
            data_b = json.load(f)

        # ------------------------------------------------------------------
        # Step 2: Cross-annotator alignment check
        # ------------------------------------------------------------------
        alignment = check_cross_annotator_alignment(data_a, data_b, debate_key)
        debate_report["cross_annotator_alignment"] = alignment

        console_lines.append(
            f"  Shared units: {alignment['shared_unit_ids']}, "
            f"Shared relation pairs: {alignment['shared_relation_pairs']}"
        )
        if alignment["only_annotator_A_units"]:
            console_lines.append(
                f"  WARNING: Units only in A: {alignment['only_annotator_A_units']}"
            )
        if alignment["only_annotator_B_units"]:
            console_lines.append(
                f"  WARNING: Units only in B: {alignment['only_annotator_B_units']}"
            )

        # ------------------------------------------------------------------
        # Step 3: Component agreement
        # ------------------------------------------------------------------
        units_a = data_a.get("units", [])
        units_b = data_b.get("units", [])

        map_a = {
            u["unit_id"]: u.get("component_label")
            for u in units_a
            if u.get("component_label")
        }
        map_b = {
            u["unit_id"]: u.get("component_label")
            for u in units_b
            if u.get("component_label")
        }

        common_ids = sorted(uid for uid in map_a if uid in map_b)

        if len(common_ids) < 2:
            comp_result = {
                "status": "AGREEMENT NOT AVAILABLE",
                "reason": f"Insufficient shared units ({len(common_ids)})",
            }
            all_component_pass = False
        else:
            labels_a = [map_a[uid] for uid in common_ids]
            labels_b = [map_b[uid] for uid in common_ids]
            comp_result = compute_cohens_kappa(labels_a, labels_b)
            alpha = compute_krippendorffs_alpha_nominal(labels_a, labels_b)
            comp_result["krippendorffs_alpha"] = alpha

            kappa = comp_result.get("cohens_kappa", 0.0)
            passes = kappa >= COMPONENT_KAPPA_THRESHOLD
            comp_result["passes_threshold"] = passes
            if not passes:
                all_component_pass = False

            console_lines.append(
                f"  Component kappa: {kappa:.4f} "
                f"({'PASS' if passes else 'BELOW THRESHOLD'})"
            )

        debate_report["component_agreement"] = comp_result

        # ------------------------------------------------------------------
        # Step 4: Relation agreement (shared-pairs-only method)
        # ------------------------------------------------------------------
        rels_a = data_a.get("relations", [])
        rels_b = data_b.get("relations", [])

        rel_result = compute_relation_agreement_shared_only(rels_a, rels_b)
        debate_report["relation_agreement"] = rel_result

        rel_status = rel_result.get("status", "UNAVAILABLE")
        if rel_status == "COMPLETED":
            any_relation_valid = True
            rel_kappa = rel_result.get("cohens_kappa")
            if rel_kappa is not None:
                passes_rel = rel_kappa >= RELATION_KAPPA_THRESHOLD
                rel_result["passes_threshold"] = passes_rel
                console_lines.append(
                    f"  Relation kappa [SHARED EXPLICIT POSITIVE PAIRS ONLY]: {rel_kappa:.4f} "
                    f"({'PASS' if passes_rel else 'BELOW THRESHOLD'})"
                )
            else:
                rel_result["passes_threshold"] = None
                rel_result["passes_threshold_reason"] = "Metric undefined due to zero variance or degeneracy."
                console_lines.append(
                    f"  Relation kappa [SHARED EXPLICIT POSITIVE PAIRS ONLY]: UNAVAILABLE "
                    f"({rel_result.get('cohens_kappa_note', 'Undefined')})"
                )
        else:
            rel_result["passes_threshold"] = None
            console_lines.append(
                f"  Relation agreement [SHARED EXPLICIT POSITIVE PAIRS ONLY]: {rel_status} - "
                f"{rel_result.get('reason', 'N/A')}"
            )

        # Coverage warning & limitation
        coverage = alignment.get("annotated_pair_coverage_pct", 0.0)
        console_lines.append(
            f"  NOTE: Evaluated {rel_result.get('shared_pairs', 0)} shared positive pairs only. "
            f"Coverage is {coverage:.1f}% of possible pairs; candidate-pair universe window k is undefined."
        )
        if coverage < 10.0:
            rel_result["coverage_warning"] = (
                f"Only {coverage:.1f}% of possible directed pairs are annotated. "
                f"Without a defined candidate-pair universe (turn distance window k), "
                f"kappa for relations is computed only on shared annotated pairs "
                f"and may not be representative."
            )

        report["debates"][debate_key] = debate_report

    # -----------------------------------------------------------------------
    # Overall assessment
    # -----------------------------------------------------------------------
    console_lines.append("\n" + "=" * 76)
    console_lines.append("OVERALL ASSESSMENT")
    console_lines.append("=" * 76)

    blockers: List[str] = []

    if not all_files_valid:
        blockers.append("One or more annotation files failed validation.")
        console_lines.append("[BLOCKER] File validation failures detected.")

    if all_component_pass:
        console_lines.append(
            f"[PASS] All component kappas meet threshold (>= {COMPONENT_KAPPA_THRESHOLD})"
        )
    else:
        blockers.append(
            f"Component kappa below {COMPONENT_KAPPA_THRESHOLD} in one or more debates."
        )
        console_lines.append(
            f"[FAIL] Component agreement below threshold in one or more debates."
        )

    # Relation agreement assessment
    console_lines.append("")
    console_lines.append("RELATION AGREEMENT STATUS [SHARED EXPLICIT POSITIVE PAIRS ONLY]:")
    console_lines.append(
        "  The annotation schema stores only positive/active relation edges."
    )
    console_lines.append(
        "  NO_RELATION is NOT explicitly annotated for any pair."
    )
    console_lines.append(
        "  The candidate-pair universe (turn distance window k) has NOT been "
        "determined yet (see ANNOTATION_WORKFLOW.md section 4.3)."
    )
    console_lines.append(
        "  Therefore, treating omitted pairs as NO_RELATION would produce "
        "invalid agreement statistics."
    )
    console_lines.append("")
    console_lines.append(
        "  Relation kappa is computed ONLY on pairs annotated by BOTH "
        "annotators (shared-pairs-only method)."
    )
    console_lines.append(
        "  This gives a lower-bound on label agreement for actively linked "
        "pairs but does NOT validate whether annotators agree on WHICH pairs "
        "should have links."
    )

    blockers.append(
        "Candidate-pair universe (turn distance window k) is undefined. "
        "Relation agreement cannot be fully validated until k is determined "
        "during the pilot calibration (ANNOTATION_WORKFLOW.md section 4.3)."
    )
    console_lines.append(
        "\n[BLOCKER] Candidate-pair universe undefined. Full relation IAA "
        "cannot be computed."
    )

    report["blockers"] = blockers
    report["overall_status"] = "BLOCKED" if blockers else "PASS"

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------
    console_text = "\n".join(console_lines)
    print(console_text)

    # Save JSON reports (save both agreement_audit_report.json and annotation_quality_audit.json for compatibility)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "agreement_audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved to: {report_path}")

    # Also keep annotation_quality_audit.json in sync
    legacy_path = output_dir / "annotation_quality_audit.json"
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Save console summary
    summary_path = output_dir / "annotation_quality_audit_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(console_text)
    print(f"Console summary saved to: {summary_path}")

    return report


# ============================================================================
# CLI entry point
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run ARGUMAP annotation quality audit across all pilot debates."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for audit output files (default: data/annotations/pilot/)",
    )
    args = parser.parse_args()

    report = run_full_audit(output_dir=args.output_dir)
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
