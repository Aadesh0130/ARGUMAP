"""Temporary script to inspect annotation counts."""
import json
from pathlib import Path

pilot = Path("data/annotations/pilot")
for d in ["001", "002", "003"]:
    for a in ["A", "B"]:
        f = pilot / f"debate_{d}_annotator_{a}.json"
        data = json.load(open(f, encoding="utf-8"))
        units = data.get("units", [])
        rels = data.get("relations", [])
        unit_ids = [u["unit_id"] for u in units]
        rel_pairs = [(r["source_unit_id"], r["target_unit_id"]) for r in rels]
        rel_labels = [r["relation_label"] for r in rels]
        no_rel_count = sum(1 for l in rel_labels if l == "NO_RELATION")
        print(f"debate_{d} annotator_{a}: {len(units)} units, {len(rels)} relations, {no_rel_count} NO_RELATION")
        # Check if any relation references a unit_id not in units
        all_rel_ids = set()
        for r in rels:
            all_rel_ids.add(r["source_unit_id"])
            all_rel_ids.add(r["target_unit_id"])
        missing = all_rel_ids - set(unit_ids)
        if missing:
            print(f"  WARNING: relation references missing unit IDs: {missing}")
        # Check duplicate unit IDs
        if len(unit_ids) != len(set(unit_ids)):
            print(f"  WARNING: duplicate unit IDs found")
        # Check duplicate relation pairs
        if len(rel_pairs) != len(set(rel_pairs)):
            print(f"  WARNING: duplicate relation pairs found")

    # Compare relation pairs between A and B
    fa = pilot / f"debate_{d}_annotator_A.json"
    fb = pilot / f"debate_{d}_annotator_B.json"
    da = json.load(open(fa, encoding="utf-8"))
    db = json.load(open(fb, encoding="utf-8"))
    pairs_a = set((r["source_unit_id"], r["target_unit_id"]) for r in da["relations"])
    pairs_b = set((r["source_unit_id"], r["target_unit_id"]) for r in db["relations"])
    shared = pairs_a & pairs_b
    only_a = pairs_a - pairs_b
    only_b = pairs_b - pairs_a
    n_units = len(set(u["unit_id"] for u in da["units"]) & set(u["unit_id"] for u in db["units"]))
    n_possible = n_units * (n_units - 1)
    print(f"  debate_{d}: shared_pairs={len(shared)}, only_A={len(only_a)}, only_B={len(only_b)}, shared_units={n_units}, possible_directed_pairs={n_possible}")
    # Show label agreement for shared pairs
    if shared:
        map_a = {(r["source_unit_id"], r["target_unit_id"]): r["relation_label"] for r in da["relations"]}
        map_b = {(r["source_unit_id"], r["target_unit_id"]): r["relation_label"] for r in db["relations"]}
        agree = sum(1 for p in shared if map_a[p] == map_b[p])
        print(f"  shared pair label agreement: {agree}/{len(shared)}")
        for p in sorted(shared):
            la, lb = map_a[p], map_b[p]
            mark = "OK" if la == lb else "DIFF"
            print(f"    {p}: A={la}, B={lb} {mark}")
    print()
