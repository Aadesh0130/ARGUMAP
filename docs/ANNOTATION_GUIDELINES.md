# ARGUMAP — Argument Annotation Guidelines

* **Document Version:** 1.1.0
* **Target Audience:** Human Annotators, Computational Linguists, Adjudicators
* **Scope:** Annotation of debate transcripts for the 6 frozen component labels and 4 frozen relation labels.
* **Calibrated Revision:** Updated with tie-breaking rules and case studies from the Phase 1 Pilot Annotation Ambiguity Log (`data/annotations/ambiguity_log.json`).

---

## 1. Introduction & Annotation Philosophy

The objective of argument annotation in ARGUMAP is to reconstruct the explicit and implicit reasoning structure of spoken or written debates. 

### 1.1 Core Unit of Annotation
* The unit of annotation is the **Argument Proposition (Unit)**.
* An argument unit is typically a complete clause or sentence that expresses a discrete argumentative stance, factual ground, counter-position, or response.
* Annotators must not merge two independent points into one unit. If an utterance contains a claim and a reason joined by *because*, they should be split into two contiguous units:
  * *Unit 1:* `[AI should be used in education]` $\rightarrow$ `CLAIM`
  * *Unit 2:* `[because it enables personalized learning]` $\rightarrow$ `PREMISE`

---

## 2. Component Labels Annotation Protocol

Annotators must assign each segmented proposition to exactly one of the 6 frozen component labels.

### 2.1 Label: `CLAIM`

#### Definition
A central contentious assertion, policy proposition, normative statement, or primary thesis put forward by a speaker as an overarching truth or policy objective.

#### What Qualifies
* Primary thesis statements and policy resolutions.
* Major conclusions that require justification.
* Normative judgments about what *ought* or *must* be done.

#### What Does Not Qualify
* Subordinate explanations or supporting reasons (tag as `PREMISE`).
* Empirical facts, citations, or statistical data without direct normative assertion (tag as `EVIDENCE`).
* Objections targeted directly at an opponent's already stated claim (tag as `COUNTERARGUMENT`).

#### Concrete Examples
1. *"The government should ban single-use plastics immediately."*
2. *"Artificial intelligence will fundamentally improve patient triage in rural hospitals."*
3. *"Standardized testing fails to reflect actual student capability."*

#### Ambiguous Cases & Tie-Breaking Rules
* *Ambiguity: Claim vs. Premise.* In extended reasoning chains, a statement can act as a intermediate conclusion. 
  * *Rule:* If the statement serves as the speaker's main thesis in the debate round, annotate as `CLAIM`. If it is subordinate and specifically exists to justify another statement in the same turn, annotate as `PREMISE`.

---

### 2.2 Label: `PREMISE`

#### Definition
A reason, rationale, logical mechanism, or deductive foundation offered to substantiate, explain, or justify an associated claim.

#### What Qualifies
* Statements explaining the causal *mechanism* behind a claim.
* Logical explanations that answer the question: *"Why is the claim true?"*
* Deductive, ethical, or conceptual principles used to back an assertion.

#### What Does Not Qualify
* Factual, statistical, or empirical citations from external studies (tag as `EVIDENCE`).
* Standalone assertions made without any explanatory grounding (tag as `CLAIM`).
* Direct attacks against an opponent's point (tag as `COUNTERARGUMENT` or `REBUTTAL`).

#### Concrete Examples
1. *"...because excessive social media usage disrupts sleep cycles and adolescent attention spans."*
2. *"Renewable energy sources reduce long-term national dependency on volatile foreign fuel markets."*
3. *"Without teacher supervision, automated grading algorithms fail to recognize non-standard student reasoning."*

#### Ambiguous Cases & Tie-Breaking Rules
* *Ambiguity: Premise vs. Evidence.* 
  * *Rule:* If the statement provides conceptual or logical reasoning, label as `PREMISE`. If it cites specific verifiable data, historical incidents, research authors, or numerical figures, label as `EVIDENCE`.

---

### 2.3 Label: `EVIDENCE`

#### Definition
Empirical data, statistical figures, scientific findings, expert citations, survey outcomes, or concrete historical facts presented to substantiate a premise or claim.

#### What Qualifies
* Numerical percentages, survey statistics, and quantitative data.
* Mentions of published studies, recognized institutions, academic papers, or direct quotes.
* Specific historical precedents or verified case studies.

#### What Does Not Qualify
* Generalized, unsupported claims of fact (e.g., *"Everyone knows cars are bad"* $\rightarrow$ `PREMISE`).
* Theoretical or hypothetical thought experiments (tag as `PREMISE`).

#### Concrete Examples
1. *"According to a 2023 study by MIT, automated tutoring improved math proficiency by 18% over a single semester."*
2. *"In 2021, Germany closed its final three nuclear plants, resulting in a temporary 12% rise in coal combustion."*
3. *"The World Health Organization reported that over 300 million people worldwide suffer from clinical depression."*

#### Ambiguous Cases & Tie-Breaking Rules
* *Ambiguity: Anecdotal claims.* 
  * *Rule:* If an anecdote is personal and unverifiable (e.g., *"My cousin experienced this"*), label as `PREMISE`. If it refers to documented institutional records, label as `EVIDENCE`.

---

### 2.4 Label: `COUNTERARGUMENT`

#### Definition
An affirmative objection, opposing reasoning, or critical contention raised directly against a previous speaker's established claim or premise.

#### What Qualifies
* Points raised by an opposing speaker that introduce new harms, unintended consequences, or logical flaws in the opponent's case.
* Statements that challenge the root justification of the affirmative case.

#### What Does Not Qualify
* Defensive answers or counter-responses to objections (tag as `REBUTTAL`).
* Initial constructive claims made by the affirmative side (tag as `CLAIM`).

#### Concrete Examples
1. *"However, introducing a universal basic income creates strong disincentives for workforce participation."*
2. *"The affirmative overlooks that remote schooling significantly increases social isolation among younger children."*
3. *"Implementing this policy would place an unmanageable financial burden on municipal taxpayers."*

#### Ambiguous Cases & Tie-Breaking Rules
* *Ambiguity: Counterargument vs. Rebuttal.* 
  * *Rule:* A `COUNTERARGUMENT` originates an attack on a primary case. A `REBUTTAL` is a defense made *after* an attack, responding to or invalidating the counterargument.

---

### 2.5 Label: `REBUTTAL`

#### Definition
A defensive argument or counter-offensive reasoning designed to defend a previously attacked claim by neutralizing, minimizing, or turning an opponent's counterargument.

#### What Qualifies
* Arguments answering an opposing counterargument (e.g., demonstrating why the alleged harm is mitigated or outweighed).
* Pointing out flaws, contradictions, or factual inaccuracies in an opponent's attack.
* Restoring the validity of the speaker's original claim.

#### What Does Not Qualify
* The initial counterargument itself (tag as `COUNTERARGUMENT`).
* Fresh constructive claims introducing entirely new topics (tag as `CLAIM`).

#### Concrete Examples
1. *"While the negative claims basic income causes laziness, trial data from Canada showed employment rates remained completely stable."*
2. *"This risk can be substantially mitigated through strict regulatory oversight and random audits."*
3. *"Their critique of high costs ignores the long-term healthcare savings projected over the next decade."*

#### Ambiguous Cases & Tie-Breaking Rules
* *Ambiguity: Rebuttal vs. New Counterargument.* 
  * *Rule:* If the proposition explicitly repairs, defends, or mitigates an already debated point, it is a `REBUTTAL`. If it starts a fresh attack on an unrelated issue, label as `COUNTERARGUMENT`.

---

### 2.6 Label: `OTHER`

#### Definition
Discourse that does not advance, defend, or contest the logical arguments of the debate.

#### What Qualifies
* Greetings, salutations, procedural acknowledgments, and thank-yous.
* Rhetorical transitions, meta-commentary, and timekeeping notes.
* Interrupted fragments or incomprehensible speech.

#### What Does Not Qualify
* Metaphorical assertions that express an actual substantive point (tag as `CLAIM` or `PREMISE`).

#### Concrete Examples
1. *"Thank you, Madame Chair, and good afternoon to the audience and my esteemed opponents."*
2. *"Moving on to my third and final contention in today's debate."*
3. *"Can everyone hear me clearly?"*

---

## 3. Relation Labels Annotation Protocol

Annotators must evaluate directed pairs of argument units $(u_{\text{source}} \rightarrow u_{\text{target}})$ and assign one of the 4 frozen relation labels.

### 3.1 Label: `SUPPORTS`
* **Definition:** $u_{\text{source}}$ validates, justifies, provides grounds for, or strengthens $u_{\text{target}}$.
* **Direction:** $\text{Grounds/Premise} \rightarrow \text{Claim/Conclusion}$.
* **Examples:**
  * Source: *"adaptive tutoring provides individualized feedback"*
  * Target: *"AI improves educational outcomes"*
  * Relation: `SUPPORTS` ($u_{\text{source}} \rightarrow u_{\text{target}}$).

### 3.2 Label: `ATTACKS`
* **Definition:** $u_{\text{source}}$ directly undermines, contradicts, or attempts to falsify the logical validity or factual truth of $u_{\text{target}}$.
* **Direction:** $\text{Attacking Unit} \rightarrow \text{Target Unit}$.
* **Examples:**
  * Source: *"mandatory service infringes upon constitutional freedom"*
  * Target: *"all citizens should serve one year of national service"*
  * Relation: `ATTACKS` ($u_{\text{source}} \rightarrow u_{\text{target}}$).

### 3.3 Label: `RESPONDS_TO`
* **Definition:** $u_{\text{source}}$ directly engages with or clarifies $u_{\text{target}}$ in the dialectic without constituting a binary `ATTACKS` or `SUPPORTS` relation (e.g. a rebuttal reframing a counterargument, a question addressing a claim, or a contextual concession).
* **Direction:** $\text{Responding Unit} \rightarrow \text{Addressed Unit}$.
* **Examples:**
  * Source: *"While privacy is a concern, we have already established data minimization protocols"*
  * Target: *"facial recognition systems breach user privacy"*
  * Relation: `RESPONDS_TO` ($u_{\text{source}} \rightarrow u_{\text{target}}$).

### 3.4 Label: `NO_RELATION`
* **Definition:** There is no direct logical, evidential, or rhetorical interaction between $u_{\text{source}}$ and $u_{\text{target}}$.
* **Examples:**
  * Source: *"Electric vehicles lower greenhouse gas emissions"*
  * Target: *"Space exploration budgets should be expanded"*
  * Relation: `NO_RELATION`.

---

## 4. Annotation Quality & Inter-Annotator Agreement (IAA)

1. **Independent Annotation:** Annotators must tag blind batches independently without discussing decisions during the annotation phase.
2. **Evaluation Metric:** Agreement will be measured using **Fleiss' Kappa ($\kappa$)** or **Cohen's Kappa ($\kappa$)** for multi-class labels.
3. **Threshold for Acceptance:**
   * Component labels: Minimum target $\kappa \ge 0.70$ (substantial agreement).
   * Relation labels: Minimum target $\kappa \ge 0.65$ (reflecting the inherent difficulty of pairwise link prediction).
4. **Adjudication:** Disagreements will be reviewed and resolved by a designated lead adjudicator following the tie-breaking rules documented herein.

---

## 5. Calibrated Guidelines & Adjudication Rules (v1.1.0 Updates)

Following the empirical annotation pilot on authentic debates (UK Hansard AI Debate 2024, US 2016 Presidential Debate, Kennedy-Nixon 1960 Opening Exchange), dialectical edge cases were systematically analyzed and resolved in `data/annotations/ambiguity_log.json`. The following binding adjudication rules are codified in v1.1.0:

### 5.1 Rule 1: Subordinate Policy Consequences vs. Primary Claims (`CLAIM` vs `PREMISE`)
* **Context:** In constructive policy speeches, speakers often argue that a failure to act will produce negative consequences (e.g. *“If we fail to establish enforceable standards today, displaced workers will bear the concentrated cost...”*).
* **Adjudication Principle:** When an utterance states an intermediate consequence or causal development whose primary rhetorical function is to answer *“Why must the overarching policy motion be adopted?”*, it must be annotated as **`PREMISE`**, not `CLAIM`.
* **Autonomous Claims:** An assertion is annotated as `CLAIM` only if it functions as an independent normative proposal or conclusion that itself demands justification (e.g. *“We must also guarantee paid family leave...”*).
* **Reference Case:** `AMB_001`, `AMB_005`.

### 5.2 Rule 2: Historical Generalizations vs. Empirical Citations (`PREMISE` vs `EVIDENCE`)
* **Context:** Debaters frequently appeal to broad historical trends (e.g. *“History demonstrates that every major wave of technological innovation... has created substantially more employment...”*).
* **Adjudication Principle:** An argument unit is annotated as **`EVIDENCE`** *only* if it cites verifiable empirical findings, quantitative measurements, specific historical dates, named institutions, or documented studies. Broad historical generalizations, philosophical lessons, or unquantified analogies are inductive **`PREMISE`** units.
* **Descriptive Conditions:** Statements describing social conditions with embedded causal commentary (e.g. *“thousands of classrooms remain overcrowded because the federal government has abdicated its responsibility...”*) lack objective citations and must be classified as **`PREMISE`**.
* **Reference Case:** `AMB_003`, `AMB_009`.

### 5.3 Rule 3: Technical Explanations Embedded in Rebuttal Turns (`PREMISE` vs `REBUTTAL`)
* **Context:** In rebuttal speeches, speakers contest opponent arguments by elucidating structural or economic mechanisms (e.g. explaining that generative algorithms replace cognitive tasks simultaneously).
* **Adjudication Principle:** Even within an adversarial rebuttal turn, propositions that explain the underlying causal mechanics or definitions are annotated as **`PREMISE`** supporting the central refutation point. Only the explicit, overarching statement that negates or counter-theorizes the opponent’s position is annotated as **`REBUTTAL`**.
* **Reference Case:** `AMB_004`, `AMB_007`, `AMB_016`.

### 5.4 Rule 4: Rhetorical Framing & Diplomatic Concession vs. Substantive Units (`OTHER` vs Content Labels)
* **Context:** Speakers routinely use oratorical quotes (e.g. quoting Lincoln in 1860) or polite consensus-building remarks (e.g. *“The goals that Senator Kennedy has stated are goals all Americans can share...”*).
* **Adjudication Principle:** Oratorical framing, historical quotations serving purely as introductory hooks, and polite agreements without contestation are annotated as **`OTHER`**. However, direct meta-evaluative attacks against an opponent's reasoning (e.g. *“her central premise is fundamentally flawed”*) are substantive dialectical moves and must be tagged as **`COUNTERARGUMENT`**.
* **Reference Case:** `AMB_002`, `AMB_008`, `AMB_012`, `AMB_015`.

### 5.5 Rule 5: Direct Refutation vs. Dialectical Engagement (`ATTACKS` vs `RESPONDS_TO`)
* **Context:** Cross-turn interactions between competing candidates often alternate between direct falsification and alternative vision framing.
* **Adjudication Principle:**
  * **`ATTACKS`:** Assigned when $u_{\text{source}}$ directly attempts to falsify, invalidate, or contradict the logical validity or empirical truth of $u_{\text{target}}$ (e.g. Wollaston refuting Clark's 19th-century optimism, or Nixon challenging Kennedy's federal expansion premise).
  * **`RESPONDS_TO`:** Assigned when $u_{\text{source}}$ advances an alternative normative paradigm or responds dialectically to an opponent's proposal without directly disproving the premise arithmetic (e.g. Clinton offering middle-out economics in response to Trump's corporate tax cuts).
* **Reference Case:** `AMB_010`, `AMB_011`, `AMB_013`, `AMB_017`.

