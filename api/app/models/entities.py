import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, BigInteger,
    Date, DateTime, ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from api.app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # STUDENT, BCS, GVCN, ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    class_memberships = relationship("ClassMember", back_populates="user", cascade="all, delete-orphan")


class Class(Base):
    __tablename__ = "classes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    members = relationship("ClassMember", back_populates="cls", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="cls")


class ClassMember(Base):
    __tablename__ = "class_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    member_role = Column(String(20), nullable=False)  # STUDENT, BCS, GVCN
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    cls = relationship("Class", back_populates="members")
    user = relationship("User", back_populates="class_memberships")

    __table_args__ = (
        UniqueConstraint("class_id", "user_id", "member_role", name="uq_class_user_role"),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    term = Column(String(50), nullable=False)
    term_start_on = Column(Date, nullable=True)
    term_end_on = Column(Date, nullable=True)
    status = Column(String(20), default="DRAFT", nullable=False)  # DRAFT, SCHEDULED, OPEN, REVIEW, PUBLISHED, FINALIZED
    open_at = Column(DateTime, nullable=False)
    submission_deadline_at = Column(DateTime, nullable=False)
    supplement_period_hours = Column(Integer, default=48, nullable=False)
    appeal_period_hours = Column(Integer, default=72, nullable=False)
    reminder_after_hours = Column(Integer, default=48, nullable=False)
    max_info_rounds = Column(Integer, default=2, nullable=False)
    max_proof_rounds = Column(Integer, default=2, nullable=False)
    opened_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cls = relationship("Class", back_populates="campaigns")
    template_code = Column(String(50), default="LEGACY_DEMO", nullable=True)
    criteria = relationship("Criterion", back_populates="campaign", cascade="all, delete-orphan", order_by="Criterion.sort_order")
    cases = relationship("Case", back_populates="campaign", cascade="all, delete-orphan")
    meetings = relationship("Meeting", back_populates="campaign", cascade="all, delete-orphan")
    final_handoff = relationship("FinalHandoff", back_populates="campaign", uselist=False, cascade="all, delete-orphan")


class Criterion(Base):
    __tablename__ = "criteria"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    section_code = Column(String(50), nullable=True)  # DIEU_4, DIEU_5, DIEU_6, DIEU_7, DIEU_8
    section_title = Column(String(255), nullable=True)
    section_max_score = Column(Numeric(5, 2), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_score = Column(Numeric(5, 2), nullable=False)
    requires_evidence = Column(Boolean, default=False, nullable=False)
    evidence_notes = Column(Text, nullable=True)
    allowed_input_roles = Column(JSON, nullable=True)  # e.g. ["STUDENT"], ["SYSTEM", "ADMIN"], ["STUDENT_CADRE"]
    rule_config = Column(JSON, nullable=True)
    sort_order = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="criteria")
    claims = relationship("Claim", back_populates="criterion")

    __table_args__ = (
        UniqueConstraint("campaign_id", "code", name="uq_campaign_criterion_code"),
    )


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), default="DRAFT", nullable=False)
    info_round = Column(Integer, default=0, nullable=False)
    proof_round = Column(Integer, default=0, nullable=False)
    claimed_total = Column(Numeric(5, 2), nullable=True)
    proposed_total = Column(Numeric(5, 2), nullable=True)
    final_total = Column(Numeric(5, 2), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    appeal_deadline_at = Column(DateTime, nullable=True)
    acceptance_source = Column(String(30), nullable=True)  # EXPLICIT, TIMEOUT
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="cases")
    student = relationship("User", foreign_keys=[student_id])
    claims = relationship("Claim", back_populates="case", cascade="all, delete-orphan")
    supplement_requests = relationship("SupplementRequest", back_populates="case", cascade="all, delete-orphan")
    appeals = relationship("Appeal", back_populates="case", cascade="all, delete-orphan")
    snapshots = relationship("ScoreSnapshot", back_populates="case", cascade="all, delete-orphan")
    ai_review_runs = relationship("AiReviewRun", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student_case"),
    )


class Claim(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    criterion_id = Column(String(36), ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False)
    self_score = Column(Numeric(5, 2), nullable=True)
    student_note = Column(Text, nullable=True)
    academic_gpa = Column(Numeric(4, 2), nullable=True)
    approved_score = Column(Numeric(5, 2), nullable=True)
    bcs_reason = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="claims")
    criterion = relationship("Criterion", back_populates="claims")
    evidence_files = relationship("EvidenceFile", back_populates="claim", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("case_id", "criterion_id", name="uq_case_criterion_claim"),
    )


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    storage_key = Column(String(255), unique=True, nullable=False)
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    version_no = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)

    claim = relationship("Claim", back_populates="evidence_files")
    bcs_decision = relationship("BcsEvidenceDecision", back_populates="evidence_file", uselist=False, cascade="all, delete-orphan")
    ai_feedback = relationship("BcsAiFeedback", back_populates="evidence_file", uselist=False, cascade="all, delete-orphan")


class BcsEvidenceDecision(Base):
    __tablename__ = "bcs_evidence_decisions"

    evidence_file_id = Column(String(36), ForeignKey("evidence_files.id", ondelete="CASCADE"), primary_key=True)
    decision = Column(String(24), nullable=False)
    reason = Column(Text, nullable=False)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_at = Column(DateTime, nullable=False)

    evidence_file = relationship("EvidenceFile", back_populates="bcs_decision")


class BcsAiFeedback(Base):
    __tablename__ = "bcs_ai_feedbacks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evidence_file_id = Column(String(36), ForeignKey("evidence_files.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    file_sha256 = Column(String(64), nullable=False)
    file_version_no = Column(Integer, default=1, nullable=False)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id = Column(String(36), ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False)
    criterion_code = Column(String(50), nullable=False)

    bcs_decision = Column(String(24), nullable=False)
    bcs_reason = Column(Text, nullable=False)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_at = Column(DateTime, nullable=False)

    ai_run_id = Column(String(36), ForeignKey("ai_review_runs.id", ondelete="SET NULL"), nullable=True)
    ai_model = Column(String(100), nullable=True)
    ai_prompt_version = Column(String(100), nullable=True)
    ai_verdict = Column(String(30), nullable=True)
    ai_reason = Column(Text, nullable=True)
    ai_assessment_json = Column(JSON, nullable=True)

    matching_status = Column(String(30), nullable=False)
    discrepancy_status = Column(String(30), nullable=False)

    ground_truth_status = Column(String(30), default="UNVERIFIED", nullable=False)
    ground_truth_label = Column(String(30), nullable=True)
    verification_reason = Column(Text, nullable=True)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    evidence_file = relationship("EvidenceFile", back_populates="ai_feedback")
    case = relationship("Case")
    criterion = relationship("Criterion")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    verifier = relationship("User", foreign_keys=[verified_by])
    ai_run = relationship("AiReviewRun")


class AiReviewRun(Base):
    __tablename__ = "ai_review_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    case_version = Column(Integer, nullable=False)
    rubric_version = Column(String(100), nullable=False)
    evidence_fingerprint = Column(String(64), nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    status = Column(String(20), default="QUEUED", nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    lease_until = Column(DateTime, nullable=True)
    provider = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    result_json = Column(JSON, nullable=True)
    error_code = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="ai_review_runs")
    steps = relationship("AiAgentStep", back_populates="run", cascade="all, delete-orphan", order_by="AiAgentStep.sort_order")


class AiAgentStep(Base):
    __tablename__ = "ai_agent_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("ai_review_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(30), nullable=False)  # AI_READ, AI_TRANSPARENCY
    sort_order = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)
    output_json = Column(JSON, nullable=True)
    error_code = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    run = relationship("AiReviewRun", back_populates="steps")

    __table_args__ = (UniqueConstraint("run_id", "kind", name="uq_ai_run_step_kind"),)


class SupplementRequest(Base):
    __tablename__ = "supplement_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), nullable=False)  # INFO, PROOF
    criterion_id = Column(String(36), ForeignKey("criteria.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=False)
    round_no = Column(Integer, nullable=False)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deadline_at = Column(DateTime, nullable=False)
    fulfilled_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="supplement_requests")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), nullable=False)  # BCS, CLASS
    held_at = Column(DateTime, nullable=False)
    note = Column(Text, nullable=True)
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="meetings")

    __table_args__ = (
        UniqueConstraint("campaign_id", "kind", name="uq_campaign_meeting_kind"),
    )


class Appeal(Base):
    __tablename__ = "appeals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    criterion_id = Column(String(36), ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False)
    student_reason = Column(Text, nullable=False)
    status = Column(String(20), default="OPEN", nullable=False)  # OPEN, RESOLVED
    resolution = Column(String(20), nullable=True)  # KEEP, ADJUST
    new_score = Column(Numeric(5, 2), nullable=True)
    bcs_reason = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    case = relationship("Case", back_populates="appeals")
    criterion = relationship("Criterion")

    __table_args__ = (
        UniqueConstraint("case_id", "criterion_id", name="uq_case_criterion_appeal"),
    )


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), nullable=False)  # PUBLISHED, FINAL
    per_criterion_json = Column(JSON, nullable=False)
    total = Column(Numeric(5, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    case = relationship("Case", back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint("case_id", "kind", name="uq_case_snapshot_kind"),
    )


class FinalHandoff(Base):
    __tablename__ = "final_handoffs"

    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    snapshot_sha256 = Column(String(64), nullable=False)
    sent_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime, nullable=False)
    received_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    received_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="final_handoff")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    dedup_key = Column(String(255), unique=True, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=True)
    action = Column(String(100), nullable=False)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    csrf_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EvaluationTemplate(Base):
    __tablename__ = "evaluation_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    total_max_score = Column(Numeric(5, 2), default=Decimal("100.00"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    criteria = relationship("TemplateCriterion", back_populates="template", cascade="all, delete-orphan", order_by="TemplateCriterion.sort_order")


class TemplateCriterion(Base):
    __tablename__ = "template_criteria"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    template_id = Column(String(36), ForeignKey("evaluation_templates.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    section_code = Column(String(50), nullable=False)
    section_title = Column(String(255), nullable=False)
    section_max_score = Column(Numeric(5, 2), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_score = Column(Numeric(5, 2), nullable=False)
    requires_evidence = Column(Boolean, default=False, nullable=False)
    evidence_notes = Column(Text, nullable=True)
    allowed_input_roles = Column(JSON, nullable=True)
    rule_config = Column(JSON, nullable=True)
    sort_order = Column(Integer, default=1, nullable=False)

    template = relationship("EvaluationTemplate", back_populates="criteria")

    __table_args__ = (
        UniqueConstraint("template_id", "code", name="uq_template_criterion_code"),
    )


class UserPosition(Base):
    __tablename__ = "user_positions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    term = Column(String(50), nullable=False)
    position_title = Column(String(100), nullable=False)
    organization = Column(String(255), nullable=False)
    is_confirmed = Column(Boolean, default=True, nullable=False)
    confirmed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
