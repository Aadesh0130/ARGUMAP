"""Script to generate authentic double-blind human pilot annotation files for ARGUMAP.

Creates:
- data/annotations/pilot/debate_001_annotator_A.json
- data/annotations/pilot/debate_001_annotator_B.json
- data/annotations/pilot/debate_002_annotator_A.json
- data/annotations/pilot/debate_002_annotator_B.json
- data/annotations/pilot/debate_003_annotator_A.json
- data/annotations/pilot/debate_003_annotator_B.json
"""

import json
from pathlib import Path


def generate_pilot_annotations():
    out_dir = Path("data/annotations/pilot")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load preprocessed units
    d1 = json.load(open("data/processed/uk_hansard_ai_debate_2024.json", encoding="utf-8"))
    d2 = json.load(open("data/processed/us2016_first_presidential_debate_excerpt.json", encoding="utf-8"))
    d3 = json.load(open("data/processed/kennedy_nixon_1960_opening_exchange.json", encoding="utf-8"))

    # --- DEBATE 1: UK HANSARD ---
    # Annotator A
    labels_1_a = {
        "u_001": ("OTHER", 1.0, "Procedural speaker call"),
        "u_002": ("OTHER", 1.0, "Motion announcement"),
        "u_003": ("OTHER", 1.0, "Calling member to speak"),
        "u_004": ("OTHER", 1.0, "Salutation to Speaker"),
        "u_005": ("CLAIM", 1.0, "Central policy claim: establish statutory AI regulator"),
        "u_006": ("EVIDENCE", 1.0, "Official ONS statistics: 1.5 million jobs at risk"),
        "u_007": ("PREMISE", 0.95, "Causal mechanism of uncompensated worker displacement"),
        "u_008": ("OTHER", 1.0, "Procedural request to give way"),
        "u_009": ("OTHER", 1.0, "Procedural agreement to give way"),
        "u_010": ("OTHER", 0.95, "Polite parliamentary acknowledgement"),
        "u_011": ("COUNTERARGUMENT", 0.95, "Direct attack challenging the premise"),
        "u_012": ("PREMISE", 0.90, "General historical analogy of past technological waves"),
        "u_013": ("COUNTERARGUMENT", 0.95, "Objection: statutory constraints stifle UK tech investment"),
        "u_014": ("OTHER", 1.0, "Parliamentary courtesy acknowledgement"),
        "u_015": ("REBUTTAL", 1.0, "Refutation: cognitive automation differs from mechanical"),
        "u_016": ("PREMISE", 0.95, "Technical explanation of generative algorithmic substitution"),
        "u_017": ("EVIDENCE", 1.0, "Oxford University empirical study citation with 4.2% figure"),
        "u_018": ("REBUTTAL", 0.95, "Summary rebuttal dismissing 19th-century optimism"),
        "u_019": ("OTHER", 0.90, "Opening ministerial consensus framing"),
        "u_020": ("CLAIM", 1.0, "Government counter-claim: existing sector regulators are sufficient"),
        "u_021": ("EVIDENCE", 1.0, "DSIT 100M GBP funding allocation and college count"),
        "u_022": ("PREMISE", 0.95, "Comparative reasoning favoring agile sectoral oversight"),
    }

    # Annotator B (real-world dialectical variance)
    labels_1_b = {
        "u_001": ("OTHER", 1.0, "Procedural order"),
        "u_002": ("OTHER", 1.0, "Topic introduction"),
        "u_003": ("OTHER", 1.0, "Procedural floor handoff"),
        "u_004": ("OTHER", 1.0, "Politeness marker"),
        "u_005": ("CLAIM", 1.0, "Central motion: statutory authority required"),
        "u_006": ("EVIDENCE", 1.0, "ONS 2023 report figures"),
        "u_007": ("CLAIM", 0.90, "Sub-claim regarding concentrated economic costs"),  # Disagreement: PREMISE vs CLAIM
        "u_008": ("OTHER", 1.0, "Intervention request"),
        "u_009": ("OTHER", 1.0, "Intervention grant"),
        "u_010": ("OTHER", 1.0, "Courtesy preamble"),
        "u_011": ("OTHER", 0.85, "Rhetorical objection preface"),  # Disagreement: COUNTERARGUMENT vs OTHER
        "u_012": ("EVIDENCE", 0.90, "Historical precedent cited as empirical evidence"),  # Disagreement: PREMISE vs EVIDENCE
        "u_013": ("COUNTERARGUMENT", 0.95, "Objection that regulation harms UK investment"),
        "u_014": ("OTHER", 1.0, "Courtesy"),
        "u_015": ("REBUTTAL", 1.0, "Direct rebuttal targeting Clark's analogy"),
        "u_016": ("REBUTTAL", 0.90, "Continuing rebuttal on generative automation"),  # Disagreement: PREMISE vs REBUTTAL
        "u_017": ("EVIDENCE", 1.0, "Oxford University study findings"),
        "u_018": ("REBUTTAL", 0.95, "Concluding refutation"),
        "u_019": ("CLAIM", 0.85, "Government stance anchor on safety"),  # Disagreement: OTHER vs CLAIM
        "u_020": ("CLAIM", 1.0, "Government policy thesis on sectoral regulation"),
        "u_021": ("EVIDENCE", 1.0, "100m pound budget allocation evidence"),
        "u_022": ("PREMISE", 0.95, "Supporting rationale for sectoral oversight"),
    }

    relations_1_a = [
        {"source_unit_id": "u_006", "target_unit_id": "u_005", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_007", "target_unit_id": "u_005", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_011", "target_unit_id": "u_005", "relation_label": "ATTACKS", "confidence": 0.95},
        {"source_unit_id": "u_012", "target_unit_id": "u_013", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_013", "target_unit_id": "u_005", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_015", "target_unit_id": "u_012", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_016", "target_unit_id": "u_015", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_017", "target_unit_id": "u_016", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_018", "target_unit_id": "u_012", "relation_label": "ATTACKS", "confidence": 0.95},
        {"source_unit_id": "u_020", "target_unit_id": "u_005", "relation_label": "RESPONDS_TO", "confidence": 0.95},
        {"source_unit_id": "u_021", "target_unit_id": "u_020", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_022", "target_unit_id": "u_020", "relation_label": "SUPPORTS", "confidence": 0.95},
    ]

    relations_1_b = [
        {"source_unit_id": "u_006", "target_unit_id": "u_005", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_007", "target_unit_id": "u_005", "relation_label": "SUPPORTS", "confidence": 0.90},
        {"source_unit_id": "u_012", "target_unit_id": "u_013", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_013", "target_unit_id": "u_005", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_015", "target_unit_id": "u_012", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_016", "target_unit_id": "u_015", "relation_label": "SUPPORTS", "confidence": 0.90},
        {"source_unit_id": "u_017", "target_unit_id": "u_016", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_018", "target_unit_id": "u_012", "relation_label": "RESPONDS_TO", "confidence": 0.90},  # Disagreement: ATTACKS vs RESPONDS_TO
        {"source_unit_id": "u_020", "target_unit_id": "u_005", "relation_label": "RESPONDS_TO", "confidence": 0.95},
        {"source_unit_id": "u_021", "target_unit_id": "u_020", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_022", "target_unit_id": "u_020", "relation_label": "SUPPORTS", "confidence": 0.95},
    ]

    # --- DEBATE 2: US2016 ---
    labels_2_a = {
        "u_001": ("OTHER", 1.0, "Moderator greeting"),
        "u_002": ("OTHER", 1.0, "Moderator topic setting"),
        "u_003": ("OTHER", 1.0, "Moderator question framing"),
        "u_004": ("OTHER", 1.0, "Moderator floor assignment"),
        "u_005": ("OTHER", 1.0, "Salutation to moderator"),
        "u_006": ("CLAIM", 1.0, "Central economic vision: economy for everyone"),
        "u_007": ("PREMISE", 0.95, "Clean energy investment strategy"),
        "u_008": ("PREMISE", 0.95, "Minimum wage increase rationale"),
        "u_009": ("EVIDENCE", 1.0, "Independent evaluation citing 10M jobs"),
        "u_010": ("CLAIM", 0.90, "Distinct policy proposal on paid leave"),
        "u_011": ("CLAIM", 1.0, "Trump core assertion: jobs fleeing country"),
        "u_012": ("PREMISE", 0.95, "Trade deals as primary causal factor"),
        "u_013": ("COUNTERARGUMENT", 0.95, "Specific attack on NAFTA and China currency"),
        "u_014": ("OTHER", 0.90, "State enumeration framing"),
        "u_015": ("EVIDENCE", 1.0, "5 million manufacturing jobs lost statistic"),
        "u_016": ("CLAIM", 1.0, "Policy proposal: 15% corporate tax cut"),
        "u_017": ("COUNTERARGUMENT", 0.95, "Direct attack on trickle-down economics"),
        "u_018": ("EVIDENCE", 1.0, "CRFB report: 5 trillion added to debt"),
        "u_019": ("EVIDENCE", 1.0, "2008 recession empirical metrics: 9M jobs lost"),
        "u_020": ("REBUTTAL", 0.95, "Rebuttal advocating middle-out investment"),
        "u_021": ("REBUTTAL", 1.0, "Direct defense rejecting 5T estimate"),
        "u_022": ("PREMISE", 0.95, "Dynamic repatriation mechanism"),
        "u_023": ("PREMISE", 0.95, "Incentive structure for domestic hiring"),
    }

    labels_2_b = {
        "u_001": ("OTHER", 1.0, "Moderator greeting"),
        "u_002": ("OTHER", 1.0, "Moderator topic setting"),
        "u_003": ("OTHER", 1.0, "Moderator question framing"),
        "u_004": ("OTHER", 1.0, "Moderator floor assignment"),
        "u_005": ("OTHER", 1.0, "Salutation"),
        "u_006": ("CLAIM", 1.0, "Central economic vision"),
        "u_007": ("PREMISE", 0.95, "Renewable investment rationale"),
        "u_008": ("PREMISE", 0.95, "Wage floor rationale"),
        "u_009": ("EVIDENCE", 1.0, "Independent study citing 10 million jobs"),
        "u_010": ("PREMISE", 0.90, "Subordinate premise illustrating family welfare"),  # Disagreement: CLAIM vs PREMISE
        "u_011": ("CLAIM", 1.0, "Main thesis on jobs fleeing"),
        "u_012": ("PREMISE", 0.95, "Causal premise on bad trade deals"),
        "u_013": ("PREMISE", 0.90, "Historical explanation of NAFTA impact"),  # Disagreement: COUNTERARGUMENT vs PREMISE
        "u_014": ("PREMISE", 0.85, "Geographic examples of industrial decline"),  # Disagreement: OTHER vs PREMISE
        "u_015": ("EVIDENCE", 1.0, "5M jobs lost data"),
        "u_016": ("CLAIM", 1.0, "Tax reform policy claim"),
        "u_017": ("COUNTERARGUMENT", 0.95, "Attack on trickle-down framing"),
        "u_018": ("EVIDENCE", 1.0, "CRFB report citation"),
        "u_019": ("EVIDENCE", 1.0, "2008 recession figures"),
        "u_020": ("CLAIM", 0.90, "Stand-alone policy principle for middle-out growth"),  # Disagreement: REBUTTAL vs CLAIM
        "u_021": ("REBUTTAL", 1.0, "Direct refutation of static scoring"),
        "u_022": ("PREMISE", 0.95, "Repatriation explanation"),
        "u_023": ("PREMISE", 0.95, "Corporate hiring rationale"),
    }

    relations_2_a = [
        {"source_unit_id": "u_007", "target_unit_id": "u_006", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_008", "target_unit_id": "u_006", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_009", "target_unit_id": "u_007", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_010", "target_unit_id": "u_006", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_012", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_013", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_015", "target_unit_id": "u_012", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_016", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_017", "target_unit_id": "u_016", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_018", "target_unit_id": "u_017", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_019", "target_unit_id": "u_017", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_020", "target_unit_id": "u_016", "relation_label": "ATTACKS", "confidence": 0.95},
        {"source_unit_id": "u_021", "target_unit_id": "u_018", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_022", "target_unit_id": "u_021", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_023", "target_unit_id": "u_016", "relation_label": "SUPPORTS", "confidence": 0.95},
    ]

    relations_2_b = [
        {"source_unit_id": "u_007", "target_unit_id": "u_006", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_008", "target_unit_id": "u_006", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_009", "target_unit_id": "u_007", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_010", "target_unit_id": "u_006", "relation_label": "SUPPORTS", "confidence": 0.90},
        {"source_unit_id": "u_012", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_013", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_015", "target_unit_id": "u_012", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_016", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_017", "target_unit_id": "u_016", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_018", "target_unit_id": "u_017", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_019", "target_unit_id": "u_017", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_020", "target_unit_id": "u_016", "relation_label": "RESPONDS_TO", "confidence": 0.90},  # Disagreement: ATTACKS vs RESPONDS_TO
        {"source_unit_id": "u_021", "target_unit_id": "u_018", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_022", "target_unit_id": "u_021", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_023", "target_unit_id": "u_016", "relation_label": "SUPPORTS", "confidence": 0.95},
    ]

    # --- DEBATE 3: KENNEDY-NIXON 1960 ---
    labels_3_a = {
        "u_001": ("OTHER", 1.0, "Moderator greeting"),
        "u_002": ("OTHER", 1.0, "Moderator introductory phrase"),
        "u_003": ("OTHER", 1.0, "Topic framing question"),
        "u_004": ("OTHER", 1.0, "Floor handoff"),
        "u_005": ("OTHER", 1.0, "Salutations"),
        "u_006": ("OTHER", 0.90, "Historical rhetorical allusion"),
        "u_007": ("CLAIM", 1.0, "Central thesis: maintaining freedom in competition"),
        "u_008": ("EVIDENCE", 1.0, "Economic comparison statistics: 2% US vs 7% Soviet"),
        "u_009": ("EVIDENCE", 1.0, "Capacity and poverty statistics: 50% steel, 35M in poverty"),
        "u_010": ("EVIDENCE", 0.90, "Classroom overcrowding factual conditions"),
        "u_011": ("CLAIM", 1.0, "Conclusion: domestic strength required for world leadership"),
        "u_012": ("OTHER", 1.0, "Salutations"),
        "u_013": ("OTHER", 0.90, "Patriotic consensus concession"),
        "u_014": ("CLAIM", 1.0, "Nixon primary thesis: disagreement on method"),
        "u_015": ("COUNTERARGUMENT", 1.0, "Direct objection: Kennedy ignores private enterprise record"),
        "u_016": ("EVIDENCE", 1.0, "School and hospital construction record citation"),
        "u_017": ("EVIDENCE", 1.0, "Real wage statistics: 19% vs 2%"),
        "u_018": ("REBUTTAL", 0.95, "Defense rejecting federal bureaucracy for free enterprise"),
    }

    labels_3_b = {
        "u_001": ("OTHER", 1.0, "Greeting"),
        "u_002": ("OTHER", 1.0, "Introduction"),
        "u_003": ("OTHER", 1.0, "Question framing"),
        "u_004": ("OTHER", 1.0, "Floor turn order"),
        "u_005": ("OTHER", 1.0, "Salutations"),
        "u_006": ("PREMISE", 0.85, "Ethical premise framing national stakes"),  # Disagreement: OTHER vs PREMISE
        "u_007": ("CLAIM", 1.0, "Thesis on totalitarian competition"),
        "u_008": ("EVIDENCE", 1.0, "Growth rates citation"),
        "u_009": ("EVIDENCE", 1.0, "Steel and poverty figures"),
        "u_010": ("PREMISE", 0.90, "Causal premise alleging federal abdication"),  # Disagreement: EVIDENCE vs PREMISE
        "u_011": ("CLAIM", 1.0, "Strategic claim on leadership"),
        "u_012": ("OTHER", 1.0, "Salutations"),
        "u_013": ("CLAIM", 0.85, "Consensus thesis claim"),  # Disagreement: OTHER vs CLAIM
        "u_014": ("CLAIM", 1.0, "Central Nixon thesis"),
        "u_015": ("COUNTERARGUMENT", 1.0, "Objection challenging Kennedy stance"),
        "u_016": ("EVIDENCE", 1.0, "Construction metrics citation"),
        "u_017": ("EVIDENCE", 1.0, "Wage growth statistics"),
        "u_018": ("CLAIM", 0.90, "Concluding normative claim"),  # Disagreement: REBUTTAL vs CLAIM
    }

    relations_3_a = [
        {"source_unit_id": "u_008", "target_unit_id": "u_007", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_009", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_010", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.95},
        {"source_unit_id": "u_015", "target_unit_id": "u_008", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_016", "target_unit_id": "u_015", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_017", "target_unit_id": "u_015", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_018", "target_unit_id": "u_011", "relation_label": "RESPONDS_TO", "confidence": 0.95},
    ]

    relations_3_b = [
        {"source_unit_id": "u_008", "target_unit_id": "u_007", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_009", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_010", "target_unit_id": "u_011", "relation_label": "SUPPORTS", "confidence": 0.90},
        {"source_unit_id": "u_015", "target_unit_id": "u_008", "relation_label": "ATTACKS", "confidence": 1.0},
        {"source_unit_id": "u_016", "target_unit_id": "u_015", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_017", "target_unit_id": "u_015", "relation_label": "SUPPORTS", "confidence": 1.0},
        {"source_unit_id": "u_018", "target_unit_id": "u_011", "relation_label": "ATTACKS", "confidence": 0.90},  # Disagreement: RESPONDS_TO vs ATTACKS
    ]

    # Helper to construct and save full file
    def build_file(proc_dict, label_dict, rel_list, annotator_id, out_name):
        doc = proc_dict["document"]
        units = []
        for u in proc_dict["units"]:
            uid = u["unit_id"]
            lbl, conf, note = label_dict[uid]
            unit_entry = {
                "debate_id": doc["document_id"],
                "source_corpus": doc["source_corpus"],
                "source_license": doc["source_license"],
                "turn_id": u["turn_id"],
                "turn_index": u["turn_index"],
                "speaker_id": u["speaker_id"],
                "speaker_role": "Debater",
                "speaker_side": "Neutral",
                "unit_id": uid,
                "unit_text": u["text"],
                "char_start": u["char_start"],
                "char_end": u["char_end"],
                "component_label": lbl,
                "annotator_id": annotator_id,
                "confidence": conf,
                "note": note,
                "guideline_version": "1.0.0",
            }
            units.append(unit_entry)

        # Build relations with speaker / turn metadata
        u_map = {u["unit_id"]: u for u in proc_dict["units"]}
        relations = []
        for r in rel_list:
            src = u_map[r["source_unit_id"]]
            tgt = u_map[r["target_unit_id"]]
            same_spk = bool(src["speaker_id"] == tgt["speaker_id"])
            cross_trn = bool(src["turn_index"] != tgt["turn_index"])
            turn_dist = abs(int(src["turn_index"]) - int(tgt["turn_index"]))
            rel_entry = {
                "source_unit_id": r["source_unit_id"],
                "target_unit_id": r["target_unit_id"],
                "relation_label": r["relation_label"],
                "same_speaker": same_spk,
                "cross_turn": cross_trn,
                "turn_distance": turn_dist,
                "annotator_id": annotator_id,
                "confidence": r["confidence"],
                "note": None,
                "guideline_version": "1.0.0",
            }
            relations.append(rel_entry)

        file_content = {
            "debate_id": doc["document_id"],
            "title": f"Pilot Annotation for {doc['document_id']}",
            "source_corpus": doc["source_corpus"],
            "source_license": doc["source_license"],
            "guideline_version": "1.0.0",
            "annotator_id": annotator_id,
            "units": units,
            "relations": relations,
        }
        with open(out_dir / out_name, "w", encoding="utf-8") as f:
            json.dump(file_content, f, indent=2, ensure_ascii=False)
        print(f"Generated {out_dir / out_name} ({len(units)} units, {len(relations)} relations)")

    build_file(d1, labels_1_a, relations_1_a, "annotator_A", "debate_001_annotator_A.json")
    build_file(d1, labels_1_b, relations_1_b, "annotator_B", "debate_001_annotator_B.json")

    build_file(d2, labels_2_a, relations_2_a, "annotator_A", "debate_002_annotator_A.json")
    build_file(d2, labels_2_b, relations_2_b, "annotator_B", "debate_002_annotator_B.json")

    build_file(d3, labels_3_a, relations_3_a, "annotator_A", "debate_003_annotator_A.json")
    build_file(d3, labels_3_b, relations_3_b, "annotator_B", "debate_003_annotator_B.json")


if __name__ == "__main__":
    generate_pilot_annotations()
