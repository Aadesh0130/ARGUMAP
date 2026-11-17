# ARGUMAP — Dataset Licensing & Provenance Audit Report

* **Document Version:** 1.1.0
* **Audit Date:** 2026-10-22
* **Governing Directives:** [AGENTS.md](file:///c:/Users/hii/Downloads/ARGUMAP/AGENTS.md) §1 (Prime Directives 1, 4, 7: Alignment, Secrets, Scientific Honesty), [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md) §6–7
* **Registry Manifest:** [data/dataset_manifest.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/dataset_manifest.json)
* **Raw Provenance Records:** [data/raw/provenance.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/raw/provenance.json)
* **Automated Test Suite:** [tests/test_dataset_licensing.py](file:///c:/Users/hii/Downloads/ARGUMAP/tests/test_dataset_licensing.py) (8 tests passing), [tests/](file:///c:/Users/hii/Downloads/ARGUMAP/tests/) (94 tests passing)

---

## 1. Executive Summary & Training Clearance Decision

Under ARGUMAP Prime Directive 7 (**Data Integrity & Scientific Honesty**), **synthetic labels, artificial benchmarks, and unverified data licenses are strictly prohibited**. Machine learning model training cannot proceed on unverified, proprietary, or legally ambiguous transcripts without compromising legal compliance, scientific rigor, and public reproducibility.

> [!IMPORTANT]
> **Implementation Verification vs. Legal Validity:**  
> Passing automated unit and integration tests verifies code implementation, data schema adherence, and gatekeeper behavior. It does **not** constitute legal certification of a source's copyright or license terms. In accordance with project instructions, this audit strictly distinguishes verified empirical facts from unresolved legal questions.

### Final Gatekeeping Decision: **MODEL TRAINING IS FULLY BLOCKED**

| Transcript / Dataset | Stated / Purported Source | Verified Legal & Provenance Status | Training Clearance | Action Required to Unblock |
| :--- | :--- | :--- | :---: | :--- |
| **`debate_001_hansard`** | UK House of Commons (2024 AI Debate) | **UNVERIFIED (Adapted/Synthetic Text; Purported OPL v3.0)** | **BLOCKED** | Text in repo does not exist in official Hansard; Dr. Sarah Wollaston was not an MP in 2024. Must replace with verified verbatim Hansard text or formally document repository author copyright. |
| **`debate_002_us2016`** | 2016 First Presidential Debate (Hofstra) | **UNVERIFIED (CPD Broadcast Copyright / 17 U.S.C. § 107 Fair Use)** | **BLOCKED** | Commission on Presidential Debates asserts copyright. Fair use protects local annotation, but downstream weight release is blocked. Replace with public domain transcript (e.g. UCSB APP) or obtain clearance. |
| **`debate_003_kennedy_nixon_1960`** | 1960 First Presidential Debate (Chicago) | **UNVERIFIED (Third-party speech/broadcast; not 17 U.S.C. § 105)** | **BLOCKED** | Campaign speeches and commercial broadcasts (CBS) are not works of the U.S. Government under 17 U.S.C. § 105. Text in repo has non-historical errors ('Governor Nixon'). Must verify copyright renewal under 1909 Act and replace with verbatim facsimile. |

> [!CAUTION]
> **ALL THREE PILOT TRANSCRIPTS ARE BLOCKED FROM MODEL TRAINING.**  
> Neither `debate_001`, `debate_002`, nor `debate_003` is currently cleared for supervised model training or public model weight distribution. The automated training gatekeeper in [tests/test_dataset_licensing.py](file:///c:/Users/hii/Downloads/ARGUMAP/tests/test_dataset_licensing.py) and [scripts/dataset/validate_dataset_manifest.py](file:///c:/Users/hii/Downloads/ARGUMAP/scripts/dataset/validate_dataset_manifest.py) programmatically enforces this block until authentic, verified sources are documented.

---

## 2. Multi-Layer Rights Analysis Methodology

In natural language processing on political discourse, licensing cannot be evaluated as a single monolithic property. Legal analysis requires distinguishing between four distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: The Underlying Spoken Discourse                    │
│ (Political campaign speech, Parliamentary privilege)        │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: The Specific Transcription & Broadcast Recording   │
│ (Broadcaster copyright, court stenographer, official GPO)   │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Database & Corpus Curation Rights                  │
│ (AIFdb, TUdatalib, Hugging Face, Kaggle data cards)         │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: The Downstream Derivative Annotations              │
│ (ARGUMAP unit segmentation, component & relation labels)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Audit of Pilot Debate Transcripts

### 3.1 Pilot Debate 001: UK Hansard AI Regulation Debate 2024

* **Document ID:** `uk_hansard_ai_debate_2024` (`debate_001_hansard`)
* **Local Raw File:** `data/raw/other/uk_hansard_ai_debate_2024.txt` (SHA-256: `78be07a5ae03542d62988b2b0d97644aebf5a41d1d2f5cd37b7d5fd4cac7960e`)
* **Purported Source:** [https://hansard.parliament.uk/](https://hansard.parliament.uk/)
* **Purported License:** Open Parliament Licence v3.0 (OPL v3.0)
* **Actual Verification Status:** **`UNVERIFIED`**
* **Training Clearance Status:** **`BLOCKED`**

#### Layer-by-Layer Rights Analysis & Provenance Audit
1. **Underlying Spoken Discourse & Speaker Verification:**
   * The text in `data/raw/other/uk_hansard_ai_debate_2024.txt` portrays a House of Commons floor debate where the Speaker calls *"Dr. Sarah Wollaston to move the motion"*, who then debates *"Mr. Greg Clark"* and *"Secretary Michelle Donelan"*.
   * **Empirical Fact Check:** Dr. Sarah Wollaston served as MP for Totnes from 2010 to 2019. She lost her seat in the 2019 General Election and was **not a Member of Parliament in 2024**.
   * **Hansard Database Search:** Querying the official UK Parliament Hansard database (`hansard.parliament.uk`) for the exact phrases (e.g., *"The government must establish an independent statutory authority to regulate autonomous workplace artificial intelligence"*) yields **zero matches**.
2. **Transcription Rights & OPL v3.0 Scope:**
   * The Open Parliament Licence v3.0 explicitly applies only to **Parliamentary information** published by the Parliamentary Estates, House of Commons, House of Lords, or Parliamentary Archives.
   * Because the text in `data/raw/other/uk_hansard_ai_debate_2024.txt` is an adapted, synthetic/curated demonstration text created to simulate parliamentary debate conventions (such as procedural requests to "give way"), it does **not** constitute official Parliamentary Information.
3. **Legal Status of the Stored Text:**
   * If authored by the creators of the ARGUMAP repository, copyright resides with the project creators (who may license it under MIT/Apache 2.0).
   * However, because it was attributed to UK Parliament without authentic provenance, its copyright status is legally **UNVERIFIED**.
4. **Action Required:**
   * Replace the file with an authentic, verbatim speech excerpt from an actual 2023–2024 AI debate published on `hansard.parliament.uk` (e.g., House of Lords AI Regulation debates).

---

### 3.2 Pilot Debate 003: Kennedy-Nixon First Presidential Debate 1960

* **Document ID:** `kennedy_nixon_1960_opening_exchange` (`debate_003_kennedy_nixon`)
* **Local Raw File:** `data/raw/other/kennedy_nixon_1960_opening_exchange.txt` (SHA-256: `5b1344ac0df021bb9a2407d2ea5e4c41da5035e05879d3a47330ce35cc91f0f0`)
* **Purported Source:** [U.S. Senate Senate Report No. 994, Part III](https://www.senate.gov/artandhistory/history/common/generic/Freedom_of_Communications_Nixon_Kennedy.htm)
* **Purported License:** Public Domain (U.S. Government Work / 17 U.S.C. § 105)
* **Actual Verification Status:** **`UNVERIFIED`**
* **Training Clearance Status:** **`BLOCKED`**

#### Layer-by-Layer Rights Analysis & Provenance Audit
1. **Underlying Spoken Discourse:**
   * Speeches delivered by Senator John F. Kennedy and Vice President Richard M. Nixon on September 26, 1960, in Chicago, IL.
   * **Legal Distinction:** Under U.S. copyright law, political campaign speeches delivered by candidates for office are private political expressions, **not** works created by federal employees in the course of their official duties. Therefore, presidential campaign debates are **not** works of the United States Government under 17 U.S.C. § 105.
2. **Broadcast & Production Rights:**
   * The debate was produced, staged, and broadcast live by commercial broadcast networks (CBS, NBC, ABC, Mutual), with Howard K. Smith of CBS News acting as moderator. CBS initially held commercial broadcast copyrights over the master recordings.
3. **Government Republication & 17 U.S.C. § 105:**
   * In 1961, the U.S. Senate Committee on Commerce reprinted transcripts in *S. Rep. No. 994, Part III: The Joint Appearances of Senator John F. Kennedy and Vice President Richard M. Nixon* (87th Cong., 1st Sess.).
   * Under established U.S. copyright doctrine (Compendium of U.S. Copyright Office Practices § 313.6(C)(2)), **reprinting or publishing non-governmental material in a government report does NOT extinguish third-party rights or place that material into the public domain**.
4. **Discrepancies in the Stored Raw Text:**
   * In `data/raw/other/kennedy_nixon_1960_opening_exchange.txt`, John F. Kennedy addresses Richard Nixon as *"Mr. Smith, Governor Nixon"*.
   * **Empirical Fact Check:** Richard Nixon was the sitting Vice President of the United States in 1960; he was never Governor of California (he ran in 1962 and lost). In the authentic historical transcript, Kennedy addressed him as *"Mr. Nixon"*.
   * The text contains modern paraphrasing (e.g. *"relentless totalitarian adversary"*) that does not appear in the GPO Senate transcript or the historical CBS broadcast.
5. **Action Required:**
   * Ingest an authentic, unabridged transcript from an established historical archive (e.g., UCSB American Presidency Project or official GPO facsimile) and verify whether the underlying 1960 broadcast fell into the public domain due to lack of statutory copyright renewal under the 1909 Copyright Act.

---

### 3.3 Pilot Debate 002: US 2016 First Presidential Debate Excerpt

* **Document ID:** `us2016_first_presidential_debate_excerpt` (`debate_002_us2016`)
* **Local Raw File:** `data/raw/us2016/us2016_first_presidential_debate_excerpt.txt` (SHA-256: `3b04ec879ced886dac3be7207d618ead8bbaab350f2f30b7d2adbc18bc7d9072`)
* **Repository Source URL:** [https://corpora.aifdb.org/US2016](https://corpora.aifdb.org/US2016)
* **Governing License:** **`UNVERIFIED` (Fair Use Claimed for Non-Commercial Research / CPD Copyright Asserted)**
* **Training Clearance Status:** **`BLOCKED`**

#### Layer-by-Layer Rights Analysis & Legal Boundaries
1. **Underlying Spoken Discourse:** Unscripted public debate statements by presidential candidates Donald Trump and Hillary Clinton, moderated by Lester Holt at Hofstra University (September 26, 2016).
2. **Broadcast & Transcription Rights:** The Commission on Presidential Debates (CPD), a private 501(c)(3) organization, asserts proprietary copyright over debate broadcasts and transcripts (*"© Copyright 2016 The Commission on Presidential Debates. All Rights Reserved"*).
3. **Fair Use Limitations (17 U.S.C. § 107):**
   * Non-commercial academic research and annotation qualify as transformative fair use.
   * However, **fair use is an affirmative defense**, not an affirmative open license. Downstream distribution of fine-tuned model weights or packaged training sets cannot rely on unadjudicated fair use of proprietary transcripts.
4. **Action Required:**
   * Replace with a verified public-domain debate (e.g. `m-arg` 2020 presidential debates, which use CC0 transcripts, or Lincoln-Douglas 1858) or obtain formal clearance.

---

## 4. Audit of External Candidate Datasets in Manifest

The nine candidate datasets cataloged in [data/dataset_manifest.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/dataset_manifest.json) have been researched against authoritative repository cards, licenses, and publications:

| Dataset ID | Name | Verified License | Access Terms & Critical Restrictions | Training Clearance | Intended V1 Role |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **`qt30`** | BBC Question Time Corpus | **CC BY-NC 4.0** | AIFdb (`corpora.aifdb.org/qt30`). Non-commercial academic research only. Commercial use strictly prohibited. | `REVIEW_REQUIRED` | Auxiliary non-commercial benchmark (Not downloaded). |
| **`elecdeb60to20`** | 60 Years US Presidential Debates | **CC BY-NC-ND 4.0** | Hugging Face (`MARIANNE-INRIA/ElecDeb60to20`). **RESTRICTION:** The NoDerivatives (ND) clause prohibits distributing modified, re-annotated, or derivative datasets. | `BLOCKED` | Read-only structural reference; disqualified from derivative training. |
| **`m-arg`** | Multimodal Argument Mining | **CC0 1.0 / CC-BY** | Mancini et al. (LREC 2022). Underlying 2020 presidential debate transcripts CC0 (Kaggle public domain); annotations CC-BY. | `REVIEW_REQUIRED` | Strongest replacement candidate for modern presidential debate (Not downloaded). |
| **`abstrct`** | AbstRCT Medical Abstracts | **CC BY-NC-SA 4.0** | GitLab (`gitlab.com/tomaye/abstrct`). Non-commercial research only; derivative annotations require ShareAlike. Non-dialogic medical literature. | `REVIEW_REQUIRED` | Auxiliary reference only (Not downloaded). |
| **`microtexts`** | Arg-Microtexts Corpus | **CC BY-NC-SA 4.0** | GitHub (`peldszus/arg-microtexts`). Non-commercial ShareAlike. Monologic short texts. | `REVIEW_REQUIRED` | Auxiliary reference for graph topology only (Not downloaded). |
| **`aae`** | Argument Annotated Essays v2 | **UNVERIFIED** | TUdatalib (`tudatalib.ulb.tu-darmstadt.de`). Custom institutional access terms; redistribution rights unverified. | `BLOCKED` | Auxiliary reference; blocked until terms verified. |
| **`ibm-evidence`** | IBM Debater Evidence Detection | **UNVERIFIED** | IBM Research Haifa. Custom IBM research license; Wikipedia text CC BY-SA 3.0. | `BLOCKED` | Auxiliary reference only. |
| **`web-discourse`** | Web Discourse Corpus | **UNVERIFIED** | UKP TU Darmstadt. Unregulated user commentary scraped from public forums. Copyright status of forum users unverified. | `BLOCKED` | Auxiliary reference only. |

---

## 5. Automated Gatekeeper Enforcement

To ensure programmatic enforcement of legal standards and prevent unauthorized training runs, ARGUMAP implements a strict gatekeeper in:
- [scripts/dataset/validate_dataset_manifest.py](file:///c:/Users/hii/Downloads/ARGUMAP/scripts/dataset/validate_dataset_manifest.py): Validates `training_clearance_status`, requiring explicit primary evidence for any cleared dataset, rejecting nominal license strings without evidence, and blocking NoDerivatives (`ND`) datasets.
- [tests/test_dataset_licensing.py](file:///c:/Users/hii/Downloads/ARGUMAP/tests/test_dataset_licensing.py): Tests the gatekeeper logic against mock manifests and verifies that all currently active pilot datasets are properly blocked.

---

## 6. Action Plan to Unblock Machine Learning Training

To clear ARGUMAP for supervised model training in Phase 3 while strictly preserving scientific honesty:

1. **UK Hansard Remediation:**
   * Ingest an authentic, verbatim debate excerpt from `hansard.parliament.uk` (e.g. 2023 or 2024 AI debates) with exact speech-turn timestamps and speaker IDs.
   * Provide the official Hansard URL and confirm compliance with OPL v3.0 attribution requirements.
2. **Kennedy-Nixon Remediation:**
   * Ingest the authentic transcript from the UCSB American Presidency Project or GPO facsimile.
   * Document the copyright status under the 1909 Copyright Act (confirming lack of copyright notice on broadcast or failure to renew after 28 years).
3. **US 2016 Remediation:**
   * Replace the proprietary CPD excerpt with the CC0-licensed 2020 Presidential Debate transcripts from **`m-arg`** (Mancini et al. 2022), or ingest a public domain historical debate.
