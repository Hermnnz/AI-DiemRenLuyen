from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


Role = Literal["STUDENT", "BCS", "GVCN", "ADMIN"]
CampaignStatus = Literal["DRAFT", "SCHEDULED", "OPEN", "REVIEW", "PUBLISHED", "FINALIZED"]
CaseStatus = Literal[
    "DRAFT", "SUBMITTED", "NEEDS_INFO", "BCS_REVIEW", "NEEDS_PROOF",
    "PROPOSED", "PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO",
    "RESOLVED", "FINALIZED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"
]
SupplementKind = Literal["INFO", "PROOF"]
MeetingKind = Literal["BCS", "CLASS"]
AppealStatus = Literal["OPEN", "RESOLVED"]
AppealResolution = Literal["KEEP", "ADJUST"]


# User & Auth
class UserSchema(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    class_ids: List[str] = Field(default_factory=list)


class AuthResponse(BaseModel):
    user: UserSchema
    csrf_token: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LogoutResponse(BaseModel):
    message: str = "Đăng xuất thành công"


# Criterion
class CriterionSchema(BaseModel):
    id: str
    campaign_id: str
    code: str
    section_code: Optional[str] = None
    section_title: Optional[str] = None
    section_max_score: Optional[str] = None
    title: str
    description: Optional[str] = None
    max_score: str
    requires_evidence: bool
    evidence_notes: Optional[str] = None
    allowed_input_roles: Optional[List[str]] = None
    rule_config: Optional[Dict[str, Any]] = None
    sort_order: int


class CreateCriterionInput(BaseModel):
    code: str
    section_code: Optional[str] = None
    section_title: Optional[str] = None
    section_max_score: Optional[str] = None
    title: str
    description: Optional[str] = None
    max_score: str
    requires_evidence: bool = False
    evidence_notes: Optional[str] = None
    allowed_input_roles: Optional[List[str]] = None
    rule_config: Optional[Dict[str, Any]] = None
    sort_order: int = 1


# Evidence File
class EvidenceFileSchema(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    is_current: bool = True


class BcsEvidenceDecisionSchema(BaseModel):
    evidence_file_id: str
    decision: str
    reason: str
    reviewed_by: str
    reviewed_at: str


class FinalHandoffSchema(BaseModel):
    status: Literal["NOT_SENT", "SENT", "RECEIVED"]
    snapshot_sha256: Optional[str] = None
    sent_by: Optional[str] = None
    sent_at: Optional[str] = None
    received_by: Optional[str] = None
    received_at: Optional[str] = None


class SetEvidenceDecisionRequest(BaseModel):
    decision: Literal["ACCEPT", "REQUEST_SUPPLEMENT", "REJECT_ITEM", "HOLD"]
    reason: str
    expected_version: int


class SetEvidenceDecisionResponse(BaseModel):
    case_id: str
    version: int
    status: str
    evidence_decision: BcsEvidenceDecisionSchema


# Claim
class ClaimSchema(BaseModel):
    id: str
    criterion_id: str
    self_score: Optional[str] = None
    student_note: Optional[str] = None
    academic_gpa: Optional[str] = None
    approved_score: Optional[str] = None
    bcs_reason: Optional[str] = None
    evidence: List[EvidenceFileSchema] = Field(default_factory=list)


class UpdateClaimRequest(BaseModel):
    self_score: Optional[str] = None
    student_note: Optional[str] = None
    expected_version: int


class UpdateClaimResponse(BaseModel):
    case_id: str
    version: int
    claim: ClaimSchema


class ReviewClaimRequest(BaseModel):
    approved_score: str
    reason: Optional[str] = None
    expected_version: int


class ReviewClaimResponse(BaseModel):
    case_id: str
    version: int
    claim: ClaimSchema


# Supplement Request
class SupplementRequestSchema(BaseModel):
    id: str
    case_id: str
    kind: str
    criterion_id: Optional[str] = None
    round_no: int
    reason: str
    requested_by: Optional[str] = None
    deadline_at: str
    fulfilled_at: Optional[str] = None


class CreateSupplementRequest(BaseModel):
    kind: str  # INFO, PROOF
    criterion_id: Optional[str] = None
    reason: str
    expected_version: int


# Appeal
class AppealSchema(BaseModel):
    id: str
    case_id: str
    criterion_id: str
    student_reason: str
    status: str  # OPEN, RESOLVED
    resolution: Optional[str] = None  # KEEP, ADJUST
    new_score: Optional[str] = None
    bcs_reason: Optional[str] = None
    submitted_at: str
    resolved_at: Optional[str] = None


class AppealItem(BaseModel):
    criterion_id: str
    reason: str


class CreateAppealsRequest(BaseModel):
    expected_version: int
    items: List[AppealItem] = Field(..., min_length=1)


class AppealDetailItem(BaseModel):
    id: str
    case_id: str
    student_code: str
    student_name: str
    criterion_code: str
    criterion_title: str
    self_score: str
    proposed_score: str
    student_reason: str
    status: str
    resolution: Optional[str] = None
    new_score: Optional[str] = None
    bcs_reason: Optional[str] = None
    evidence: List[EvidenceFileSchema] = Field(default_factory=list)


class ResolveAppealRequest(BaseModel):
    resolution: str  # KEEP, ADJUST
    new_score: Optional[str] = None
    reason: str


# Meeting
class MeetingSchema(BaseModel):
    id: str
    campaign_id: str
    kind: str  # BCS, CLASS
    held_at: str
    note: Optional[str] = None


class CreateMeetingRequest(BaseModel):
    kind: str
    held_at: str
    note: Optional[str] = None


class ConfirmDraftReviewRequest(BaseModel):
    expected_fingerprint: str
    note: str


class DraftReviewStatus(BaseModel):
    fingerprint: str
    reviewed: bool
    reviewed_at: Optional[str] = None


# Campaign
class CampaignSchema(BaseModel):
    id: str
    class_id: str
    title: str
    term: str
    term_start_on: Optional[str] = None
    term_end_on: Optional[str] = None
    status: str
    template_code: Optional[str] = "LEGACY_DEMO"
    open_at: str
    submission_deadline_at: str
    supplement_period_hours: int
    appeal_period_hours: int
    reminder_after_hours: int
    max_info_rounds: int
    max_proof_rounds: int
    criteria: Optional[List[CriterionSchema]] = None


class CreateCampaignRequest(BaseModel):
    class_id: str
    title: str
    term: str
    term_start_on: Optional[str] = None
    term_end_on: Optional[str] = None
    template_code: Optional[str] = "49K14_1_V1"
    open_at: str
    submission_deadline_at: str
    supplement_period_hours: int = 48
    appeal_period_hours: int = 72
    reminder_after_hours: int = 48
    max_info_rounds: int = 2
    max_proof_rounds: int = 2
    criteria: List[CreateCriterionInput] = Field(default_factory=list)


# Evaluation Template
class TemplateCriterionSchema(BaseModel):
    id: str
    template_id: str
    code: str
    section_code: str
    section_title: str
    section_max_score: str
    title: str
    description: Optional[str] = None
    max_score: str
    requires_evidence: bool
    evidence_notes: Optional[str] = None
    allowed_input_roles: Optional[List[str]] = None
    rule_config: Optional[Dict[str, Any]] = None
    sort_order: int


class EvaluationTemplateSchema(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    version: int
    total_max_score: str
    criteria_count: int = 0
    criteria: Optional[List[TemplateCriterionSchema]] = None


# Cadre Positions
class UserPositionSchema(BaseModel):
    id: str
    user_id: str
    term: str
    position_title: str
    organization: str
    is_confirmed: bool = True
    confirmed_by: Optional[str] = None
    created_at: str


class CreateUserPositionRequest(BaseModel):
    user_id: str
    term: str
    position_title: str
    organization: str
    is_confirmed: bool = True


# Academic Scores (4e)
class AcademicScoreItem(BaseModel):
    student_code: str
    gpa: float = Field(..., ge=0.0, le=4.0)


class ImportAcademicScoresRequest(BaseModel):
    items: List[AcademicScoreItem] = Field(..., min_length=1)


class ImportAcademicScoresResponse(BaseModel):
    updated_count: int
    details: List[Dict[str, Any]]


class OpenCampaignResponse(BaseModel):
    id: str
    status: str


class PublishCampaignRequest(BaseModel):
    expected_campaign_status: Optional[str] = None


class PublishCampaignResponse(BaseModel):
    campaign_id: str
    status: str
    published_at: str
    appeal_deadline_at: str


class FinalizeCampaignResponse(BaseModel):
    campaign_id: str
    status: str
    finalized_at: str


# Case
class StudentCaseSummary(BaseModel):
    id: str
    version: int
    status: str
    claimed_total: Optional[str] = None
    proposed_total: Optional[str] = None
    final_total: Optional[str] = None
    submitted_at: Optional[str] = None
    published_at: Optional[str] = None
    appeal_deadline_at: Optional[str] = None
    info_round: int = 0
    proof_round: int = 0


class StudentCurrentResponse(BaseModel):
    campaign: CampaignSchema
    case: StudentCaseSummary
    criteria: List[CriterionSchema]
    claims: List[ClaimSchema]
    supplement_requests: Optional[List[SupplementRequestSchema]] = None
    appeals: Optional[List[AppealSchema]] = None
    unread_notifications_count: int = 0


class SubmitCaseRequest(BaseModel):
    expected_version: int


class SubmitCaseResponse(BaseModel):
    case_id: str
    status: str
    version: int
    missing_items: List[str] = Field(default_factory=list)


class AcceptCaseRequest(BaseModel):
    expected_version: int


class AcceptCaseResponse(BaseModel):
    case_id: str
    status: str
    version: int
    acceptance_source: str = "EXPLICIT"


class SubmitAppealsResponse(BaseModel):
    case_id: str
    status: str
    version: int
    appeals: List[AppealSchema]


class CompleteReviewRequest(BaseModel):
    expected_version: int


class CompleteReviewResponse(BaseModel):
    case_id: str
    status: str
    proposed_total: str
    version: int


# BCS Views
class BcsCampaignOverview(BaseModel):
    campaign_id: str
    total_students: int
    not_submitted_count: int
    bcs_review_count: int
    needs_info_count: int
    needs_proof_count: int
    proposed_count: int
    published_count: int
    open_appeals_count: int
    finalized_count: int


class BcsCaseListItem(BaseModel):
    id: str
    student_code: str
    student_name: str
    status: str
    claimed_total: Optional[str] = None
    proposed_total: Optional[str] = None
    info_round: int = 0
    proof_round: int = 0
    updated_at: str


class BcsCaseListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[BcsCaseListItem]


class BcsCaseClaimCriterion(BaseModel):
    id: str
    campaign_id: str
    code: str
    title: str
    description: Optional[str] = None
    max_score: str
    requires_evidence: bool
    sort_order: int


class BcsCaseClaimItem(BaseModel):
    criterion: CriterionSchema
    self_score: Optional[str] = None
    student_note: Optional[str] = None
    approved_score: Optional[str] = None
    bcs_reason: Optional[str] = None
    evidence: List[EvidenceFileSchema] = Field(default_factory=list)


class BcsCaseHistoryItem(BaseModel):
    action: str
    at: str
    actor: str


class BcsCaseStudentInfo(BaseModel):
    id: str
    code: str
    full_name: str


class BcsCaseDeadlines(BaseModel):
    submission_at: Optional[str] = None
    supplement_at: Optional[str] = None


class BcsCaseRounds(BaseModel):
    info: int
    info_max: int
    proof: int
    proof_max: int


class BcsCaseDetail(BaseModel):
    id: str
    version: int
    status: str
    student: BcsCaseStudentInfo
    deadlines: BcsCaseDeadlines
    rounds: BcsCaseRounds
    claims: List[BcsCaseClaimItem]
    evidence_decisions: List[BcsEvidenceDecisionSchema] = Field(default_factory=list)
    evidence_review_required_ids: List[str] = Field(default_factory=list)
    draft_editable: bool = False
    supplement_requests: List[SupplementRequestSchema] = Field(default_factory=list)
    review_mode: str = "MANUAL"
    history: List[BcsCaseHistoryItem] = Field(default_factory=list)


class ScoreboardItem(BaseModel):
    case_id: Optional[str] = None
    student_code: str
    student_name: str
    status: str
    claimed_total: Optional[str] = None
    proposed_total: Optional[str] = None
    final_total: Optional[str] = None


class ScoreboardResponse(BaseModel):
    campaign_id: str
    can_publish: bool
    draft_review: Optional[DraftReviewStatus] = None
    meetings: List[MeetingSchema] = Field(default_factory=list)
    items: List[ScoreboardItem] = Field(default_factory=list)


# Notifications
class NotificationItem(BaseModel):
    id: str
    case_id: Optional[str] = None
    title: str
    body: str
    type: str
    read_at: Optional[str] = None
    created_at: str


class ReadNotificationResponse(BaseModel):
    id: str
    read_at: str


# AI Quality Evaluation & BCS Feedback Alignment
class BcsAiFeedbackItemSchema(BaseModel):
    id: str
    evidence_file_id: str
    file_sha256: str
    file_version_no: int
    case_id: str
    criterion_id: str
    criterion_code: str
    bcs_decision: str
    bcs_reason: str
    reviewer_name: Optional[str] = None
    reviewed_at: str
    ai_run_id: Optional[str] = None
    ai_model: Optional[str] = None
    ai_prompt_version: Optional[str] = None
    ai_verdict: Optional[str] = None
    ai_reason: Optional[str] = None
    matching_status: str
    discrepancy_status: str
    ground_truth_status: str
    ground_truth_label: Optional[str] = None
    verification_reason: Optional[str] = None
    verifier_name: Optional[str] = None
    verified_at: Optional[str] = None
    created_at: str
    updated_at: str


class BcsAiFeedbackDetailSchema(BcsAiFeedbackItemSchema):
    ai_assessment: Optional[Dict[str, Any]] = None
    file_original_name: Optional[str] = None
    file_mime_type: Optional[str] = None
    audit_history: List[Dict[str, Any]] = Field(default_factory=list)


class VerifyGroundTruthRequest(BaseModel):
    ground_truth_label: Literal["SUPPORTED", "FLAGGED", "UNKNOWN"]
    reason: str


class AiFeedbackMetricsResponse(BaseModel):
    total_count: int
    matched_count: int
    no_ai_count: int
    stale_ai_count: int
    agreed_count: int
    discrepancy_count: int
    non_final_count: int
    unverified_count: int
    verified_count: int
    verified_matched_count: int
    ai_accuracy: Optional[float] = None
    ai_precision_supported: Optional[float] = None
    ai_recall_supported: Optional[float] = None
    confusion_matrix: Optional[Dict[str, Dict[str, int]]] = None
    discrepancy_resolution: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class AiFeedbackListResponse(BaseModel):
    items: List[BcsAiFeedbackItemSchema] = Field(default_factory=list)
    total: int
    page: int
    limit: int
