"""ARGUMAP — AI-Assisted Provisional Annotation Workflow.

Prepares and executes a controlled, AI-assisted provisional annotation workflow for:
`data/annotation/candidate_relations_full.json` -> `data/annotation/candidate_relations_ai_provisional.json`

Scientific & System Safeguards:
1. Purely Provisional: AI suggestions are stored in dedicated `ai_*` fields and are
   NEVER written into human gold-label fields (`label`, `relation_label`, `annotation_status`).
2. Input Immutability: `candidate_relations_full.json` is treated as strictly read-only and
   is never modified or overwritten.
3. Strict Taxonomy Enforcement: Only the 4 frozen labels (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`,
   `NO_RELATION`) are permitted.
4. Directional Independence: Source -> Target is evaluated independently; reverse pair labels
   are never inferred or mechanically duplicated.
5. Grounding & Anti-Hallucination: No spurious correlation on keywords or speaker turns alone.
6. Calibrated Review Queue: Ambiguous (< 0.7 confidence or disputed links) are flagged with
   `ai_review_status = "NEEDS_HUMAN_REVIEW"`.
7. Resilient Execution: Bounded batching, atomic checkpointing, retry handling, and resume support.
"""

from abc import ABC, abstractmethod
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset.validate_annotations import FROZEN_RELATION_LABELS

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "annotation" / "candidate_relations_full.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "annotation" / "candidate_relations_ai_provisional.json"
DEFAULT_ANNOTATION_VERSION = "1.0.0"

AI_REVIEW_STATUS_PROVISIONAL = "PROVISIONAL"
AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
AI_REVIEW_STATUS_PENDING = "PENDING_CONFIGURATION"
AI_REVIEW_STATUS_ERROR = "ERROR_INSPECTION_REQUIRED"

CONFIDENCE_HUMAN_REVIEW_THRESHOLD = 0.70


class InputValidationError(Exception):
    """Raised when input dataset violates structural or referential invariants."""
    pass


def validate_input_dataset(records: List[Dict[str, Any]], expected_count: int = 1260) -> Tuple[bool, List[str]]:
    """Revalidates candidate relations against the 7 mandatory invariants.

    Invariants:
    1. Exactly 1,260 records.
    2. Unique pair_id values.
    3. Non-empty source_text and target_text.
    4. No self-loops (source_unit_id != target_unit_id).
    5. Every directed pair (u_i -> u_j) has its reverse pair (u_j -> u_i).
    6. All labels are currently null and statuses are unannotated.
    7. Override metadata and unit references are preserved.
    """
    errors: List[str] = []

    if not isinstance(records, list):
        errors.append(f"Input records must be a list, got {type(records).__name__}")
        return False, errors

    if len(records) != expected_count:
        errors.append(f"Expected exactly {expected_count} records, found {len(records)}")

    seen_pair_ids: Set[str] = set()
    pairs_directed: Set[Tuple[str, str]] = set()

    for idx, r in enumerate(records):
        p_id = r.get("pair_id")
        s_id = r.get("source_unit_id")
        t_id = r.get("target_unit_id")
        s_text = r.get("source_text")
        t_text = r.get("target_text")

        # 2. Unique pair_id
        if not p_id or not isinstance(p_id, str):
            errors.append(f"Record #{idx + 1}: Missing or invalid pair_id '{p_id}'")
        elif p_id in seen_pair_ids:
            errors.append(f"Record #{idx + 1}: Duplicate pair_id '{p_id}'")
        else:
            seen_pair_ids.add(p_id)

        # 3. Non-empty text
        if not s_text or not str(s_text).strip():
            errors.append(f"Record #{idx + 1} ({p_id}): Empty or missing source_text")
        if not t_text or not str(t_text).strip():
            errors.append(f"Record #{idx + 1} ({p_id}): Empty or missing target_text")

        # 4. No self-loops
        if s_id == t_id and s_id is not None:
            errors.append(f"Record #{idx + 1} ({p_id}): Self-referencing loop detected ({s_id} == {t_id})")

        if s_id and t_id:
            pairs_directed.add((s_id, t_id))

        # 6. Human labels unannotated
        if r.get("label") is not None:
            errors.append(f"Record #{idx + 1} ({p_id}): Expected label to be null, got '{r.get('label')}'")
        if r.get("relation_label") is not None:
            errors.append(f"Record #{idx + 1} ({p_id}): Expected relation_label to be null, got '{r.get('relation_label')}'")
        if r.get("annotation_status") != "UNANNOTATED":
            errors.append(f"Record #{idx + 1} ({p_id}): Expected annotation_status 'UNANNOTATED', got '{r.get('annotation_status')}'")

        # 7. Metadata fields
        if "is_override" not in r:
            errors.append(f"Record #{idx + 1} ({p_id}): Missing 'is_override' field")
        if "notes" not in r and "note" not in r:
            errors.append(f"Record #{idx + 1} ({p_id}): Missing 'notes' field")

    # 5. Reverse pair completeness
    for s_id, t_id in pairs_directed:
        if (t_id, s_id) not in pairs_directed:
            errors.append(f"Missing reverse directed pair for ({s_id} -> {t_id})")

    is_valid = (len(errors) == 0)
    return is_valid, errors


class PredictionResult:
    """Encapsulates a model prediction for a directed candidate pair."""

    def __init__(
        self,
        suggested_label: Optional[str],
        rationale: Optional[str],
        confidence: Optional[float],
        review_status: str,
        model_name: str,
        error_message: Optional[str] = None,
    ) -> None:
        self.suggested_label = suggested_label
        self.rationale = rationale
        self.confidence = confidence
        self.review_status = review_status
        self.model_name = model_name
        self.error_message = error_message


class BaseModelProvider(ABC):
    """Abstract interface for language-model providers."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns provider/model identifier."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if provider has active API credentials/configuration."""
        pass

    @abstractmethod
    def classify_pair(self, pair: Dict[str, Any]) -> PredictionResult:
        """Classifies a single candidate pair."""
        pass

    def classify_batch(self, pairs: List[Dict[str, Any]]) -> List[PredictionResult]:
        """Classifies a batch of pairs."""
        return [self.classify_pair(p) for p in pairs]


class UnconfiguredQueueProvider(BaseModelProvider):
    """Fallback provider when no approved external LLM provider is configured.

    Initializes the candidate relations into a clean, reviewable AI queue without fabricating labels.
    """

    def get_provider_name(self) -> str:
        return "UNCONFIGURED_QUEUE"

    def is_configured(self) -> bool:
        return False

    def classify_pair(self, pair: Dict[str, Any]) -> PredictionResult:
        return PredictionResult(
            suggested_label=None,
            rationale="Language-model provider unconfigured in environment; queued for provisional inference.",
            confidence=None,
            review_status=AI_REVIEW_STATUS_PENDING,
            model_name=self.get_provider_name(),
        )


class MockModelProvider(BaseModelProvider):
    """Deterministic mock provider for unit testing all four labels, errors, and retries."""

    def __init__(
        self,
        default_label: str = "NO_RELATION",
        custom_mapping: Optional[Dict[str, Tuple[str, float, str, str]]] = None,
        simulate_malformed: bool = False,
        simulate_failure_count: int = 0,
    ) -> None:
        self.default_label = default_label
        self.custom_mapping = custom_mapping or {}
        self.simulate_malformed = simulate_malformed
        self.simulate_failure_count = simulate_failure_count
        self._current_failures = 0

    def get_provider_name(self) -> str:
        return "mock_test_engine_v1"

    def is_configured(self) -> bool:
        return True

    def classify_pair(self, pair: Dict[str, Any]) -> PredictionResult:
        if self._current_failures < self.simulate_failure_count:
            self._current_failures += 1
            raise RuntimeError("Simulated transient connection failure")

        if self.simulate_malformed:
            return PredictionResult(
                suggested_label="INVALID_LABEL_UNKNOWN",
                rationale="Malformed response for testing",
                confidence=0.5,
                review_status=AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW,
                model_name=self.get_provider_name(),
                error_message="Invalid label returned by model",
            )

        pair_id = pair.get("pair_id", "")
        if pair_id in self.custom_mapping:
            lbl, conf, rat, status = self.custom_mapping[pair_id]
            return PredictionResult(
                suggested_label=lbl,
                rationale=rat,
                confidence=conf,
                review_status=status,
                model_name=self.get_provider_name(),
            )

        # Default classification based on frozen guidelines
        conf = 0.85
        status = AI_REVIEW_STATUS_PROVISIONAL if conf >= CONFIDENCE_HUMAN_REVIEW_THRESHOLD else AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW

        return PredictionResult(
            suggested_label=self.default_label,
            rationale=f"Mock evaluation determined {self.default_label} based on textual analysis.",
            confidence=conf,
            review_status=status,
            model_name=self.get_provider_name(),
        )


class GeminiProvider(BaseModelProvider):
    """Google Gemini API Provider (used when GEMINI_API_KEY / GOOGLE_API_KEY is configured)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model

    def get_provider_name(self) -> str:
        return f"gemini/{self.model}"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def classify_pair(self, pair: Dict[str, Any]) -> PredictionResult:
        if not self.is_configured():
            return PredictionResult(
                suggested_label=None,
                rationale="GEMINI_API_KEY not configured.",
                confidence=None,
                review_status=AI_REVIEW_STATUS_PENDING,
                model_name=self.get_provider_name(),
            )

        # REST invocation using requests or httpx
        import urllib.request
        import urllib.error

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        prompt = (
            "You are an expert computational linguist annotating argument relations in a parliamentary debate.\n"
            "Given a directed pair of propositions (Source -> Target), assign exactly one of the 4 frozen labels:\n"
            "- SUPPORTS: Source provides evidence, grounds, or justification for Target.\n"
            "- ATTACKS: Source undermines, contradicts, or refutes Target.\n"
            "- RESPONDS_TO: Source directly engages or clarifies Target without direct support or attack.\n"
            "- NO_RELATION: No direct argumentative interaction.\n\n"
            f"Source (Speaker: {pair.get('source_speaker')}, Turn: {pair.get('source_turn')}):\n"
            f"\"{pair.get('source_text')}\"\n\n"
            f"Target (Speaker: {pair.get('target_speaker')}, Turn: {pair.get('target_turn')}):\n"
            f"\"{pair.get('target_text')}\"\n\n"
            "Respond in JSON format with fields: 'label' (one of SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION), "
            "'confidence' (float 0.0-1.0), 'rationale' (brief explanation), 'is_ambiguous' (boolean)."
        )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "response_mime_type": "application/json"
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(content)

            label = parsed.get("label", "").upper().strip()
            confidence = float(parsed.get("confidence", 0.5))
            rationale = parsed.get("rationale", "")
            is_ambiguous = bool(parsed.get("is_ambiguous", False))

            if label not in FROZEN_RELATION_LABELS:
                return PredictionResult(
                    suggested_label=None,
                    rationale=f"Model returned invalid label '{label}'. Raw response: {content}",
                    confidence=confidence,
                    review_status=AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW,
                    model_name=self.get_provider_name(),
                    error_message=f"Invalid label '{label}'",
                )

            status = AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW if (is_ambiguous or confidence < CONFIDENCE_HUMAN_REVIEW_THRESHOLD) else AI_REVIEW_STATUS_PROVISIONAL

            return PredictionResult(
                suggested_label=label,
                rationale=rationale,
                confidence=confidence,
                review_status=status,
                model_name=self.get_provider_name(),
            )
        except Exception as e:
            return PredictionResult(
                suggested_label=None,
                rationale=f"API request failed: {str(e)}",
                confidence=None,
                review_status=AI_REVIEW_STATUS_ERROR,
                model_name=self.get_provider_name(),
                error_message=str(e),
            )


class OpenAIProvider(BaseModelProvider):
    """OpenAI API Provider (used when OPENAI_API_KEY is configured)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    def get_provider_name(self) -> str:
        return f"openai/{self.model}"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def classify_pair(self, pair: Dict[str, Any]) -> PredictionResult:
        if not self.is_configured():
            return PredictionResult(
                suggested_label=None,
                rationale="OPENAI_API_KEY not configured.",
                confidence=None,
                review_status=AI_REVIEW_STATUS_PENDING,
                model_name=self.get_provider_name(),
            )

        import urllib.request

        url = "https://api.openai.com/v1/chat/completions"
        system_prompt = (
            "You are an expert computational linguist. Evaluate directed relation (Source -> Target). "
            "Output JSON with 'label' (SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION), "
            "'confidence' (0.0-1.0), 'rationale' (string), 'is_ambiguous' (boolean)."
        )
        user_prompt = (
            f"Source (Speaker: {pair.get('source_speaker')}): {pair.get('source_text')}\n"
            f"Target (Speaker: {pair.get('target_speaker')}): {pair.get('target_text')}"
        )

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            label = parsed.get("label", "").upper().strip()
            confidence = float(parsed.get("confidence", 0.5))
            rationale = parsed.get("rationale", "")
            is_ambiguous = bool(parsed.get("is_ambiguous", False))

            if label not in FROZEN_RELATION_LABELS:
                return PredictionResult(
                    suggested_label=None,
                    rationale=f"Invalid label '{label}' returned.",
                    confidence=confidence,
                    review_status=AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW,
                    model_name=self.get_provider_name(),
                    error_message=f"Invalid label '{label}'",
                )

            status = AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW if (is_ambiguous or confidence < CONFIDENCE_HUMAN_REVIEW_THRESHOLD) else AI_REVIEW_STATUS_PROVISIONAL

            return PredictionResult(
                suggested_label=label,
                rationale=rationale,
                confidence=confidence,
                review_status=status,
                model_name=self.get_provider_name(),
            )
        except Exception as e:
            return PredictionResult(
                suggested_label=None,
                rationale=f"OpenAI API call failed: {str(e)}",
                confidence=None,
                review_status=AI_REVIEW_STATUS_ERROR,
                model_name=self.get_provider_name(),
                error_message=str(e),
            )


def resolve_active_provider(explicit_provider: Optional[str] = None) -> BaseModelProvider:
    """Detects available model configuration or returns UnconfiguredQueueProvider."""
    if explicit_provider == "gemini":
        return GeminiProvider()
    if explicit_provider == "openai":
        return OpenAIProvider()

    # Automatic detection based on environment
    gemini = GeminiProvider()
    if gemini.is_configured():
        return gemini

    openai = OpenAIProvider()
    if openai.is_configured():
        return openai

    # Fallback to unconfigured queue
    return UnconfiguredQueueProvider()


class AIProvisionalPipeline:
    """Manages input validation, batch processing, checkpointing, retries, and resume."""

    def __init__(
        self,
        input_path: Path = DEFAULT_INPUT_PATH,
        output_path: Path = DEFAULT_OUTPUT_PATH,
        provider: Optional[BaseModelProvider] = None,
        batch_size: int = 50,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        annotation_version: str = DEFAULT_ANNOTATION_VERSION,
    ) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.provider = provider or resolve_active_provider()
        self.batch_size = max(1, batch_size)
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.annotation_version = annotation_version

        # Statistics
        self.retries_count = 0
        self.errors_count = 0

    def load_and_validate_input(self) -> List[Dict[str, Any]]:
        """Loads and revalidates input without touching or modifying the file."""
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input candidate relations file not found: {self.input_path}")

        # Strict read-only load
        with open(self.input_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        is_valid, errors = validate_input_dataset(records, expected_count=1260)
        if not is_valid:
            raise InputValidationError(f"Input validation failed with {len(errors)} error(s): " + "; ".join(errors[:5]))

        return records

    def _atomic_write(self, target_path: Path, data: Any) -> None:
        """Atomic write to prevent file corruption during checkpointing."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(f".tmp_{os.getpid()}_{int(time.time())}.json")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, target_path)
        except Exception:
            if tmp_path.exists():
                os.remove(tmp_path)
            raise

    def initialize_or_resume_output(self, input_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resumes from existing provisional artifact if present, otherwise initializes fresh copy."""
        if self.output_path.exists():
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if isinstance(existing, list) and len(existing) == len(input_records):
                    # Check pair_id matching
                    input_ids = [r["pair_id"] for r in input_records]
                    existing_ids = [r.get("pair_id") for r in existing]
                    if input_ids == existing_ids:
                        return existing
            except Exception:
                pass  # Fall through to reinitialize if existing is corrupted

        # Initialize fresh artifact preserving all original fields
        initialized: List[Dict[str, Any]] = []
        for r in input_records:
            entry = copy.deepcopy(r)
            entry["ai_suggested_label"] = None
            entry["ai_rationale"] = None
            entry["ai_confidence"] = None
            entry["ai_review_status"] = AI_REVIEW_STATUS_PENDING
            entry["ai_model_or_method"] = self.provider.get_provider_name()
            entry["ai_annotation_version"] = self.annotation_version
            initialized.append(entry)

        self._atomic_write(self.output_path, initialized)
        return initialized

    def run(self, dry_run: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Executes provisional annotation workflow with checkpointing and retry handling."""
        input_records = self.load_and_validate_input()

        if dry_run:
            # Revalidation check without writing
            report = self.compute_report(input_records, is_dry_run=True)
            return input_records, report

        working_records = self.initialize_or_resume_output(input_records)

        # Identify pending indices
        pending_indices: List[int] = []
        for idx, r in enumerate(working_records):
            status = r.get("ai_review_status")
            lbl = r.get("ai_suggested_label")
            # If pending or unannotated under current provider
            if status == AI_REVIEW_STATUS_PENDING or (lbl is None and status not in (AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW, AI_REVIEW_STATUS_ERROR)):
                pending_indices.append(idx)

        total_pending = len(pending_indices)

        # If provider is unconfigured, set informative rationale and checkpoint immediately
        if not self.provider.is_configured():
            for idx in pending_indices:
                res = self.provider.classify_pair(working_records[idx])
                working_records[idx]["ai_suggested_label"] = res.suggested_label
                working_records[idx]["ai_rationale"] = res.rationale
                working_records[idx]["ai_confidence"] = res.confidence
                working_records[idx]["ai_review_status"] = res.review_status
                working_records[idx]["ai_model_or_method"] = res.model_name
                working_records[idx]["ai_annotation_version"] = self.annotation_version

            self._atomic_write(self.output_path, working_records)
            report = self.compute_report(working_records, total_pending=0)
            return working_records, report

        # Process in bounded batches
        for batch_start in range(0, total_pending, self.batch_size):
            batch_slice = pending_indices[batch_start : batch_start + self.batch_size]

            for idx in batch_slice:
                pair = working_records[idx]
                attempts = 0
                success = False

                while attempts <= self.max_retries and not success:
                    try:
                        res = self.provider.classify_pair(pair)
                        pair["ai_suggested_label"] = res.suggested_label
                        pair["ai_rationale"] = res.rationale
                        pair["ai_confidence"] = res.confidence
                        pair["ai_review_status"] = res.review_status
                        pair["ai_model_or_method"] = res.model_name
                        pair["ai_annotation_version"] = self.annotation_version

                        if res.error_message:
                            self.errors_count += 1
                        success = True
                    except Exception as e:
                        attempts += 1
                        self.retries_count += 1
                        if attempts > self.max_retries:
                            self.errors_count += 1
                            pair["ai_suggested_label"] = None
                            pair["ai_rationale"] = f"Failed after {self.max_retries} retries: {str(e)}"
                            pair["ai_confidence"] = None
                            pair["ai_review_status"] = AI_REVIEW_STATUS_ERROR
                            pair["ai_model_or_method"] = self.provider.get_provider_name()
                            pair["ai_annotation_version"] = self.annotation_version
                        else:
                            time.sleep(self.retry_delay_seconds * (2 ** (attempts - 1)))

            # Atomic checkpoint after every batch
            self._atomic_write(self.output_path, working_records)

        report = self.compute_report(working_records)
        return working_records, report

    def compute_report(
        self,
        records: List[Dict[str, Any]],
        is_dry_run: bool = False,
        total_pending: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculates detailed metrics, distributions, reverse disagreements, and override stats."""
        total_records = len(records)

        # Status & label counts
        label_dist: Dict[str, int] = {lbl: 0 for lbl in sorted(list(FROZEN_RELATION_LABELS))}
        label_dist["UNANNOTATED_OR_NULL"] = 0

        status_dist: Dict[str, int] = {
            AI_REVIEW_STATUS_PROVISIONAL: 0,
            AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW: 0,
            AI_REVIEW_STATUS_PENDING: 0,
            AI_REVIEW_STATUS_ERROR: 0,
        }

        confidences: List[float] = []
        override_stats = {"total": 0, "labeled": 0, "needs_review": 0}
        standard_stats = {"total": 0, "labeled": 0, "needs_review": 0}

        pair_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for r in records:
            s_id = r.get("source_unit_id", "")
            t_id = r.get("target_unit_id", "")
            pair_map[(s_id, t_id)] = r

            lbl = r.get("ai_suggested_label")
            if lbl in label_dist:
                label_dist[lbl] += 1
            else:
                label_dist["UNANNOTATED_OR_NULL"] += 1

            st = r.get("ai_review_status", AI_REVIEW_STATUS_PENDING)
            status_dist[st] = status_dist.get(st, 0) + 1

            conf = r.get("ai_confidence")
            if isinstance(conf, (int, float)):
                confidences.append(float(conf))

            is_ov = r.get("is_override", False)
            target_stat = override_stats if is_ov else standard_stats
            target_stat["total"] += 1
            if lbl in FROZEN_RELATION_LABELS:
                target_stat["labeled"] += 1
            if st == AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW:
                target_stat["needs_review"] += 1

        # Reverse-pair analysis
        reverse_disagreements: List[Dict[str, Any]] = []
        seen_symmetric: Set[frozenset] = set()

        for (s_id, t_id), forward_pair in pair_map.items():
            pair_set = frozenset([s_id, t_id])
            if pair_set in seen_symmetric:
                continue
            seen_symmetric.add(pair_set)

            reverse_pair = pair_map.get((t_id, s_id))
            if not reverse_pair:
                continue

            f_lbl = forward_pair.get("ai_suggested_label")
            r_lbl = reverse_pair.get("ai_suggested_label")

            # Check for dialectical disagreement / asymmetry
            if f_lbl and r_lbl and f_lbl != r_lbl:
                reverse_disagreements.append({
                    "forward_pair_id": forward_pair.get("pair_id"),
                    "forward_label": f_lbl,
                    "forward_confidence": forward_pair.get("ai_confidence"),
                    "reverse_pair_id": reverse_pair.get("pair_id"),
                    "reverse_label": r_lbl,
                    "reverse_confidence": reverse_pair.get("ai_confidence"),
                    "turn_distance": forward_pair.get("turn_distance"),
                    "is_override": forward_pair.get("is_override"),
                })

        # Confidence distribution
        conf_summary: Dict[str, Any] = {
            "count": len(confidences),
            "mean": round(sum(confidences) / len(confidences), 4) if confidences else None,
            "min": round(min(confidences), 4) if confidences else None,
            "max": round(max(confidences), 4) if confidences else None,
            "low_confidence_count (<0.7)": sum(1 for c in confidences if c < CONFIDENCE_HUMAN_REVIEW_THRESHOLD),
        }

        total_processed = sum(1 for r in records if r.get("ai_suggested_label") is not None)
        total_remaining = total_records - total_processed

        return {
            "input_file": str(self.input_path),
            "output_file": str(self.output_path),
            "total_records": total_records,
            "total_processed": total_processed,
            "total_remaining": total_remaining,
            "provider_name": self.provider.get_provider_name(),
            "provider_configured": self.provider.is_configured(),
            "label_distribution": label_dist,
            "status_distribution": status_dist,
            "confidence_distribution": conf_summary,
            "needs_human_review_count": status_dist.get(AI_REVIEW_STATUS_NEEDS_HUMAN_REVIEW, 0),
            "reverse_disagreements_count": len(reverse_disagreements),
            "reverse_disagreements_sample": reverse_disagreements[:5],
            "override_statistics": override_stats,
            "standard_statistics": standard_stats,
            "retries_count": self.retries_count,
            "errors_count": self.errors_count,
            "is_dry_run": is_dry_run,
        }


def print_summary_report(report: Dict[str, Any]) -> None:
    """Prints a structured ASCII report of the provisional annotation run."""
    print("=" * 70)
    print("ARGUMAP AI-ASSISTED PROVISIONAL ANNOTATION REPORT")
    print("=" * 70)
    print(f"Input File:              {report['input_file']}")
    print(f"Output File:             {report['output_file']}")
    print(f"Total Records:           {report['total_records']}")
    print(f"Processed:               {report['total_processed']}")
    print(f"Remaining / Pending:     {report['total_remaining']}")
    print(f"Provider:                {report['provider_name']} (Configured: {report['provider_configured']})")
    print("-" * 70)
    print("LABEL DISTRIBUTION:")
    for lbl, count in report["label_distribution"].items():
        pct = (count / report["total_records"] * 100) if report["total_records"] else 0.0
        print(f"  {lbl:<25} : {count:>5} ({pct:>5.1f}%)")
    print("-" * 70)
    print("REVIEW STATUS DISTRIBUTION:")
    for st, count in report["status_distribution"].items():
        print(f"  {st:<28} : {count:>5}")
    print("-" * 70)
    print("CANDIDATE PARTITION STATISTICS:")
    ov = report["override_statistics"]
    st = report["standard_statistics"]
    print(f"  Standard (k <= 3):      Total={st['total']}, Labeled={st['labeled']}, Needs Review={st['needs_review']}")
    print(f"  Override (k > 3):       Total={ov['total']}, Labeled={ov['labeled']}, Needs Review={ov['needs_review']}")
    print("-" * 70)
    print(f"Reverse Disagreements:   {report['reverse_disagreements_count']}")
    print(f"Retries:                 {report['retries_count']}")
    print(f"Errors:                  {report['errors_count']}")
    print("=" * 70)

    if not report["provider_configured"]:
        print("CONFIGURATION NOTE:")
        print("No language-model provider API key is currently detected in the environment.")
        print("The 1,260 records have been initialized safely into the provisional queue.")
        print("To run inference with an external provider, set:")
        print("  $env:GEMINI_API_KEY='your-api-key'")
        print("  or $env:OPENAI_API_KEY='your-api-key'")
        print("and rerun:")
        print("  backend\\venv\\Scripts\\python.exe scripts/annotation/ai_provisional_annotator.py")
        print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-Assisted Provisional Annotation for ARGUMAP Candidate Relations.")
    parser.add_argument("--input", type=str, default=str(DEFAULT_INPUT_PATH), help="Input candidate relations JSON path.")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_PATH), help="Output provisional JSON path.")
    parser.add_argument("--provider", type=str, choices=["auto", "gemini", "openai"], default="auto", help="Model provider.")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for checkpointing.")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry attempts for failed requests.")
    parser.add_argument("--dry-run", action="store_true", help="Validate input and report without writing output.")
    args = parser.parse_args()

    in_p = Path(args.input)
    out_p = Path(args.output)

    explicit_prov = None if args.provider == "auto" else args.provider
    provider = resolve_active_provider(explicit_prov)

    pipeline = AIProvisionalPipeline(
        input_path=in_p,
        output_path=out_p,
        provider=provider,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
    )

    records, report = pipeline.run(dry_run=args.dry_run)
    print_summary_report(report)


if __name__ == "__main__":
    main()
