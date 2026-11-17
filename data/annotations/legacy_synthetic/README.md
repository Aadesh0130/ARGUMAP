# Legacy Synthetic Pilot Annotations Archive

This directory archives the legacy pilot human and adjudicated annotations created for the synthetic/adapted demonstration text data/raw/other/uk_hansard_ai_debate_2024.txt.

## Provenance & Archive Notice
* **Original File:** data/raw/other/uk_hansard_ai_debate_2024.txt (SHA-256: 78be07a5ae03542d62988b2b0d97644aebf5a41d1d2f5cd37b7d5fd4cac7960e)
* **Status:** UNVERIFIED / BLOCKED for model training.
* **Audit Finding:** The debate attributed statements to Dr. Sarah Wollaston as a 2024 MP (she left Parliament in 2019) and does not exist in official Hansard records.
* **Superseded By:** Authentic verbatim transcript at data/raw/hansard/hansard_lords_ai_debate_2023.txt (House of Lords debate on Advanced Artificial Intelligence, 24 July 2023, licensed under Open Parliament Licence v3.0).

## Strict Integrity Safeguards
1. **No Span Reuse:** Character spans (char_start, char_end), unit strings, speaker IDs, and relations in these archived files are hardcoded to the legacy demonstration text and must NOT be mapped or overlaid onto the new authentic transcript.
2. **No Model Training:** These files are retained purely as historical demonstration and agreement audit records. They are blocked from supervised machine learning.
3. **Future Annotation Procedure:** The new authentic verbatim transcript (hansard_lords_ai_debate_2023.txt) must undergo an independent human annotation pass adhering to ANNOTATION_GUIDELINES.md v1.0.0.
