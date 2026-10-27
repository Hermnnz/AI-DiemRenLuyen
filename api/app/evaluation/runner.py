"""Evaluation runner for AI Read and Transparency pilot (Stage F1).

Key security & audit guarantees:
1. Strict path traversal & symlink containment within resolved dataset directory.
2. File type and size inspection BEFORE reading into memory.
3. Strict rule template and criterion verification (NO generic fallbacks).
4. Mandatory positive limit on --live mode to prevent uncontrolled API costs.
5. Standardized safe error codes (zero raw exception or system path leakage).
"""

import asyncio
import hashlib
import mimetypes
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from api.app.config import settings
from api.app.evaluation.metrics import (
    compute_aggregate_metrics,
    evaluate_read_step,
    evaluate_transparency_step,
)
from api.app.evaluation.schemas import (
    AllowlistedCaseReport,
    CaseEvaluationResult,
    EvaluationDataset,
    EvaluationReport,
    TestCase,
    sanitize_technical_version,
)
from api.app.review.gemini_read import ALLOWED_MIME_TYPES, GeminiReadError, GeminiReadProvider
from api.app.review.gemini_transparency import GeminiTransparencyProvider
from api.app.services.template_service import CRITERIA_49K14_1_DEFINITIONS, TEMPLATE_49K14_1_CODE


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
APPROVED_TEMPLATES = {TEMPLATE_49K14_1_CODE, "49K14_1_V1"}


def get_criterion_context(criterion_code: str, template_code: str = "49K14_1_V1") -> Optional[Dict[str, Any]]:
    """Retrieve trusted criterion definition from template definitions.

    Rejects unapproved templates or unknown criteria. NO generic fallback.
    """
    if template_code not in APPROVED_TEMPLATES:
        return None

    for item in CRITERIA_49K14_1_DEFINITIONS:
        if item["code"] == criterion_code:
            return {
                "code": item["code"],
                "title": item["title"],
                "description": item.get("description") or "",
                "evidence_notes": item.get("evidence_notes") or "",
                "rule_config": item.get("rule_config") or {},
                "clause_id": f"{template_code}:{item['code']}",
            }
    return None


def detect_mime_type(file_path: Path) -> str:
    """Detect MIME type from file extension with explicit fallback."""
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    elif suffix == ".pdf":
        return "application/pdf"
    mime, _ = mimetypes.guess_type(str(file_path))
    return mime or "application/octet-stream"


class EvaluationRunner:
    """Executes evaluation dataset against Mock or Live Gemini pipeline."""

    def __init__(
        self,
        live: bool = False,
        api_key: Optional[str] = None,
        model_read: Optional[str] = None,
        model_transparency: Optional[str] = None,
        limit: Optional[int] = None,
        start_index: int = 1,
        client: Optional[httpx.AsyncClient] = None,
    ):
        if start_index < 1:
            raise ValueError("Vị trí --start-index phải là số nguyên dương (>= 1).")
        self.live = live
        self.limit = limit
        self.start_index = start_index
        if self.live and (self.limit is None or self.limit <= 0):
            raise ValueError("Chế độ --live bắt buộc phải cấu hình limit là số nguyên dương (> 0) để khống chế chi phí.")

        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_read = model_read or settings.GEMINI_MODEL
        self.model_transparency = model_transparency or settings.GEMINI_TRANSPARENCY_MODEL
        self.client = client

    async def run_case(
        self,
        case: TestCase,
        dataset_dir: Path,
        template_code: str = "49K14_1_V1",
        safe_case_id: Optional[str] = None,
    ) -> CaseEvaluationResult:
        assigned_id = safe_case_id or f"CASE_{case.criterion_code.upper()}"

        # 1. Template validation
        if template_code not in APPROVED_TEMPLATES:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="UNAPPROVED_TEMPLATE",
                total_duration_seconds=0.0,
            )

        # 2. Criterion validation (Strict: NO fallback)
        criterion_ctx = get_criterion_context(case.criterion_code, template_code)
        if criterion_ctx is None:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="UNAPPROVED_CRITERION",
                total_duration_seconds=0.0,
            )

        # 3. Path traversal & symlink containment
        resolved_dataset_dir = dataset_dir.resolve()
        raw_case_file = Path(case.file)
        if raw_case_file.is_absolute():
            candidate_path = raw_case_file.resolve()
        else:
            candidate_path = (resolved_dataset_dir / raw_case_file).resolve()

        try:
            is_contained = candidate_path.is_relative_to(resolved_dataset_dir)
        except AttributeError:
            is_contained = os.path.commonpath([str(resolved_dataset_dir), str(candidate_path)]) == str(resolved_dataset_dir)

        if not is_contained:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="PATH_TRAVERSAL_DETECTED",
                total_duration_seconds=0.0,
            )

        # Check symlink target containment
        if (dataset_dir / case.file).is_symlink():
            if not candidate_path.is_relative_to(resolved_dataset_dir):
                return CaseEvaluationResult(
                    case_id=assigned_id,
                    file="REDACTED",
                    criterion_code=case.criterion_code,
                    status="FAILED",
                    safe_error_code="PATH_TRAVERSAL_DETECTED",
                    total_duration_seconds=0.0,
                )

        # 4. File existence check
        if not candidate_path.is_file():
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="FILE_NOT_FOUND",
                total_duration_seconds=0.0,
            )

        # 5. File type check (BEFORE reading bytes)
        ext = candidate_path.suffix.lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="UNSUPPORTED_FILE_TYPE",
                total_duration_seconds=0.0,
            )

        mime_type = detect_mime_type(candidate_path)
        if mime_type not in ALLOWED_MIME_TYPES:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="UNSUPPORTED_FILE_TYPE",
                total_duration_seconds=0.0,
            )

        # 6. File size check (BEFORE reading bytes)
        try:
            file_size = candidate_path.stat().st_size
        except Exception:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="FILE_STAT_ERROR",
                total_duration_seconds=0.0,
            )

        if file_size == 0:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="FILE_EMPTY",
                total_duration_seconds=0.0,
            )

        if file_size > MAX_FILE_SIZE:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="FILE_TOO_LARGE",
                total_duration_seconds=0.0,
            )

        # 7. Safe read bytes
        try:
            data = candidate_path.read_bytes()
        except Exception:
            return CaseEvaluationResult(
                case_id=assigned_id,
                file="REDACTED",
                criterion_code=case.criterion_code,
                status="FAILED",
                safe_error_code="FILE_READ_ERROR",
                total_duration_seconds=0.0,
            )

        sha256 = hashlib.sha256(data).hexdigest()

        # -------------------------------------------------------------
        # Step 1: AI_Read (OCR fact extraction)
        # -------------------------------------------------------------
        read_start = time.monotonic()
        read_dict: Optional[Dict[str, Any]] = None
        read_safe_error: Optional[str] = None
        read_duration: float = 0.0

        if not self.live:
            # Mock mode
            await asyncio.sleep(0.01)
            read_duration = time.monotonic() - read_start

            if case.simulate_error in {"MODEL_TIMEOUT", "TIMEOUT"}:
                read_safe_error = "MODEL_TIMEOUT"
            elif case.simulate_error in {"503", "MODEL_TEMPORARILY_UNAVAILABLE"}:
                read_safe_error = "MODEL_TEMPORARILY_UNAVAILABLE"
            elif case.simulate_error in {"429", "MODEL_RATE_LIMITED", "RATE_LIMITED"}:
                read_safe_error = "MODEL_RATE_LIMITED"
            elif not case.expected_read.readable:
                read_dict = {
                    "evidence_file_id": assigned_id,
                    "sha256": sha256,
                    "readable": False,
                    "unreadable_reason": case.expected_read.unreadable_reason or "Tệp ảnh mờ/hỏng, không đọc được.",
                    "facts": [],
                }
            else:
                facts = [
                    {
                        "kind": f.kind,
                        "value": f.value,
                        "page": f.page or 1,
                        "source_excerpt": f.value,
                    }
                    for f in case.expected_read.expected_facts
                ]
                read_dict = {
                    "evidence_file_id": assigned_id,
                    "sha256": sha256,
                    "readable": True,
                    "unreadable_reason": "",
                    "facts": facts,
                }
        else:
            # Live mode
            read_provider = GeminiReadProvider(
                api_key=self.api_key,
                model=self.model_read,
                client=self.client,
            )
            try:
                read_dict = await read_provider.read(
                    evidence_file_id=assigned_id,
                    sha256=sha256,
                    mime_type=mime_type,
                    data=data,
                )
            except GeminiReadError as exc:
                read_safe_error = exc.code
            except httpx.TimeoutException:
                read_safe_error = "MODEL_TIMEOUT"
            except Exception:
                read_safe_error = "UNEXPECTED_READ_ERROR"
            read_duration = time.monotonic() - read_start

        read_eval = evaluate_read_step(
            expected=case.expected_read,
            actual=read_dict,
            duration=read_duration,
            safe_error_code=read_safe_error,
        )

        # -------------------------------------------------------------
        # Step 2: AI_Transparency (rule & evidence compliance assessment)
        # -------------------------------------------------------------
        trans_start = time.monotonic()
        trans_dict: Optional[Dict[str, Any]] = None
        trans_safe_error: Optional[str] = None
        trans_duration: float = 0.0

        if read_safe_error:
            trans_safe_error = "READ_STEP_FAILED"
            trans_duration = 0.0
        elif not read_dict or not read_dict.get("readable"):
            trans_dict = {
                "evidence_file_id": assigned_id,
                "sha256": sha256,
                "criterion_code": case.criterion_code,
                "verdict": "UNKNOWN",
                "raw_verdict": "UNKNOWN",
                "post_processing_reason": None,
                "reason": "Minh chứng không đọc được dữ kiện để đối chiếu quy chế.",
                "citations": [],
                "visual_signals": [],
                "authenticity": "UNVERIFIED",
                "limitations": ["Minh chứng bị hỏng hoặc quá mờ."],
            }
            trans_duration = time.monotonic() - trans_start
        else:
            if not self.live:
                # Mock mode
                await asyncio.sleep(0.01)
                trans_duration = time.monotonic() - trans_start

                if case.simulate_error in {"TRANSPARENCY_TIMEOUT", "ASSESS_TIMEOUT"}:
                    trans_safe_error = "MODEL_TIMEOUT"
                elif case.simulate_error in {"TRANSPARENCY_429", "TRANSPARENCY_RATE_LIMITED"}:
                    trans_safe_error = "MODEL_RATE_LIMITED"
                elif case.simulate_error == "SIMULATE_VISUAL_CONCERN_OVERRIDE":
                    facts = read_dict.get("facts", []) if read_dict else []
                    citations = [
                        {
                            "page": f.get("page", 1),
                            "source_excerpt": f.get("source_excerpt", f.get("value", "")),
                            "kind": f.get("kind", "other"),
                            "value": f.get("value", ""),
                        }
                        for f in facts
                    ] if facts else []
                    trans_dict = {
                        "evidence_file_id": assigned_id,
                        "sha256": sha256,
                        "criterion_code": case.criterion_code,
                        "verdict": "FLAGGED",
                        "raw_verdict": "SUPPORTED",
                        "post_processing_reason": "FLAGGED_DUE_TO_VISUAL_CONCERN",
                        "reason": "Mô phỏng hậu xử lý chuyển sang FLAGGED do visual concern.",
                        "citations": citations,
                        "visual_signals": [{"page": 1, "description": "Dấu hiệu nghi vấn", "concern": True}],
                        "authenticity": "SUSPICIOUS",
                        "limitations": ["Mô phỏng override."],
                    }
                elif case.simulate_error == "SIMULATE_NO_CITATIONS_OVERRIDE":
                    trans_dict = {
                        "evidence_file_id": assigned_id,
                        "sha256": sha256,
                        "criterion_code": case.criterion_code,
                        "verdict": "UNKNOWN",
                        "raw_verdict": "SUPPORTED",
                        "post_processing_reason": "UNKNOWN_DUE_TO_MISSING_CITATIONS",
                        "reason": "Mô phỏng hậu xử lý chuyển sang UNKNOWN do thiếu trích dẫn.",
                        "citations": [],
                        "visual_signals": [],
                        "authenticity": "UNVERIFIED",
                        "limitations": ["Mô phỏng override."],
                    }
                elif case.simulate_error == "SIMULATE_NO_BASIS_OVERRIDE":
                    trans_dict = {
                        "evidence_file_id": assigned_id,
                        "sha256": sha256,
                        "criterion_code": case.criterion_code,
                        "verdict": "UNKNOWN",
                        "raw_verdict": "FLAGGED",
                        "post_processing_reason": "UNKNOWN_DUE_TO_LACK_OF_BASIS",
                        "reason": "Mô phỏng hậu xử lý chuyển sang UNKNOWN do thiếu căn cứ.",
                        "citations": [],
                        "visual_signals": [],
                        "authenticity": "UNVERIFIED",
                        "limitations": ["Mô phỏng override."],
                    }
                elif case.simulate_error == "TRANSPARENCY_INVALID_CITATION":
                    trans_dict = {
                        "evidence_file_id": assigned_id,
                        "sha256": sha256,
                        "criterion_code": case.criterion_code,
                        "verdict": case.expected_transparency.verdict,
                        "raw_verdict": case.expected_transparency.verdict,
                        "post_processing_reason": None,
                        "reason": "Mô phỏng trích dẫn không có căn cứ.",
                        "citations": [{"page": 99, "kind": "recipient", "value": "INVALID_VALUE_NON_EXISTENT"}],
                        "visual_signals": [],
                        "authenticity": "UNVERIFIED",
                        "limitations": ["Trích dẫn bịa."],
                    }
                else:
                    exp_verdict = case.expected_transparency.verdict
                    citations = [
                        {
                            "page": f.get("page", 1),
                            "source_excerpt": f.get("source_excerpt", f.get("value", "")),
                            "kind": f.get("kind", "other"),
                            "value": f.get("value", ""),
                        }
                        for f in read_dict.get("facts", [])
                    ]
                    visual_signals = []
                    if case.expected_transparency.expected_visual_concern:
                        visual_signals.append({
                            "page": 1,
                            "description": "Dấu hiệu nghi vấn thị giác phát hiện trên tài liệu.",
                            "concern": True,
                        })

                    trans_dict = {
                        "evidence_file_id": assigned_id,
                        "sha256": sha256,
                        "criterion_code": case.criterion_code,
                        "verdict": exp_verdict,
                        "raw_verdict": exp_verdict,
                        "post_processing_reason": None,
                        "reason": "Mô phỏng thẩm định AI.",
                        "citations": citations if exp_verdict == "SUPPORTED" else [],
                        "visual_signals": visual_signals,
                        "authenticity": case.expected_transparency.authenticity or ("SUSPICIOUS" if visual_signals else "UNVERIFIED"),
                        "limitations": ["Đánh giá mô phỏng theo dữ liệu nhãn con người."],
                    }
            else:
                # Live mode
                trans_provider = GeminiTransparencyProvider(
                    api_key=self.api_key,
                    model=self.model_transparency,
                    client=self.client,
                )
                try:
                    trans_dict = await trans_provider.assess(
                        evidence_file_id=assigned_id,
                        sha256=sha256,
                        mime_type=mime_type,
                        data=data,
                        read_result=read_dict,
                        criterion=criterion_ctx,
                        student_name=case.student_name,
                        term=case.term,
                    )
                except GeminiReadError as exc:
                    trans_safe_error = exc.code
                except httpx.TimeoutException:
                    trans_safe_error = "MODEL_TIMEOUT"
                except Exception:
                    trans_safe_error = "UNEXPECTED_TRANSPARENCY_ERROR"
                trans_duration = time.monotonic() - trans_start

        trans_eval = evaluate_transparency_step(
            expected=case.expected_transparency,
            actual=trans_dict,
            read_facts=read_dict.get("facts", []) if read_dict else [],
            duration=trans_duration,
            safe_error_code=trans_safe_error,
        )

        # Token aggregation if available
        tokens_info = None
        prompt_tokens = 0
        candidate_tokens = 0
        total_tokens = 0
        found_tokens = False

        if read_eval.usage_metadata:
            found_tokens = True
            prompt_tokens += read_eval.usage_metadata.get("promptTokenCount", 0)
            candidate_tokens += read_eval.usage_metadata.get("candidatesTokenCount", 0)
            total_tokens += read_eval.usage_metadata.get("totalTokenCount", 0)

        if trans_eval.usage_metadata:
            found_tokens = True
            prompt_tokens += trans_eval.usage_metadata.get("promptTokenCount", 0)
            candidate_tokens += trans_eval.usage_metadata.get("candidatesTokenCount", 0)
            total_tokens += trans_eval.usage_metadata.get("totalTokenCount", 0)

        if found_tokens:
            tokens_info = {
                "prompt_tokens": prompt_tokens,
                "candidate_tokens": candidate_tokens,
                "total_tokens": total_tokens,
            }

        status = "COMPLETED"
        safe_error = None
        if read_safe_error or trans_safe_error:
            status = "FAILED"
            safe_error = read_safe_error or trans_safe_error

        return CaseEvaluationResult(
            case_id=assigned_id,
            file="REDACTED",  # Never keep file path in evaluation output
            criterion_code=case.criterion_code,
            status=status,
            safe_error_code=safe_error,
            total_duration_seconds=round(read_duration + trans_duration, 3),
            read=read_eval,
            transparency=trans_eval,
            tokens=tokens_info,
            expected_verdict=case.expected_transparency.verdict,
        )

    async def run_dataset(self, dataset: EvaluationDataset, dataset_dir: Path) -> EvaluationReport:
        # Enumerate with 1-based index to preserve original case position in dataset
        cases_indexed = list(enumerate(dataset.cases, start=1))

        # Filter starting from start_index (1-based)
        cases_to_run = [item for item in cases_indexed if item[0] >= self.start_index]

        if self.limit is not None and self.limit > 0:
            cases_to_run = cases_to_run[: self.limit]

        results: List[CaseEvaluationResult] = []
        stopped_due_to_rate_limit = False

        for orig_idx, case in cases_to_run:
            safe_id = f"CASE_{orig_idx:03d}"

            if stopped_due_to_rate_limit:
                # Short-circuit on 429: skip subsequent calls
                skipped_res = CaseEvaluationResult(
                    case_id=safe_id,
                    file="REDACTED",
                    criterion_code=case.criterion_code,
                    status="SKIPPED",
                    safe_error_code="SKIPPED_DUE_TO_RATE_LIMIT",
                    total_duration_seconds=0.0,
                    read=None,
                    transparency=None,
                    tokens=None,
                    expected_verdict=case.expected_transparency.verdict,
                )
                results.append(skipped_res)
                continue

            res = await self.run_case(
                case,
                dataset_dir,
                template_code=dataset.template_code,
                safe_case_id=safe_id,
            )
            results.append(res)

            # Circuit breaker: if current case encountered MODEL_RATE_LIMITED (HTTP 429), stop further calls
            if res.safe_error_code == "MODEL_RATE_LIMITED":
                stopped_due_to_rate_limit = True

        summary = compute_aggregate_metrics(results)
        allowlisted_reports: List[AllowlistedCaseReport] = [r.to_allowlisted_report() for r in results]

        disclaimer_text = (
            "CHẾ ĐỘ MOCK: Toàn bộ kết quả dưới đây chỉ để kiểm tra tính đúng đắn của công cụ, "
            "định dạng dữ liệu và luồng thực thi. ĐÂY KHÔNG PHẢI LÀ ĐỘ CHÍNH XÁC HAY CHẤT LƯỢNG THỰC TẾ "
            "CỦA MÔ HÌNH GEMINI. Tuyệt đối không dùng tỷ lệ 100% của MOCK để làm căn cứ đánh giá AI."
            if not self.live
            else "CHẾ ĐỘ LIVE: Kết quả thẩm định thực tế từ các lời gọi Google Gemini REST API."
        )

        return EvaluationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode="LIVE" if self.live else "MOCK",
            is_mock_simulation=not self.live,
            disclaimer=disclaimer_text,
            dataset_source=dataset.dataset_source,
            human_verified=dataset.human_verified,
            model_read=self.model_read,
            model_transparency=self.model_transparency,
            dataset_version=sanitize_technical_version(dataset.version),
            total_evaluated=len(allowlisted_reports),
            summary_metrics=summary,
            case_reports=allowlisted_reports,
        )
