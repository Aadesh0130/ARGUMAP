#!/usr/bin/env python3
"""Preprocessor and Unitizer for the Authentic UK Hansard Lords AI Debate (2023).

Performs:
1. Integrity verification of data/raw/hansard/hansard_lords_ai_debate_2023.txt against provenance SHA-256.
2. Turn extraction and speaker attribution across all 29 turns.
3. Sentence-level proposition segmentation into stable argument units.
4. Calculation and verification of exact character offsets (turn within raw text; unit within turn text).
5. Generation of:
   - data/processed/hansard_lords_ai_debate_2023.json
   - data/annotations/templates/debate_001_annotator_A_template.json
   - data/annotations/templates/debate_001_annotator_B_template.json
"""

import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def split_sentences_with_spans(text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
    """Segment a turn's speech text into sentence proposition units and return exact spans.
    
    Protects common abbreviations (Lord, Dr, Mr, Mrs, Ms, Prof, etc.) to prevent false splits.
    Guarantees that text[start:end] == unit_text for all generated spans.
    """
    protected = text
    abbrevs = [
        'Lord', 'Dr', 'Mr', 'Mrs', 'Ms', 'Prof', 'Vol', 'Col', 'No', 'Gov',
        'etc', 'i.e', 'e.g', 'vs', 'Hon', 'Rt', 'St'
    ]
    for ab in abbrevs:
        protected = re.sub(rf'\b{ab}\.', f'{ab}__DOT__', protected)

    # Regex matches sentence terminal punctuation followed by space/newline and uppercase letter/quote
    pattern = re.compile(r'([.!?])(?:\s+|\n+)(?=[A-Z0-9"\'“‘]|\Z)')

    sents: List[str] = []
    spans: List[Tuple[int, int]] = []
    last_end = 0

    for match in pattern.finditer(protected):
        punct_end = match.end(1)
        sent = text[last_end:punct_end].strip()
        if sent:
            start = text.find(sent, last_end)
            end = start + len(sent)
            assert text[start:end] == sent, f"Span mismatch: {text[start:end]!r} != {sent!r}"
            sents.append(sent)
            spans.append((start, end))
            last_end = match.end()

    # Remaining tail
    tail = text[last_end:].strip()
    if tail:
        start = text.find(tail, last_end)
        end = start + len(tail)
        assert text[start:end] == tail, f"Span mismatch on tail: {text[start:end]!r} != {tail!r}"
        sents.append(tail)
        spans.append((start, end))

    return sents, spans


def preprocess_hansard_2023():
    raw_path = PROJECT_ROOT / "data" / "raw" / "hansard" / "hansard_lords_ai_debate_2023.txt"
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw transcript not found: {raw_path}")

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # 1. Verify provenance checksum
    calculated_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    prov_path = PROJECT_ROOT / "data" / "raw" / "provenance.json"
    with open(prov_path, "r", encoding="utf-8") as f:
        prov = json.load(f)
    doc_prov = next((d for d in prov["documents"] if d["document_id"] == "hansard_lords_ai_debate_2023"), None)
    if not doc_prov:
        raise ValueError("hansard_lords_ai_debate_2023 not found in provenance.json")
    if calculated_sha != doc_prov["checksum_sha256"]:
        raise ValueError(
            f"Provenance checksum mismatch: expected {doc_prov['checksum_sha256']}, got {calculated_sha}"
        )
    print(f"[OK] Checksum match verified: {calculated_sha}")

    # 2. Extract turns
    turn_blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]
    print(f"[OK] Parsed {len(turn_blocks)} turn blocks.")
    assert len(turn_blocks) == 29, f"Expected 29 turns, got {len(turn_blocks)}"

    speakers_dict: Dict[str, Dict[str, Any]] = {}
    turns_list: List[Dict[str, Any]] = []
    units_list: List[Dict[str, Any]] = []

    unit_global_idx = 0
    doc_cursor = 0

    for turn_idx, block in enumerate(turn_blocks):
        if ":" not in block:
            raise ValueError(f"Turn {turn_idx} missing speaker prefix colon: {block[:50]}")
        speaker_name, speech_text = block.split(":", 1)
        speaker_name = speaker_name.strip()
        speech_text = speech_text.strip()

        # Turn level speaker ID
        spk_key = speaker_name.lower().replace(" ", "_")
        if spk_key not in speakers_dict:
            spk_id = f"spk_{len(speakers_dict) + 1:03d}"
            role = "Minister" if "Minister" in speaker_name or "Camrose" in speaker_name else "Debater"
            speakers_dict[spk_key] = {
                "speaker_id": spk_id,
                "speaker_name": speaker_name,
                "speaker_role": role,
                "speaker_side": "Government" if role == "Minister" else "Neutral"
            }
        spk_id = speakers_dict[spk_key]["speaker_id"]

        turn_id = f"turn_{turn_idx + 1:03d}"

        # Find turn speech offsets in raw_text
        block_pos = raw_text.find(block, doc_cursor)
        assert block_pos != -1, f"Block position not found for turn {turn_idx}"
        speech_in_block = block.find(speech_text)
        speech_char_start = block_pos + speech_in_block
        speech_char_end = speech_char_start + len(speech_text)
        assert raw_text[speech_char_start:speech_char_end] == speech_text
        doc_cursor = block_pos + len(block)

        turns_list.append({
            "turn_id": turn_id,
            "turn_index": turn_idx,
            "speaker_id": spk_id,
            "speaker_name": speaker_name,
            "text": speech_text,
            "char_start": speech_char_start,
            "char_end": speech_char_end
        })

        # Segment speech into proposition units
        sents, spans = split_sentences_with_spans(speech_text)
        for sent_idx, (sent_text, (c_start, c_end)) in enumerate(zip(sents, spans)):
            assert speech_text[c_start:c_end] == sent_text
            unit_id = f"u_{unit_global_idx + 1:04d}"
            unit_global_idx += 1

            units_list.append({
                "unit_id": unit_id,
                "document_id": "uk_hansard_lords_2023",
                "turn_id": turn_id,
                "speaker_id": spk_id,
                "speaker_name": speaker_name,
                "turn_index": turn_idx,
                "unit_index": unit_global_idx - 1,
                "text": sent_text,
                "char_start": c_start,
                "char_end": c_end,
                "sentence_index": sent_idx,
                "component_label": None
            })

    print(f"[OK] Generated {len(units_list)} argument units across {len(turns_list)} turns and {len(speakers_dict)} speakers.")

    # 3. Construct processed representation
    processed_doc = {
        "document": {
            "document_id": "uk_hansard_lords_2023",
            "source_corpus": "uk_parliament_hansard",
            "source_license": "Open Parliament Licence v3.0",
            "source_url": "https://hansard.parliament.uk/Lords/2023-07-24/debates/5432715E-F305-4EC1-8A79-B9A0C6402BFF/AdvancedArtificialIntelligence",
            "attribution": "Contains Parliamentary information licensed under the Open Parliament Licence v3.0.",
            "text": raw_text,
            "metadata": {
                "raw_character_count": len(raw_text),
                "word_count": len(raw_text.split()),
                "speaker_count": len(speakers_dict),
                "turn_count": len(turns_list),
                "unit_count": len(units_list)
            }
        },
        "speakers": list(speakers_dict.values()),
        "turns": turns_list,
        "units": units_list
    }

    processed_path = PROJECT_ROOT / "data" / "processed" / "hansard_lords_ai_debate_2023.json"
    with open(processed_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(processed_doc, f, indent=2)
    print(f"[OK] Saved processed dataset to: {processed_path}")

    # 4. Construct unannotated templates for Annotator A and Annotator B
    templates_dir = PROJECT_ROOT / "data" / "annotations" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    for ann_id in ["annotator_A", "annotator_B"]:
        template_units = []
        for u in units_list:
            template_units.append({
                "debate_id": "uk_hansard_lords_2023",
                "source_corpus": "uk_parliament_hansard",
                "source_license": "Open Parliament Licence v3.0",
                "turn_id": u["turn_id"],
                "turn_index": u["turn_index"],
                "speaker_id": u["speaker_id"],
                "speaker_role": next(s["speaker_role"] for s in speakers_dict.values() if s["speaker_id"] == u["speaker_id"]),
                "speaker_side": next(s["speaker_side"] for s in speakers_dict.values() if s["speaker_id"] == u["speaker_id"]),
                "unit_id": u["unit_id"],
                "unit_text": u["text"],
                "char_start": u["char_start"],
                "char_end": u["char_end"],
                "component_label": None,  # Strictly unannotated
                "annotator_id": ann_id,
                "confidence": None,
                "note": None,
                "guideline_version": "1.1.0"
            })

        template_doc = {
            "debate_id": "uk_hansard_lords_2023",
            "title": "UK House of Lords: Advanced Artificial Intelligence Debate (24 July 2023) - Unannotated Template",
            "source_corpus": "uk_parliament_hansard",
            "source_license": "Open Parliament Licence v3.0",
            "guideline_version": "1.1.0",
            "annotator_id": ann_id,
            "status": "UNANNOTATED_TEMPLATE",
            "attribution": "Contains Parliamentary information licensed under the Open Parliament Licence v3.0.",
            "candidate_relation_policy": "provisional_directional_k3",
            "units": template_units,
            "relations": []
        }

        template_file = templates_dir / f"debate_001_{ann_id}_template.json"
        with open(template_file, "w", encoding="utf-8", newline="\n") as f:
            json.dump(template_doc, f, indent=2)
        print(f"[OK] Saved unannotated template to: {template_file}")

    print("\n[SUCCESS] Authentic Hansard transcript preprocessed and unannotated templates created successfully.")


if __name__ == "__main__":
    preprocess_hansard_2023()
