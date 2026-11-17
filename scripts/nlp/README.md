# ARGUMAP — NLP Preprocessing Scripts

This directory contains standalone CLI scripts and utilities for preprocessing debate discourse transcripts into structured, offset-verified argumentative units.

---

## 1. Scripts

| Script | Purpose |
| :--- | :--- |
| `preprocess_transcript.py` | Converts a raw plain text debate transcript into structured JSON (speakers, turns, units, offsets) ready for annotation or ML feature extraction. |

---

## 2. Usage Examples

### 2.1 Basic Execution (Print to stdout)
```powershell
python scripts/nlp/preprocess_transcript.py path/to/transcript.txt
```

### 2.2 Process and Save Structured JSON
```powershell
python scripts/nlp/preprocess_transcript.py path/to/transcript.txt --output output.json
```

### 2.3 Custom Document ID and Corpus Metadata
```powershell
python scripts/nlp/preprocess_transcript.py path/to/transcript.txt --output output.json --document-id debate_101 --source-corpus us2016
```

---

## 3. Output Format Guarantees

* **Document Structure:** Returns `document`, `speakers`, `turns`, `units`, `metadata`, and `validation`.
* **Zero Fabrication:** `component_label` remains strictly `null` (no fake predictions).
* **Exact Offsets:** Every unit includes character spans matching the exact substring in the parent speech turn (`turn.text[char_start:char_end] == unit.text`).
* **Reproducibility:** Running the identical transcript yields deterministic IDs, speaker attribution, and ordering.
