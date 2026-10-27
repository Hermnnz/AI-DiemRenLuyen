from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AiStepResponse(BaseModel):
    kind: str
    status: str
    error_code: Optional[str] = None
    output: Optional[Dict[str, Any]] = None


class AiReviewResponse(BaseModel):
    id: str
    case_id: str
    case_version: int
    rubric_version: str
    status: str
    stale: bool
    attempt_count: int
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    steps: List[AiStepResponse] = Field(default_factory=list)


class AiLatestResponse(BaseModel):
    run: Optional[AiReviewResponse] = None


class AiTickResponse(BaseModel):
    processed: int
    needs_human: int
    stale: int
    failed: int


class RuleFindingResponse(BaseModel):
    code: str
    level: str
    message: str
    criterion_id: Optional[str] = None
    criterion_code: Optional[str] = None
    evidence_file_ids: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class RuleCheckResponse(BaseModel):
    case_id: str
    case_version: int
    rule_version: str
    term_window: Dict[str, Any]
    date_evidence_status: str
    findings: List[RuleFindingResponse] = Field(default_factory=list)
    counts: Dict[str, int]
    evaluated_at: str


class ScoreSuggestionItemResponse(BaseModel):
    criterion_id: str
    criterion_code: str
    clause_id: str
    self_score: Optional[str] = None
    draft_score: Optional[str] = None
    status: str
    reason: str
    calculation: Optional[str] = None
    evidence_file_ids: List[str] = Field(default_factory=list)
    finding_codes: List[str] = Field(default_factory=list)


class ScoreSuggestionResponse(BaseModel):
    case_id: str
    case_version: int
    rubric_version: str
    decision_version: str
    rule_version: str
    source_run_id: Optional[str] = None
    items: List[ScoreSuggestionItemResponse]
    section_checks: List[Dict[str, Any]]
    draft_total: Optional[str] = None
    ready_count: int
    review_required_count: int
    requires_bcs_approval: bool
    evaluated_at: str
