# ARGUMAP — Pilot Annotation Workspace

This directory contains the pilot annotation template and sample schema demonstration file.

---

> [!IMPORTANT]
> **DEMO / NOT TRAINING DATA**  
> Any annotation files located within this directory are strictly illustrative demonstrations of the JSON schema, validation scripts, and tooling. They must **NEVER** be ingested into model training sets, validation folds, or benchmark evaluations.

---

## Purpose of the Annotation Pilot

The pilot phase precedes large-scale dataset annotation. Its purpose is to:
1. Test and calibrate the [ANNOTATION_GUIDELINES.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_GUIDELINES.md).
2. Measure inter-annotator agreement (Cohen's Kappa $\kappa$, Fleiss' $\kappa$) across 2–3 full debate transcripts.
3. Identify and resolve systemic edge cases (such as `CLAIM` vs `PREMISE` or `COUNTERARGUMENT` vs `REBUTTAL`).
4. Establish the empirical candidate relation pair distance window ($k$).

## Pilot Packages & Files

### Authentic UK Parliament Hansard 2023 Pilot (Current)
* `hansard_2023_pilot_annotator_A.json`: Unannotated pilot package for Annotator A (36 units, 828 candidate pairs).
* `hansard_2023_pilot_annotator_B.json`: Unannotated pilot package for Annotator B (36 units, 828 candidate pairs).
* Full protocol and selection methodology: [docs/ANNOTATION_PILOT_PROTOCOL.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_PILOT_PROTOCOL.md).

### Legacy Demonstration Artifacts (Phase 1 Pilot)
* `debate_001_annotator_A.json` / `debate_001_annotator_B.json`: Legacy pilot demo data (UNVERIFIED license).
* `debate_002_annotator_A.json` / `debate_002_annotator_B.json`: Legacy pilot demo data (UNVERIFIED license).
* `debate_003_annotator_A.json` / `debate_003_annotator_B.json`: Legacy pilot demo data (UNVERIFIED license).
* `sample_annotation.json`: Toy introductory debate transcript demonstration. Validated by `scripts/dataset/validate_annotations.py`.
