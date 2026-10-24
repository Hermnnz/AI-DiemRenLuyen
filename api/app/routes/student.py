from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, Form, UploadFile, File, Header, status
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import (
    User,
    Campaign,
    Criterion,
    Case,
    Claim,
    EvidenceFile,
    SupplementRequest,
    Appeal,
    Notification,
    ClassMember,
)
from api.app.schemas import (
    StudentCurrentResponse,
    CampaignSchema,
    StudentCaseSummary,
    CriterionSchema,
    ClaimSchema,
    EvidenceFileSchema,
    SupplementRequestSchema,
    AppealSchema,
    UpdateClaimRequest,
    UpdateClaimResponse,
    SubmitCaseRequest,
    SubmitCaseResponse,
    AcceptCaseRequest,
    AcceptCaseResponse,
    CreateAppealsRequest,
    SubmitAppealsResponse,
    AppError,
    format_datetime,
    format_score,
)
from api.app.services.auth_service import require_roles, verify_csrf
from api.app.services.file_service import save_upload_file
from api.app.services.scoring_service import parse_score, validate_score_bounds, sum_scores
from api.app.services.workflow_service import submit_student_case
from api.app.services.audit_service import log_audit
from api.app.services.notification_service import send_notification

router = APIRouter(prefix="/student", tags=["Student"])


def _build_claim_schema(cl: Claim, crit: Criterion, is_published_or_above: bool) -> ClaimSchema:
    evidence_schemas = [
        EvidenceFileSchema(
            id=ev.id,
            original_name=ev.original_name,
            mime_type=ev.mime_type,
            size_bytes=ev.size_bytes,
            uploaded_at=format_datetime(ev.uploaded_at),
            is_current=ev.is_current,
        )
        for ev in cl.evidence_files
        if ev.is_current
    ]

    approved_score = format_score(cl.approved_score) if is_published_or_above else None
    bcs_reason = cl.bcs_reason if is_published_or_above else None

    return ClaimSchema(
        id=cl.id,
        criterion_id=cl.criterion_id,
        self_score=format_score(cl.self_score),
        student_note=cl.student_note,
        approved_score=approved_score,
        bcs_reason=bcs_reason,
        evidence=evidence_schemas,
    )


@router.get("/current", response_model=StudentCurrentResponse)
def get_student_current(
    auth_data: tuple[User, list[str]] = Depends(require_roles("STUDENT")),
    db: Session = Depends(get_db),
):
    student_user, class_ids = auth_data
    if not class_ids:
        raise AppError(
            status_code=404,
            code="CLASS_NOT_FOUND",
            message="Sinh viên chưa được phân bổ vào lớp học nào.",
        )

    # Find campaign for student's class
    campaign = (
        db.query(Campaign)
        .filter(Campaign.class_id.in_(class_ids))
        .order_by(Campaign.created_at.desc())
        .first()
    )
    if not campaign:
        raise AppError(
            status_code=404,
            code="CAMPAIGN_NOT_FOUND",
            message="Chưa có đợt đánh giá nào cho lớp của bạn.",
        )

    case = (
        db.query(Case)
        .filter(Case.campaign_id == campaign.id, Case.student_id == student_user.id)
        .first()
    )
    if not case:
        raise AppError(
            status_code=404,
            code="CASE_NOT_FOUND",
            message="Hồ sơ rèn luyện chưa được khởi tạo cho đợt này.",
        )

    criteria = (
        db.query(Criterion)
        .filter(Criterion.campaign_id == campaign.id)
        .order_by(Criterion.sort_order)
        .all()
    )

    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    claims_by_crit = {cl.criterion_id: cl for cl in claims}

    is_published_or_above = case.status in [
        "PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO", "RESOLVED", "FINALIZED"
    ]
    is_finalized = case.status == "FINALIZED"

    criteria_schemas = [
        CriterionSchema(
            id=c.id,
            campaign_id=c.campaign_id,
            code=c.code,
            title=c.title,
            description=c.description,
            max_score=format_score(c.max_score),
            requires_evidence=c.requires_evidence,
            sort_order=c.sort_order,
        )
        for c in criteria
    ]

    claim_schemas = []
    for crit in criteria:
        cl = claims_by_crit.get(crit.id)
        if cl:
            claim_schemas.append(_build_claim_schema(cl, crit, is_published_or_above))

    supplement_requests = (
        db.query(SupplementRequest)
        .filter(SupplementRequest.case_id == case.id)
        .order_by(SupplementRequest.requested_at.desc())
        .all()
    )
    supp_schemas = [
        SupplementRequestSchema(
            id=s.id,
            case_id=s.case_id,
            kind=s.kind,
            criterion_id=s.criterion_id,
            round_no=s.round_no,
            reason=s.reason,
            requested_by=s.requested_by,
            deadline_at=format_datetime(s.deadline_at),
            fulfilled_at=format_datetime(s.fulfilled_at),
        )
        for s in supplement_requests
    ]

    appeals = (
        db.query(Appeal)
        .filter(Appeal.case_id == case.id)
        .order_by(Appeal.submitted_at.desc())
        .all()
    )
    appeal_schemas = [
        AppealSchema(
            id=ap.id,
            case_id=ap.case_id,
            criterion_id=ap.criterion_id,
            student_reason=ap.student_reason,
            status=ap.status,
            resolution=ap.resolution,
            new_score=format_score(ap.new_score),
            bcs_reason=ap.bcs_reason,
            submitted_at=format_datetime(ap.submitted_at),
            resolved_at=format_datetime(ap.resolved_at),
        )
        for ap in appeals
    ]

    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == student_user.id, Notification.read_at.is_(None))
        .count()
    )

    campaign_schema = CampaignSchema(
        id=campaign.id,
        class_id=campaign.class_id,
        title=campaign.title,
        term=campaign.term,
        status=campaign.status,
        open_at=format_datetime(campaign.open_at),
        submission_deadline_at=format_datetime(campaign.submission_deadline_at),
        supplement_period_hours=campaign.supplement_period_hours,
        appeal_period_hours=campaign.appeal_period_hours,
        reminder_after_hours=campaign.reminder_after_hours,
        max_info_rounds=campaign.max_info_rounds,
        max_proof_rounds=campaign.max_proof_rounds,
        criteria=criteria_schemas,
    )

    case_summary = StudentCaseSummary(
        id=case.id,
        version=case.version,
        status=case.status,
        claimed_total=format_score(case.claimed_total),
        proposed_total=format_score(case.proposed_total) if is_published_or_above else None,
        final_total=format_score(case.final_total) if is_finalized else None,
        submitted_at=format_datetime(case.submitted_at),
        published_at=format_datetime(case.published_at),
        appeal_deadline_at=format_datetime(case.appeal_deadline_at),
        info_round=case.info_round,
        proof_round=case.proof_round,
    )

    return StudentCurrentResponse(
        campaign=campaign_schema,
        case=case_summary,
        criteria=criteria_schemas,
        claims=claim_schemas,
        supplement_requests=supp_schemas,
        appeals=appeal_schemas,
        unread_notifications_count=unread_count,
    )


@router.put("/cases/{caseId}/claims/{criterionId}", response_model=UpdateClaimResponse, dependencies=[Depends(verify_csrf)])
def update_claim(
    caseId: str,
    criterionId: str,
    payload: UpdateClaimRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("STUDENT")),
    db: Session = Depends(get_db),
):
    student_user, _ = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")
    if case.student_id != student_user.id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền chỉnh sửa hồ sơ này.")

    if case.version != payload.expected_version:
        raise AppError(status_code=409, code="CASE_CHANGED", message="Hồ sơ đã thay đổi, vui lòng tải lại.")

    if case.status not in ["DRAFT", "NEEDS_INFO", "NEEDS_PROOF"]:
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Không thể chỉnh sửa điểm khi hồ sơ ở trạng thái {case.status}."
        )

    crit = db.query(Criterion).filter(Criterion.id == criterionId, Criterion.campaign_id == case.campaign_id).first()
    if not crit:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy tiêu chí đánh giá.")

    parsed_score = parse_score(payload.self_score)
    validate_score_bounds(parsed_score, crit.max_score, field_name=crit.code)

    claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == crit.id).first()
    if not claim:
        claim = Claim(
            case_id=case.id,
            criterion_id=crit.id,
            self_score=parsed_score,
            student_note=payload.student_note,
        )
        db.add(claim)
    else:
        claim.self_score = parsed_score
        claim.student_note = payload.student_note

    # Update case claimed_total
    all_claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    scores = [cl.self_score for cl in all_claims if cl.id != (claim.id or "")]
    scores.append(parsed_score)
    case.claimed_total = sum_scores(scores)
    case.version += 1
    case.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(claim)
    db.refresh(case)

    is_published = case.status in ["PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO", "RESOLVED", "FINALIZED"]
    return UpdateClaimResponse(
        case_id=case.id,
        version=case.version,
        claim=_build_claim_schema(claim, crit, is_published),
    )


@router.post("/cases/{caseId}/evidence", response_model=EvidenceFileSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
async def upload_evidence(
    caseId: str,
    criterion_id: str = Form(...),
    file: UploadFile = File(...),
    auth_data: tuple[User, list[str]] = Depends(require_roles("STUDENT")),
    db: Session = Depends(get_db),
):
    student_user, _ = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")
    if case.student_id != student_user.id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền tải tệp lên hồ sơ này.")

    if case.status not in ["DRAFT", "NEEDS_INFO", "NEEDS_PROOF"]:
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Không thể tải minh chứng khi hồ sơ ở trạng thái {case.status}."
        )

    crit = db.query(Criterion).filter(Criterion.id == criterion_id, Criterion.campaign_id == case.campaign_id).first()
    if not crit:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy tiêu chí đánh giá.")

    claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == crit.id).first()
    if not claim:
        claim = Claim(case_id=case.id, criterion_id=crit.id)
        db.add(claim)
        db.flush()

    storage_key, orig_name, size_bytes, sha256_hash = await save_upload_file(file)

    ev = EvidenceFile(
        claim_id=claim.id,
        storage_key=storage_key,
        original_name=orig_name,
        mime_type=file.content_type,
        size_bytes=size_bytes,
        sha256=sha256_hash,
        uploaded_by=student_user.id,
        uploaded_at=datetime.now(timezone.utc),
        is_current=True,
    )
    db.add(ev)
    case.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ev)

    return EvidenceFileSchema(
        id=ev.id,
        original_name=ev.original_name,
        mime_type=ev.mime_type,
        size_bytes=ev.size_bytes,
        uploaded_at=format_datetime(ev.uploaded_at),
        is_current=ev.is_current,
    )


@router.post("/cases/{caseId}/submit", response_model=SubmitCaseResponse, dependencies=[Depends(verify_csrf)])
def submit_case(
    caseId: str,
    payload: SubmitCaseRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: tuple[User, list[str]] = Depends(require_roles("STUDENT")),
    db: Session = Depends(get_db),
):
    student_user, _ = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")

    now = datetime.now(timezone.utc)
    updated_case, missing_items = submit_student_case(
        db, case, student_user, payload.expected_version, now
    )
    db.commit()
    db.refresh(updated_case)

    return SubmitCaseResponse(
        case_id=updated_case.id,
        status=updated_case.status,
        version=updated_case.version,
        missing_items=missing_items,
    )


@router.post("/cases/{caseId}/accept", response_model=AcceptCaseResponse, dependencies=[Depends(verify_csrf)])
def accept_case(
    caseId: str,
    payload: AcceptCaseRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: tuple[User, list[str]] = Depends(require_roles("STUDENT")),
    db: Session = Depends(get_db),
):
    student_user, _ = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")
    if case.student_id != student_user.id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền chấp nhận hồ sơ này.")

    if case.version != payload.expected_version:
        raise AppError(status_code=409, code="CASE_CHANGED", message="Hồ sơ đã thay đổi, vui lòng tải lại.")

    if case.status != "PUBLISHED":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể chấp nhận điểm khi hồ sơ ở trạng thái PUBLISHED (hiện tại: {case.status})."
        )

    now = datetime.now(timezone.utc)
    dl = case.appeal_deadline_at.replace(tzinfo=timezone.utc) if case.appeal_deadline_at and case.appeal_deadline_at.tzinfo is None else case.appeal_deadline_at
    if dl and now > dl:
        raise AppError(status_code=422, code="DEADLINE_EXPIRED", message="Đã quá thời hạn phản hồi/khiếu nại.")

    # Mutual exclusion check: can't accept if already appealed
    existing_appeals = db.query(Appeal).filter(Appeal.case_id == case.id).count()
    if existing_appeals > 0:
        raise AppError(status_code=409, code="ALREADY_APPEALED", message="Bạn đã gửi khiếu nại, không thể đồng ý điểm.")

    case.status = "ACCEPTED"
    case.acceptance_source = "EXPLICIT"
    case.version += 1
    case.updated_at = now
    log_audit(
        db,
        campaign_id=case.campaign_id,
        case_id=case.id,
        action="CASE_ACCEPTED",
        actor_user_id=student_user.id,
        after_json={"status": "ACCEPTED", "source": "EXPLICIT"},
    )
    db.commit()
    db.refresh(case)

    return AcceptCaseResponse(
        case_id=case.id,
        status=case.status,
        version=case.version,
        acceptance_source="EXPLICIT",
    )


@router.post("/cases/{caseId}/appeals", response_model=SubmitAppealsResponse, dependencies=[Depends(verify_csrf)])
def create_appeals(
    caseId: str,
    payload: CreateAppealsRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: tuple[User, list[str]] = Depends(require_roles("STUDENT")),
    db: Session = Depends(get_db),
):
    student_user, _ = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")
    if case.student_id != student_user.id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền khiếu nại hồ sơ này.")

    if case.version != payload.expected_version:
        raise AppError(status_code=409, code="CASE_CHANGED", message="Hồ sơ đã thay đổi, vui lòng tải lại.")

    if case.status != "PUBLISHED":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể gửi khiếu nại khi hồ sơ ở trạng thái PUBLISHED (hiện tại: {case.status})."
        )

    now = datetime.now(timezone.utc)
    dl = case.appeal_deadline_at.replace(tzinfo=timezone.utc) if case.appeal_deadline_at and case.appeal_deadline_at.tzinfo is None else case.appeal_deadline_at
    if dl and now > dl:
        raise AppError(status_code=422, code="DEADLINE_EXPIRED", message="Đã quá thời hạn phản hồi/khiếu nại.")

    # Mutual exclusion check: can't appeal if already accepted
    if case.acceptance_source == "EXPLICIT":
        raise AppError(status_code=409, code="ALREADY_ACCEPTED", message="Bạn đã đồng ý với điểm dự kiến, không thể khiếu nại.")

    criteria_ids = {
        c.id
        for c in db.query(Criterion).filter(Criterion.campaign_id == case.campaign_id).all()
    }

    created_appeals = []
    for item in payload.items:
        if item.criterion_id not in criteria_ids:
            raise AppError(status_code=404, code="NOT_FOUND", message=f"Tiêu chí {item.criterion_id} không thuộc đợt đánh giá này.")
        
        existing = (
            db.query(Appeal)
            .filter(Appeal.case_id == case.id, Appeal.criterion_id == item.criterion_id)
            .first()
        )
        if existing:
            raise AppError(status_code=409, code="APPEAL_EXISTS", message=f"Đã có khiếu nại cho tiêu chí này.")

        appeal = Appeal(
            case_id=case.id,
            criterion_id=item.criterion_id,
            student_reason=item.reason,
            status="OPEN",
            submitted_at=now,
        )
        db.add(appeal)
        created_appeals.append(appeal)

    case.status = "APPEALED"
    case.version += 1
    case.updated_at = now

    log_audit(
        db,
        campaign_id=case.campaign_id,
        case_id=case.id,
        action="APPEAL_SUBMITTED",
        actor_user_id=student_user.id,
        after_json={"appeals_count": len(created_appeals)},
    )
    db.commit()

    appeal_schemas = [
        AppealSchema(
            id=ap.id,
            case_id=ap.case_id,
            criterion_id=ap.criterion_id,
            student_reason=ap.student_reason,
            status=ap.status,
            resolution=ap.resolution,
            new_score=format_score(ap.new_score),
            bcs_reason=ap.bcs_reason,
            submitted_at=format_datetime(ap.submitted_at),
            resolved_at=format_datetime(ap.resolved_at),
        )
        for ap in created_appeals
    ]

    return SubmitAppealsResponse(
        case_id=case.id,
        status=case.status,
        version=case.version,
        appeals=appeal_schemas,
    )
