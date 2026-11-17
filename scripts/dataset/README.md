# ARGUMAP — Dataset Validation & Ingestion Tooling

This directory contains standalone validation, conversion, and profiling utilities for the **ARGUMAP** argument mining pipeline.

---

## 1. Tooling Overview

| Script | Purpose |
| :--- | :--- |
| `validate_dataset_manifest.py` | Validates `data/dataset_manifest.json` schema, provenance fields, and strict license statuses (`VERIFIED` vs `UNVERIFIED`). |
| `validate_annotations.py` | Validates human annotation JSON files against frozen component taxonomy, relation labels, character offset bounds, unit IDs, and non-dangling graph edges. |
| `dataset_statistics.py` | Computes formal corpus statistics (debates, speakers, turns, units, label distributions, edge counts) without fabricating data. |
| `conversion/` | Modular ingestion framework for converting external debate and argument corpora into normalized intermediate representations with full provenance tracking. |

---

## 2. Usage Examples

### 2.1 Validate Dataset Manifest
```powershell
python scripts/dataset/validate_dataset_manifest.py
```
Checks:
* Presence of required metadata fields for all registered candidate datasets.
* Explicit verification of license statuses (rejects speculative or ambiguous licenses).
* Download status conformity (`NOT_DOWNLOADED`, `DOWNLOADED`, `UNAVAILABLE`).

### 2.2 Validate Annotation Files
```powershell
python scripts/dataset/validate_annotations.py data/annotations/pilot/sample_annotation.json
```
Checks:
* Enforces frozen component labels: `CLAIM`, `PREMISE`, `EVIDENCE`, `COUNTERARGUMENT`, `REBUTTAL`, `OTHER`.
* Enforces frozen relation labels: `SUPPORTS`, `ATTACKS`, `RESPONDS_TO`, `NO_RELATION`.
* Rejects duplicate `unit_id`s, inverted offsets (`char_end <= char_start`), and out-of-range confidence scores.
* Rejects relations referencing nonexistent or dangling argument units.
* Flags self-loops (`source_unit_id == target_unit_id`).

### 2.3 Compute Dataset Statistics
```powershell
python scripts/dataset/dataset_statistics.py data/annotations/pilot/sample_annotation.json
```
Computes and outputs:
* Total debate counts, distinct speakers, and speech turns.
* Argument proposition counts and component label distribution with percentages.
* Relation count and edge type distribution (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`, `NO_RELATION`).
* Graph metrics: units per speaker and cross-turn edge ratios.
