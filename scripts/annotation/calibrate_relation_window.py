"""ARGUMAP — calibrate_relation_window.py

Empirical calibration analysis of relation candidate-pair windows (k)
based on the Phase 1 pilot annotation data (debates 001, 002, 003).

Computes:
1. Detailed inventory of unique positive relation edges across pilot debates.
2. Directionality and chronologic structure (intra-turn vs cross-turn, forward vs backward).
3. Distance distributions (turn distance and proposition/unit distance).
4. Quantiles (Median, 90th percentile, 95th percentile, Max).
5. Candidate space simulation under multiple candidate-pair generation strategies:
   - Exhaustive (all N*(N-1) pairs)
   - Directional turn window (turn_src >= turn_tgt, delta_turn <= k)
   - Bidirectional turn window (|delta_turn| <= k)
   - Unit-distance window (|delta_unit| <= w)
6. Workload and class balance / density implications.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PILOT_DIR = PROJECT_ROOT / "data" / "annotations" / "pilot"
PILOT_DEBATES = ["001", "002", "003"]


def load_debate_pilot_data(pilot_dir: Path = PILOT_DIR) -> Dict[str, Any]:
    """Load annotator A and B JSON files for all pilot debates."""
    data: Dict[str, Any] = {}
    for d_num in PILOT_DEBATES:
        d_key = f"debate_{d_num}"
        file_a = pilot_dir / f"debate_{d_num}_annotator_A.json"
        file_b = pilot_dir / f"debate_{d_num}_annotator_B.json"

        if not file_a.exists() or not file_b.exists():
            raise FileNotFoundError(f"Pilot files for {d_key} missing in {pilot_dir}")

        with open(file_a, "r", encoding="utf-8") as f:
            da = json.load(f)
        with open(file_b, "r", encoding="utf-8") as f:
            db = json.load(f)

        data[d_key] = {"annotator_A": da, "annotator_B": db}
    return data


def extract_unique_positive_relations(debate_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract deduplicated union of positive relation edges for a debate.

    Preserves source and target directions, tracks annotator agreement,
    and calculates both turn distance and unit sequence distance.
    """
    da = debate_dict["annotator_A"]
    db = debate_dict["annotator_B"]
    units = da["units"]  # Aligned units

    unit_pos = {u["unit_id"]: idx for idx, u in enumerate(units)}
    unit_obj = {u["unit_id"]: u for u in units}

    pair_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for ann_name, doc in [("annotator_A", da), ("annotator_B", db)]:
        for r in doc.get("relations", []):
            src = r["source_unit_id"]
            tgt = r["target_unit_id"]
            pair = (src, tgt)
            lbl = r["relation_label"]

            s_u = unit_obj[src]
            t_u = unit_obj[tgt]

            s_turn = s_u["turn_index"]
            t_turn = t_u["turn_index"]
            turn_dist = abs(s_turn - t_turn)
            signed_turn_delta = s_turn - t_turn  # Positive means src is in later turn

            s_idx = unit_pos[src]
            t_idx = unit_pos[tgt]
            unit_dist = abs(s_idx - t_idx)
            signed_unit_delta = s_idx - t_idx  # Positive means src appears later in transcript

            same_speaker = (s_u["speaker_id"] == t_u["speaker_id"])
            same_turn = (s_turn == t_turn)

            if pair not in pair_map:
                pair_map[pair] = {
                    "source_unit_id": src,
                    "target_unit_id": tgt,
                    "source_turn_index": s_turn,
                    "target_turn_index": t_turn,
                    "turn_distance": turn_dist,
                    "signed_turn_delta": signed_turn_delta,
                    "source_unit_index": s_idx,
                    "target_unit_index": t_idx,
                    "unit_distance": unit_dist,
                    "signed_unit_delta": signed_unit_delta,
                    "same_speaker": same_speaker,
                    "same_turn": same_turn,
                    "labels": {ann_name: lbl},
                    "source_component": s_u.get("component_label"),
                    "target_component": t_u.get("component_label"),
                    "source_text": s_u.get("unit_text"),
                    "target_text": t_u.get("unit_text"),
                }
            else:
                pair_map[pair]["labels"][ann_name] = lbl

    return list(pair_map.values())


def compute_distance_statistics(relations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics for turn and unit distances."""
    if not relations:
        return {"count": 0}

    td = [r["turn_distance"] for r in relations]
    ud = [r["unit_distance"] for r in relations]

    def _stats(arr: List[int]) -> Dict[str, Any]:
        return {
            "min": int(np.min(arr)),
            "median": float(np.median(arr)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "max": int(np.max(arr)),
            "mean": float(round(np.mean(arr), 2)),
            "counts": {int(k): int(v) for k, v in zip(*np.unique(arr, return_counts=True))},
        }

    return {
        "count": len(relations),
        "turn_distance": _stats(td),
        "unit_distance": _stats(ud),
    }


def simulate_candidate_windows(
    debates_data: Dict[str, Any],
    max_k: int = 6,
) -> Dict[str, Any]:
    """Simulate candidate pair generation across various strategies and windows."""
    results: Dict[str, Any] = {
        "directional_turn": {},
        "bidirectional_turn": {},
        "unit_window": {},
    }

    # Extract all unique positive pairs per debate
    debate_pos_pairs: Dict[str, Set[Tuple[str, str]]] = {}
    total_pos = 0
    for d_key, d_info in debates_data.items():
        unique_rels = extract_unique_positive_relations(d_info)
        pairs = {(r["source_unit_id"], r["target_unit_id"]) for r in unique_rels}
        debate_pos_pairs[d_key] = pairs
        total_pos += len(pairs)

    windows = list(range(max_k + 1)) + [999]  # 999 = unlimited/all

    # 1. Directional Turn Window: turn(source) >= turn(target), delta_turn <= k
    for k in windows:
        k_label = str(k) if k < 999 else "All"
        cand_count = 0
        captured = 0

        for d_key, d_info in debates_data.items():
            units = d_info["annotator_A"]["units"]
            pos = debate_pos_pairs[d_key]
            n = len(units)

            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    s = units[i]
                    t = units[j]
                    if s["turn_index"] >= t["turn_index"]:
                        td = s["turn_index"] - t["turn_index"]
                        if td <= k:
                            cand_count += 1
                            if (s["unit_id"], t["unit_id"]) in pos:
                                captured += 1

        recall = (captured / total_pos * 100.0) if total_pos > 0 else 0.0
        density = (captured / cand_count * 100.0) if cand_count > 0 else 0.0
        results["directional_turn"][k_label] = {
            "k": k_label,
            "candidates": cand_count,
            "captured_positive": captured,
            "total_positive": total_pos,
            "recall_pct": round(recall, 2),
            "positive_density_pct": round(density, 2),
            "negative_ratio": f"{round((cand_count - captured) / captured, 1)}:1" if captured > 0 else "N/A",
        }

    # 2. Bidirectional Turn Window: |turn(source) - turn(target)| <= k (no chronology filter)
    for k in windows:
        k_label = str(k) if k < 999 else "All"
        cand_count = 0
        captured = 0

        for d_key, d_info in debates_data.items():
            units = d_info["annotator_A"]["units"]
            pos = debate_pos_pairs[d_key]
            n = len(units)

            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    s = units[i]
                    t = units[j]
                    td = abs(s["turn_index"] - t["turn_index"])
                    if td <= k:
                        cand_count += 1
                        if (s["unit_id"], t["unit_id"]) in pos:
                            captured += 1

        recall = (captured / total_pos * 100.0) if total_pos > 0 else 0.0
        density = (captured / cand_count * 100.0) if cand_count > 0 else 0.0
        results["bidirectional_turn"][k_label] = {
            "k": k_label,
            "candidates": cand_count,
            "captured_positive": captured,
            "total_positive": total_pos,
            "recall_pct": round(recall, 2),
            "positive_density_pct": round(density, 2),
            "negative_ratio": f"{round((cand_count - captured) / captured, 1)}:1" if captured > 0 else "N/A",
        }

    # 3. Unit-distance window w: |idx_s - idx_t| <= w
    unit_windows = [1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 999]
    for w in unit_windows:
        w_label = str(w) if w < 999 else "All"
        cand_count = 0
        captured = 0

        for d_key, d_info in debates_data.items():
            units = d_info["annotator_A"]["units"]
            pos = debate_pos_pairs[d_key]
            n = len(units)

            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    if abs(i - j) <= w:
                        cand_count += 1
                        if (units[i]["unit_id"], units[j]["unit_id"]) in pos:
                            captured += 1

        recall = (captured / total_pos * 100.0) if total_pos > 0 else 0.0
        density = (captured / cand_count * 100.0) if cand_count > 0 else 0.0
        results["unit_window"][w_label] = {
            "w": w_label,
            "candidates": cand_count,
            "captured_positive": captured,
            "total_positive": total_pos,
            "recall_pct": round(recall, 2),
            "positive_density_pct": round(density, 2),
            "negative_ratio": f"{round((cand_count - captured) / captured, 1)}:1" if captured > 0 else "N/A",
        }

    return results


def run_full_calibration_analysis() -> Dict[str, Any]:
    """Run complete calibration analysis and return structured results."""
    data = load_debate_pilot_data()

    report: Dict[str, Any] = {
        "debates": {},
        "combined_unique_relations": [],
        "overall_stats": {},
        "stats_by_relation_type": {},
        "stats_by_debate": {},
        "label_disagreements": [],
        "simulations": {},
    }

    all_unique_rels: List[Dict[str, Any]] = []

    for d_num in PILOT_DEBATES:
        d_key = f"debate_{d_num}"
        d_info = data[d_key]
        unique_rels = extract_unique_positive_relations(d_info)

        # Check label disagreements
        for r in unique_rels:
            labels = r["labels"]
            if len(labels) == 2 and labels["annotator_A"] != labels["annotator_B"]:
                report["label_disagreements"].append({
                    "debate": d_key,
                    "pair": f"{r['source_unit_id']}->{r['target_unit_id']}",
                    "annotator_A": labels["annotator_A"],
                    "annotator_B": labels["annotator_B"],
                    "turn_distance": r["turn_distance"],
                    "unit_distance": r["unit_distance"],
                })

        report["debates"][d_key] = {
            "unique_positive_count": len(unique_rels),
            "relations": unique_rels,
            "stats": compute_distance_statistics(unique_rels),
        }
        all_unique_rels.extend(unique_rels)

    report["combined_unique_relations"] = all_unique_rels
    report["overall_stats"] = compute_distance_statistics(all_unique_rels)

    # By relation type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for r in all_unique_rels:
        # Use annotator A label as reference or combined
        lbl = r["labels"].get("annotator_A", r["labels"].get("annotator_B"))
        by_type.setdefault(lbl, []).append(r)

    for lbl, rels in by_type.items():
        report["stats_by_relation_type"][lbl] = compute_distance_statistics(rels)

    # Simulations
    report["simulations"] = simulate_candidate_windows(data)

    return report


if __name__ == "__main__":
    rep = run_full_calibration_analysis()
    ov = rep["overall_stats"]
    print("=" * 70)
    print("ARGUMAP RELATION CANDIDATE-PAIR WINDOW CALIBRATION")
    print("=" * 70)
    print(f"Total Unique Positive Edges: {ov['count']}")
    print(f"Turn Distance Distribution: {ov['turn_distance']['counts']}")
    print(f"Turn Dist Quantiles: Median={ov['turn_distance']['median']}, p90={ov['turn_distance']['p90']}, p95={ov['turn_distance']['p95']}, Max={ov['turn_distance']['max']}")
    print(f"Unit Distance Distribution: {ov['unit_distance']['counts']}")
    print(f"Unit Dist Quantiles: Median={ov['unit_distance']['median']}, p90={ov['unit_distance']['p90']}, p95={ov['unit_distance']['p95']}, Max={ov['unit_distance']['max']}")
    
    print("\n--- Directional Turn Window Simulation ---")
    print(f"{'k':>5} | {'Candidates':>12} | {'Captured':>10} | {'Recall':>8} | {'Density':>8} | {'Neg:Pos':>8}")
    for k, v in rep["simulations"]["directional_turn"].items():
        print(f"{k:>5} | {v['candidates']:>12} | {v['captured_positive']:>10} | {v['recall_pct']:>7.1f}% | {v['positive_density_pct']:>7.2f}% | {v['negative_ratio']:>8}")

    print("\n--- Bidirectional Turn Window Simulation ---")
    print(f"{'k':>5} | {'Candidates':>12} | {'Captured':>10} | {'Recall':>8} | {'Density':>8} | {'Neg:Pos':>8}")
    for k, v in rep["simulations"]["bidirectional_turn"].items():
        print(f"{k:>5} | {v['candidates']:>12} | {v['captured_positive']:>10} | {v['recall_pct']:>7.1f}% | {v['positive_density_pct']:>7.2f}% | {v['negative_ratio']:>8}")
