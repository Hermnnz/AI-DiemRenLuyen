"""Data contracts and schemas for AI pilot evaluation (Stage F1).

Implements strict allowlist schemas to ensure zero data leakage in reports.
"""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


TECHNICAL_VERSION_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?$")


def sanitize_technical_version(v: Optional[str]) -> str:
    """Sanitizes version string to only allow strict technical format like '1.0.0'.

    Replaces any non-conforming or arbitrary free-text string with safe fallback.
    """
    if not v or not isinstance(v, str):
        return "1.0.0"
    v_clean = v.strip()
    if TECHNICAL_VERSION_PATTERN.match(v_clean):
        return v_clean
    return "SAFE_VERSION"


MatchMode = Literal["contains", "exact", "regex"]
VerdictType = Literal["SUPPORTED", "FLAGGED", "UNKNOWN"]
DatasetSourceType = Literal["SYNTHETIC_SCRIPT_GENERATED", "INDEPENDENT_HUMAN_VERIFIED"]
PostProcessingReasonCode = Literal[
    "FLAGGED_DUE_TO_VISUAL_CONCERN",
    "UNKNOWN_DUE_TO_MISSING_CITATIONS",
    "UNKNOWN_DUE_TO_LACK_OF_BASIS",
]
ALLOWED_POST_PROCESSING_REASONS = {
    "FLAGGED_DUE_TO_VISUAL_CONCERN",
    "UNKNOWN_DUE_TO_MISSING_CITATIONS",
    "UNKNOWN_DUE_TO_LACK_OF_BASIS",
}
VerdictSourceType = Literal["MODEL_DIRECT", "SYSTEM_OVERRIDE"]
FactKind = Literal[
    "document_type",
    "activity_name",
    "event_date",
    "issuer",
    "recipient",
    "award_level",
    "reference_code",
    "other",
]


class ExpectedFact(BaseModel):
    kind: FactKind = Field(description="Loại dữ kiện mong đợi")
    value: str = Field(min_length=1, description="Giá trị dữ kiện mong đợi")
    match_mode: MatchMode = Field(default="contains", description="Chế độ so khớp: contains, exact, regex")
    page: Optional[int] = Field(default=None, ge=1, description="Trang xuất hiện (1-based, tùy chọn)")


class ExpectedRead(BaseModel):
    readable: bool = Field(default=True, description="Kỳ vọng tệp có đọc được hay không")
    unreadable_reason: Optional[str] = Field(default=None, description="Lý do không đọc được nếu readable=false")
    expected_facts: List[ExpectedFact] = Field(default_factory=list, description="Danh sách dữ kiện kỳ vọng trích xuất")


class ExpectedTransparency(BaseModel):
    verdict: VerdictType = Field(description="Nhãn chuẩn do con người đánh giá: SUPPORTED | FLAGGED | UNKNOWN")
    authenticity: Optional[Literal["AUTHENTIC", "SUSPICIOUS", "UNVERIFIED"]] = Field(
        default=None, description="Mức xác thực mong đợi"
    )
    requires_human_review: Optional[bool] = Field(
        default=True, description="Kỳ vọng cờ yêu cầu người rà soát"
    )
    expected_visual_concern: Optional[bool] = Field(
        default=None, description="Có dấu hiệu thị giác đáng ngờ hay không"
    )
    notes: Optional[str] = Field(default=None, description="Căn cứ/ghi chú của người gán nhãn")


class TestCase(BaseModel):
    __test__ = False
    id: str = Field(min_length=1, description="Mã ca đánh giá duy nhất (ví dụ: CASE_7B_001)")
    file: str = Field(min_length=1, description="Tên tệp hoặc đường dẫn tương đối trong thư mục dataset")
    criterion_code: str = Field(min_length=1, description="Mã tiêu chí theo quy chế (ví dụ: 7b, 4b_nckh)")
    student_name: str = Field(default="SV-ANON", description="Tên sinh viên ẩn danh")
    term: str = Field(default="HK1-2026-2027", description="Học kỳ đánh giá")
    self_score: str = Field(default="1.00", description="Điểm tự khai của sinh viên")
    student_note: Optional[str] = Field(default=None, description="Ghi chú tự khai của sinh viên")
    expected_read: ExpectedRead = Field(description="Kết quả đọc mong đợi từ AI_Read")
    expected_transparency: ExpectedTransparency = Field(
        description="Nhãn đối chiếu mong đợi từ AI_Transparency"
    )
    simulate_error: Optional[str] = Field(
        default=None,
        description="Mã lỗi giả lập phục vụ kiểm thử đơn vị (ví dụ: MODEL_TIMEOUT, 503)",
    )


class EvaluationDataset(BaseModel):
    version: str = Field(default="1.0.0", description="Phiên bản bộ dữ liệu nhãn")
    description: Optional[str] = Field(default=None, description="Mô tả bộ dữ liệu đánh giá")
    template_code: str = Field(default="49K14_1_V1", description="Mẫu quy tắc áp dụng")
    dataset_source: DatasetSourceType = Field(
        default="SYNTHETIC_SCRIPT_GENERATED",
        description="Nguồn gốc nhãn: SYNTHETIC_SCRIPT_GENERATED (sinh bằng script) hoặc INDEPENDENT_HUMAN_VERIFIED (người thẩm định độc lập)",
    )
    human_verified: bool = Field(
        default=False,
        description="Xác nhận đã qua kiểm định độc lập của con người hay chưa",
    )
    cases: List[TestCase] = Field(default_factory=list, description="Danh sách các ca đánh giá")

    @model_validator(mode="after")
    def validate_unique_case_ids(self):
        ids = [c.id for c in self.cases]
        if len(ids) != len(set(ids)):
            duplicates = [i for i in ids if ids.count(i) > 1]
            raise ValueError(f"Trùng lặp case id trong bộ dữ liệu: {set(duplicates)}")
        return self


# ---------------------------------------------------------------------------
# Output Schemas: Allowlisted Per-Case Report (Censored & Privacy Safe)
# ---------------------------------------------------------------------------


class AllowlistedCaseReport(BaseModel):
    """Báo cáo từng ca đã lọc qua danh sách trường cho phép (Allowlist).

    Tuyệt đối KHÔNG lưu trữ:
    - Tên tệp hoặc đường dẫn vật lý
    - Tên người hoặc ghi chú cá nhân
    - Giá trị trích xuất thực tế hoặc trích đoạn văn bản gốc
    - Lý do tự do hoặc ghi chú của người gán nhãn
    - Chi tiết exception/stacktrace hệ thống
    """
    case_id: str = Field(description="Mã ca ẩn danh")
    criterion_code: str = Field(description="Mã tiêu chí theo quy chế")
    status: Literal["COMPLETED", "FAILED", "SKIPPED"] = Field(description="Trạng thái thực thi")
    safe_error_code: Optional[str] = Field(default=None, description="Mã lỗi an toàn chuẩn hóa")

    # Labels & Verdicts
    verdict_expected: str
    verdict_actual: Optional[str] = None
    verdict_raw: Optional[Literal["SUPPORTED", "FLAGGED", "UNKNOWN"]] = None
    post_processing_reason: Optional[PostProcessingReasonCode] = None
    verdict_source: Optional[VerdictSourceType] = None
    verdict_match: bool
    is_false_flag: bool
    is_missed_flag: bool
    is_inconclusive: bool

    # Read step metrics
    readable_expected: bool
    readable_actual: Optional[bool] = None
    readable_match: bool
    expected_fact_count: int
    extracted_fact_count: int
    matched_fact_count: int
    read_precision: float
    read_recall: float

    # Transparency step metrics
    citation_count: int
    valid_citations: Optional[bool] = None
    visual_signals_count: int

    # Timing
    read_duration_seconds: float
    transparency_duration_seconds: float
    total_duration_seconds: float

    # Tokens (nếu API cung cấp)
    tokens: Optional[Dict[str, int]] = None


# ---------------------------------------------------------------------------
# Internal Schemas used during processing
# ---------------------------------------------------------------------------


class FactMatchDetail(BaseModel):
    expected_kind: str
    expected_value: str
    found: bool
    matched_value: Optional[str] = None
    matched_page: Optional[int] = None


class CaseReadEvaluation(BaseModel):
    readable_expected: bool
    readable_actual: Optional[bool] = None
    readable_match: bool = False
    unreadable_reason: Optional[str] = None
    expected_fact_count: int = 0
    extracted_fact_count: int = 0
    matched_fact_count: int = 0
    precision: float = 0.0
    recall: float = 0.0
    missing_facts: List[Dict[str, Any]] = Field(default_factory=list)
    fact_details: List[FactMatchDetail] = Field(default_factory=list)
    duration_seconds: float = 0.0
    usage_metadata: Optional[Dict[str, Any]] = None
    safe_error_code: Optional[str] = None


class CaseTransparencyEvaluation(BaseModel):
    verdict_expected: str
    verdict_actual: Optional[str] = None
    verdict_raw: Optional[Literal["SUPPORTED", "FLAGGED", "UNKNOWN"]] = None
    post_processing_reason: Optional[str] = None
    verdict_source: Optional[Literal["MODEL_DIRECT", "SYSTEM_OVERRIDE"]] = None
    verdict_match: bool = False
    is_false_flag: bool = False
    is_missed_flag: bool = False
    is_inconclusive: bool = False
    reason: Optional[str] = None
    citation_count: int = 0
    valid_citations: Optional[bool] = None
    safe_citation_error: Optional[str] = None
    visual_signals_count: int = 0
    authenticity: Optional[str] = None
    duration_seconds: float = 0.0
    usage_metadata: Optional[Dict[str, Any]] = None
    safe_error_code: Optional[str] = None


class CaseEvaluationResult(BaseModel):
    case_id: str
    file: str
    criterion_code: str
    status: Literal["COMPLETED", "FAILED", "SKIPPED"]
    safe_error_code: Optional[str] = None
    total_duration_seconds: float = 0.0
    read: Optional[CaseReadEvaluation] = None
    transparency: Optional[CaseTransparencyEvaluation] = None
    tokens: Optional[Dict[str, int]] = None
    expected_verdict: Optional[str] = None

    def to_allowlisted_report(self) -> AllowlistedCaseReport:
        """Convert internal detailed result into strict privacy-safe allowlisted report."""
        read_exp = self.read.readable_expected if self.read else False
        read_act = self.read.readable_actual if self.read else None
        read_match = self.read.readable_match if self.read else False
        exp_facts = self.read.expected_fact_count if self.read else 0
        ext_facts = self.read.extracted_fact_count if self.read else 0
        matched_facts = self.read.matched_fact_count if self.read else 0
        read_prec = self.read.precision if self.read else 0.0
        read_rec = self.read.recall if self.read else 0.0
        read_dur = self.read.duration_seconds if self.read else 0.0

        v_exp = self.transparency.verdict_expected if self.transparency else (self.expected_verdict or "UNKNOWN")
        v_act = self.transparency.verdict_actual if self.transparency else None
        v_raw = self.transparency.verdict_raw if (self.transparency and self.transparency.verdict_actual is not None) else None
        raw_pp = self.transparency.post_processing_reason if self.transparency else None
        post_proc: Optional[PostProcessingReasonCode] = raw_pp if raw_pp in ALLOWED_POST_PROCESSING_REASONS else None
        v_src = self.transparency.verdict_source if (self.transparency and self.transparency.verdict_actual is not None) else None
        v_match = self.transparency.verdict_match if self.transparency else False
        is_ff = self.transparency.is_false_flag if self.transparency else False
        is_mf = self.transparency.is_missed_flag if self.transparency else False
        is_inc = self.transparency.is_inconclusive if self.transparency else False
        cit_count = self.transparency.citation_count if self.transparency else 0
        valid_cit = (
            self.transparency.valid_citations
            if (self.transparency and self.transparency.verdict_actual is not None)
            else None
        )
        vis_count = self.transparency.visual_signals_count if self.transparency else 0
        trans_dur = self.transparency.duration_seconds if self.transparency else 0.0

        # Combine safe error codes
        safe_err = self.safe_error_code
        if not safe_err and self.read and self.read.safe_error_code:
            safe_err = self.read.safe_error_code
        if not safe_err and self.transparency and self.transparency.safe_error_code:
            safe_err = self.transparency.safe_error_code

        return AllowlistedCaseReport(
            case_id=self.case_id,
            criterion_code=self.criterion_code,
            status=self.status,
            safe_error_code=safe_err,
            verdict_expected=v_exp,
            verdict_actual=v_act,
            verdict_raw=v_raw,
            post_processing_reason=post_proc,
            verdict_source=v_src,
            verdict_match=v_match,
            is_false_flag=is_ff,
            is_missed_flag=is_mf,
            is_inconclusive=is_inc,
            readable_expected=read_exp,
            readable_actual=read_act,
            readable_match=read_match,
            expected_fact_count=exp_facts,
            extracted_fact_count=ext_facts,
            matched_fact_count=matched_facts,
            read_precision=read_prec,
            read_recall=read_rec,
            citation_count=cit_count,
            valid_citations=valid_cit,
            visual_signals_count=vis_count,
            read_duration_seconds=read_dur,
            transparency_duration_seconds=trans_dur,
            total_duration_seconds=self.total_duration_seconds,
            tokens=self.tokens,
        )


class ConfusionMatrix(BaseModel):
    matrix: Dict[str, Dict[str, int]] = Field(
        default_factory=lambda: {
            "SUPPORTED": {"SUPPORTED": 0, "FLAGGED": 0, "UNKNOWN": 0, "ERROR": 0},
            "FLAGGED": {"SUPPORTED": 0, "FLAGGED": 0, "UNKNOWN": 0, "ERROR": 0},
            "UNKNOWN": {"SUPPORTED": 0, "FLAGGED": 0, "UNKNOWN": 0, "ERROR": 0},
        }
    )


class AggregateMetrics(BaseModel):
    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    executed_cases: int = 0

    # Denominators for transparency quality metrics (actual AI conclusions)
    assessed_cases: int = 0
    human_supported_evaluated: int = 0
    human_flagged_evaluated: int = 0

    # Verdict metrics
    confusion_matrix: ConfusionMatrix = Field(default_factory=ConfusionMatrix)
    exact_match_accuracy: float = 0.0
    false_flag_count: int = 0
    false_flag_rate: float = 0.0
    missed_flag_count: int = 0
    missed_flag_rate: float = 0.0
    unknown_count: int = 0
    unknown_rate: float = 0.0

    # Model vs System breakdown
    model_flagged_count: int = 0
    system_flagged_count: int = 0
    system_unknown_count: int = 0

    # Denominators for OCR metrics
    read_evaluated_cases: int = 0
    read_valid_evaluated_cases: int = 0

    # OCR Read metrics
    read_readability_accuracy: float = 0.0
    read_avg_fact_precision: float = 0.0
    read_avg_fact_recall: float = 0.0
    total_missing_facts: int = 0

    # Citation quality
    invalid_citation_cases: int = 0
    avg_citations_per_case: float = 0.0

    # Latency (seconds)
    latency_read_avg: float = 0.0
    latency_transparency_avg: float = 0.0
    latency_total_avg: float = 0.0
    latency_total_min: float = 0.0
    latency_total_max: float = 0.0

    # Standardized API error counts
    api_errors: Dict[str, int] = Field(default_factory=dict)

    # Token totals (từ API chính thức, không ước tính tiền)
    total_prompt_tokens: Optional[int] = None
    total_candidate_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class EvaluationReport(BaseModel):
    timestamp: str
    mode: Literal["MOCK", "LIVE"]
    is_mock_simulation: bool
    disclaimer: str
    dataset_source: DatasetSourceType
    human_verified: bool
    model_read: str
    model_transparency: str
    dataset_version: str
    total_evaluated: int
    summary_metrics: AggregateMetrics
    case_reports: List[AllowlistedCaseReport]

    @field_validator("dataset_version", mode="before")
    @classmethod
    def sanitize_version(cls, v: Any) -> str:
        return sanitize_technical_version(str(v) if v is not None else "")
