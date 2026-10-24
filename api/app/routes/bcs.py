from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from api.app.database import get_db
from api.app.models.entities import (
    User,
    Campaign,
    Criterion,
    Case,
    Claim,
    EvidenceFile,
    SupplementRequest,
    Meeting,
    Appeal,
    AuditEvent,
    ClassMember,
)
from api.app.schemas import (
    BcsCampaignOverview,
    BcsCaseListItem,
    BcsCaseListResponse,
    BcsCaseDetail,
    BcsCaseStudentInfo,
    BcsCaseDeadlines,
    BcsCaseRounds,
    BcsCaseClaimItem,
    BcsCaseHistoryItem,
    CriterionSchema,
    EvidenceFileSchema,
    SupplementRequestSchema,
    CreateSupplementRequest,
    ReviewClaimRequest,
    ReviewClaimResponse,
    ClaimSchema,
    CompleteReviewRequest,
    CompleteReviewResponse,
    CreateMeetingRequest,
    MeetingSchema,
    PublishCampaignRequest,
    PublishCampaignResponse,
    ScoreboardResponse,
    ScoreboardItem,
    AppealDetailItem,
    ResolveAppealRequest,
    AppealSchema,
    FinalizeCampaignResponse,
    AppError,
    format_datetime,
    format_score,
)
from api.app.services.auth_service import require_roles, verify_csrf
from api.app.services.scoring_service import parse_score, validate_score_bounds, sum_scores
from api.app.services.workflow_service import complete_bcs_case_review, publish_campaign, finalize_campaign
from api.app.services.audit_service import log_audit
from api.app.services.notification_service import send_notification

router = APIRouter(prefix="/bcs", tags=["BCS"])


def _verify_bcs_class(user: User, class_ids: List[str], campaign_class_id: str):
    if campaign_class_id not in class_ids:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Bạn không có quyền quản lý đợt đánh giá của lớp này.",
        )


@router.get("/campaigns/{id}/overview", response_model=BcsCampaignOverview)
def get_campaign_overview(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    cases = db.query(Case).filter(Case.campaign_id == campaign.id).all()
    total_students = (
        db.query(ClassMember)
        .filter(ClassMember.class_id == campaign.class_id, ClassMember.member_role == "STUDENT")
        .count()
    )

    not_submitted = sum(1 for c in cases if c.status == "DRAFT")
    bcs_review = sum(1 for c in cases if c.status == "BCS_REVIEW")
    needs_info = sum(1 for c in cases if c.status == "NEEDS_INFO")
    needs_proof = sum(1 for c in cases if c.status == "NEEDS_PROOF")
    proposed = sum(1 for c in cases if c.status == "PROPOSED")
    published = sum(1 for c in cases if c.status in ["PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO", "RESOLVED"])
    finalized = sum(1 for c in cases if c.status in ["FINALIZED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"])

    case_ids = [c.id for c in cases]
    open_appeals = (
        db.query(Appeal)
        .filter(Appeal.case_id.in_(case_ids), Appeal.status == "OPEN")
        .count()
        if case_ids
        else 0
    )

    return BcsCampaignOverview(
        campaign_id=campaign.id,
        total_students=total_students,
        not_submitted_count=not_submitted,
        bcs_review_count=bcs_review,
        needs_info_count=needs_info,
        needs_proof_count=needs_proof,
        proposed_count=proposed,
        published_count=published,
        open_appeals_count=open_appeals,
        finalized_count=finalized,
    )


@router.get("/campaigns/{id}/cases", response_model=BcsCaseListResponse)
def get_campaign_cases(
    id: str,
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    query = (
        db.query(Case, User)
        .join(User, Case.student_id == User.id)
        .filter(Case.campaign_id == campaign.id)
    )

    if status:
        query = query.filter(Case.status == status)

    if q:
        search = f"%{q}%"
        query = query.filter(or_(User.username.ilike(search), User.full_name.ilike(search)))

    total = query.count()
    offset = (page - 1) * page_size
    records = query.order_by(User.username.asc()).offset(offset).limit(page_size).all()

    items = [
        BcsCaseListItem(
            id=c.id,
            student_code=u.username,
            student_name=u.full_name,
            status=c.status,
            claimed_total=format_score(c.claimed_total),
            proposed_total=format_score(c.proposed_total),
            info_round=c.info_round,
            proof_round=c.proof_round,
            updated_at=format_datetime(c.updated_at),
        )
        for c, u in records
    ]

    return BcsCaseListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/cases/{caseId}", response_model=BcsCaseDetail)
def get_bcs_case_detail(
    caseId: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")

    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    _verify_bcs_class(user, class_ids, campaign.class_id)

    student = db.query(User).filter(User.id == case.student_id).first()
    criteria = db.query(Criterion).filter(Criterion.campaign_id == campaign.id).order_by(Criterion.sort_order).all()
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    claims_dict = {cl.criterion_id: cl for cl in claims}

    claims_list = []
    for crit in criteria:
        cl = claims_dict.get(crit.id)
        evidence_files = []
        if cl:
            evidence_files = [
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

        claims_list.append(
            BcsCaseClaimItem(
                criterion=CriterionSchema(
                    id=crit.id,
                    campaign_id=crit.campaign_id,
                    code=crit.code,
                    title=crit.title,
                    description=crit.description,
                    max_score=format_score(crit.max_score),
                    requires_evidence=crit.requires_evidence,
                    sort_order=crit.sort_order,
                ),
                self_score=format_score(cl.self_score) if cl else None,
                student_note=cl.student_note if cl else None,
                approved_score=format_score(cl.approved_score) if cl else None,
                bcs_reason=cl.bcs_reason if cl else None,
                evidence=evidence_files,
            )
        )

    supplement_requests = (
        db.query(SupplementRequest)
        .filter(SupplementRequest.case_id == case.id)
        .order_by(SupplementRequest.requested_at.desc())
        .all()
    )
    latest_supp = supplement_requests[0] if supplement_requests else None
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

    # History from audit events
    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(20)
        .all()
    )
    actors = {u.id: u.username for u in db.query(User).filter(User.id.in_([ev.actor_user_id for ev in audit_events if ev.actor_user_id])).all()}
    history_items = [
        BcsCaseHistoryItem(
            action=ev.action,
            at=format_datetime(ev.created_at),
            actor=actors.get(ev.actor_user_id, "Hệ thống"),
        )
        for ev in audit_events
    ]

    return BcsCaseDetail(
        id=case.id,
        version=case.version,
        status=case.status,
        student=BcsCaseStudentInfo(
            id=student.id,
            code=student.username,
            full_name=student.full_name,
        ),
        deadlines=BcsCaseDeadlines(
            submission_at=format_datetime(campaign.submission_deadline_at),
            supplement_at=format_datetime(latest_supp.deadline_at) if latest_supp else None,
        ),
        rounds=BcsCaseRounds(
            info=case.info_round,
            info_max=campaign.max_info_rounds,
            proof=case.proof_round,
            proof_max=campaign.max_proof_rounds,
        ),
        claims=claims_list,
        supplement_requests=supp_schemas,
        review_mode="MANUAL",
        history=history_items,
    )


@router.post("/cases/{caseId}/supplement-requests", response_model=SupplementRequestSchema, dependencies=[Depends(verify_csrf)])
def request_supplement(
    caseId: str,
    payload: CreateSupplementRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")

    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    _verify_bcs_class(user, class_ids, campaign.class_id)

    if case.version != payload.expected_version:
        raise AppError(status_code=409, code="CASE_CHANGED", message="Hồ sơ đã thay đổi, vui lòng tải lại.")

    if case.status != "BCS_REVIEW":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể yêu cầu bổ sung khi hồ sơ ở trạng thái BCS_REVIEW (hiện tại: {case.status})."
        )

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=campaign.supplement_period_hours)

    if payload.kind == "PROOF":
        if case.proof_round >= campaign.max_proof_rounds:
            raise AppError(
                status_code=422,
                code="MAX_ROUNDS_EXCEEDED",
                message=f"Đã đạt giới hạn tối đa {campaign.max_proof_rounds} lượt bổ sung minh chứng."
            )
        case.proof_round += 1
        case.status = "NEEDS_PROOF"
        round_no = case.proof_round
    elif payload.kind == "INFO":
        if case.info_round >= campaign.max_info_rounds:
            raise AppError(
                status_code=422,
                code="MAX_ROUNDS_EXCEEDED",
                message=f"Đã đạt giới hạn tối đa {campaign.max_info_rounds} lượt bổ sung thông tin."
            )
        case.info_round += 1
        case.status = "NEEDS_INFO"
        round_no = case.info_round
    else:
        raise AppError(status_code=422, code="INVALID_KIND", message="Loại yêu cầu bổ sung phải là INFO hoặc PROOF.")

    supp_req = SupplementRequest(
        case_id=case.id,
        kind=payload.kind,
        criterion_id=payload.criterion_id,
        reason=payload.reason,
        round_no=round_no,
        requested_by=user.id,
        requested_at=now,
        deadline_at=deadline,
    )
    db.add(supp_req)
    case.version += 1
    case.updated_at = now

    send_notification(
        db,
        user_id=case.student_id,
        type=f"NEEDS_{payload.kind}",
        title=f"Yêu cầu bổ sung {'minh chứng' if payload.kind == 'PROOF' else 'thông tin'}",
        body=f"BCS yêu cầu bạn bổ sung: {payload.reason}. Hạn bổ sung: {deadline.strftime('%d/%m/%Y %H:%M')}.",
        case_id=case.id,
        dedup_key=f"needs_{payload.kind.lower()}_{case.id}_{round_no}",
    )
    log_audit(
        db,
        campaign_id=campaign.id,
        case_id=case.id,
        action=f"SUPPLEMENT_{payload.kind}_REQUESTED",
        actor_user_id=user.id,
        after_json={"round": round_no, "reason": payload.reason},
    )
    db.commit()
    db.refresh(supp_req)

    return SupplementRequestSchema(
        id=supp_req.id,
        case_id=supp_req.case_id,
        kind=supp_req.kind,
        criterion_id=supp_req.criterion_id,
        round_no=supp_req.round_no,
        reason=supp_req.reason,
        requested_by=supp_req.requested_by,
        deadline_at=format_datetime(supp_req.deadline_at),
        fulfilled_at=format_datetime(supp_req.fulfilled_at),
    )


@router.put("/cases/{caseId}/claims/{criterionId}/review", response_model=ReviewClaimResponse, dependencies=[Depends(verify_csrf)])
def review_claim(
    caseId: str,
    criterionId: str,
    payload: ReviewClaimRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")

    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    _verify_bcs_class(user, class_ids, campaign.class_id)

    if case.version != payload.expected_version:
        raise AppError(status_code=409, code="CASE_CHANGED", message="Hồ sơ đã thay đổi, vui lòng tải lại.")

    if case.status != "BCS_REVIEW":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể chấm điểm khi hồ sơ ở trạng thái BCS_REVIEW (hiện tại: {case.status})."
        )

    crit = db.query(Criterion).filter(Criterion.id == criterionId, Criterion.campaign_id == campaign.id).first()
    if not crit:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy tiêu chí đánh giá.")

    parsed_approved = parse_score(payload.approved_score)
    validate_score_bounds(parsed_approved, crit.max_score, field_name=crit.code)

    claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == crit.id).first()
    if not claim:
        claim = Claim(case_id=case.id, criterion_id=crit.id)
        db.add(claim)
        db.flush()

    # Reason required if approved_score != self_score
    if claim.self_score is not None and parsed_approved != claim.self_score:
        if not payload.reason or not payload.reason.strip():
            raise AppError(
                status_code=422,
                code="REASON_REQUIRED",
                message=f"Bắt buộc nhập lý do khi điểm duyệt ({parsed_approved}) khác điểm tự khai ({claim.self_score}) ở tiêu chí {crit.code}."
            )

    now = datetime.now(timezone.utc)
    claim.approved_score = parsed_approved
    claim.bcs_reason = payload.reason
    claim.reviewed_by = user.id
    claim.reviewed_at = now
    case.version += 1
    case.updated_at = now

    db.commit()
    db.refresh(claim)
    db.refresh(case)

    return ReviewClaimResponse(
        case_id=case.id,
        version=case.version,
        claim=ClaimSchema(
            id=claim.id,
            criterion_id=claim.criterion_id,
            self_score=format_score(claim.self_score),
            student_note=claim.student_note,
            approved_score=format_score(claim.approved_score),
            bcs_reason=claim.bcs_reason,
            evidence=[
                EvidenceFileSchema(
                    id=ev.id,
                    original_name=ev.original_name,
                    mime_type=ev.mime_type,
                    size_bytes=ev.size_bytes,
                    uploaded_at=format_datetime(ev.uploaded_at),
                    is_current=ev.is_current,
                )
                for ev in claim.evidence_files
                if ev.is_current
            ],
        ),
    )


@router.post("/cases/{caseId}/complete-review", response_model=CompleteReviewResponse, dependencies=[Depends(verify_csrf)])
def complete_case_review(
    caseId: str,
    payload: CompleteReviewRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    case = db.query(Case).filter(Case.id == caseId).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")

    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    _verify_bcs_class(user, class_ids, campaign.class_id)

    now = datetime.now(timezone.utc)
    updated_case = complete_bcs_case_review(db, case, user, payload.expected_version, now)
    db.commit()
    db.refresh(updated_case)

    return CompleteReviewResponse(
        case_id=updated_case.id,
        status=updated_case.status,
        proposed_total=format_score(updated_case.proposed_total),
        version=updated_case.version,
    )


@router.post("/campaigns/{id}/meetings", response_model=MeetingSchema, dependencies=[Depends(verify_csrf)])
def create_or_update_meeting(
    id: str,
    payload: CreateMeetingRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    if payload.kind not in ["BCS", "CLASS"]:
        raise AppError(status_code=422, code="INVALID_MEETING_KIND", message="Loại cuộc họp phải là BCS hoặc CLASS.")

    try:
        held_at = datetime.fromisoformat(payload.held_at.replace("Z", "+00:00"))
    except Exception:
        raise AppError(status_code=422, code="INVALID_DATE_FORMAT", message="Định dạng thời gian cuộc họp không hợp lệ.")

    meeting = db.query(Meeting).filter(Meeting.campaign_id == campaign.id, Meeting.kind == payload.kind).first()
    if meeting:
        meeting.held_at = held_at
        meeting.note = payload.note
        meeting.recorded_by = user.id
    else:
        meeting = Meeting(
            campaign_id=campaign.id,
            kind=payload.kind,
            held_at=held_at,
            note=payload.note,
            recorded_by=user.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(meeting)

    log_audit(
        db,
        campaign_id=campaign.id,
        action=f"MEETING_{payload.kind}_RECORDED",
        actor_user_id=user.id,
        after_json={"kind": payload.kind, "held_at": held_at.isoformat(), "note": payload.note},
    )
    db.commit()
    db.refresh(meeting)

    return MeetingSchema(
        id=meeting.id,
        campaign_id=meeting.campaign_id,
        kind=meeting.kind,
        held_at=format_datetime(meeting.held_at),
        note=meeting.note,
    )


@router.post("/campaigns/{id}/publish", response_model=PublishCampaignResponse, dependencies=[Depends(verify_csrf)])
def publish_results(
    id: str,
    payload: PublishCampaignRequest = PublishCampaignRequest(),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    now = datetime.now(timezone.utc)
    updated_campaign = publish_campaign(db, campaign, user, payload.expected_campaign_status, now)
    db.commit()
    db.refresh(updated_campaign)

    appeal_dl = updated_campaign.published_at + timedelta(hours=updated_campaign.appeal_period_hours)
    return PublishCampaignResponse(
        campaign_id=updated_campaign.id,
        status=updated_campaign.status,
        published_at=format_datetime(updated_campaign.published_at),
        appeal_deadline_at=format_datetime(appeal_dl),
    )


@router.get("/campaigns/{id}/scoreboard", response_model=ScoreboardResponse)
def get_scoreboard(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    cases = (
        db.query(Case, User)
        .join(User, Case.student_id == User.id)
        .filter(Case.campaign_id == campaign.id)
        .order_by(User.username.asc())
        .all()
    )
    meetings = db.query(Meeting).filter(Meeting.campaign_id == campaign.id).all()
    meeting_kinds = {m.kind for m in meetings}
    has_all_meetings = "BCS" in meeting_kinds and "CLASS" in meeting_kinds

    all_cases_ready = all(
        c.status in ["PROPOSED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT", "PUBLISHED", "ACCEPTED", "APPEALED", "ACCEPTED_AUTO", "RESOLVED", "FINALIZED"]
        for c, _ in cases
    ) and len(cases) > 0

    can_publish = (campaign.status in ["OPEN", "REVIEW"]) and has_all_meetings and all_cases_ready

    meeting_schemas = [
        MeetingSchema(
            id=m.id,
            campaign_id=m.campaign_id,
            kind=m.kind,
            held_at=format_datetime(m.held_at),
            note=m.note,
        )
        for m in meetings
    ]

    items = [
        ScoreboardItem(
            case_id=c.id,
            student_code=u.username,
            student_name=u.full_name,
            status=c.status,
            claimed_total=format_score(c.claimed_total),
            proposed_total=format_score(c.proposed_total),
            final_total=format_score(c.final_total),
        )
        for c, u in cases
    ]

    return ScoreboardResponse(
        campaign_id=campaign.id,
        can_publish=can_publish,
        meetings=meeting_schemas,
        items=items,
    )


@router.get("/campaigns/{id}/appeals", response_model=List[AppealDetailItem])
def get_campaign_appeals(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    appeals_records = (
        db.query(Appeal, Case, User, Criterion)
        .join(Case, Appeal.case_id == Case.id)
        .join(User, Case.student_id == User.id)
        .join(Criterion, Appeal.criterion_id == Criterion.id)
        .filter(Case.campaign_id == campaign.id)
        .order_by(Appeal.submitted_at.desc())
        .all()
    )

    result = []
    for ap, c, u, crit in appeals_records:
        claim = db.query(Claim).filter(Claim.case_id == c.id, Claim.criterion_id == crit.id).first()
        evidence_files = []
        if claim:
            evidence_files = [
                EvidenceFileSchema(
                    id=ev.id,
                    original_name=ev.original_name,
                    mime_type=ev.mime_type,
                    size_bytes=ev.size_bytes,
                    uploaded_at=format_datetime(ev.uploaded_at),
                    is_current=ev.is_current,
                )
                for ev in claim.evidence_files
                if ev.is_current
            ]

        result.append(
            AppealDetailItem(
                id=ap.id,
                case_id=ap.case_id,
                student_code=u.username,
                student_name=u.full_name,
                criterion_code=crit.code,
                criterion_title=crit.title,
                self_score=format_score(claim.self_score) if claim else "0.00",
                proposed_score=format_score(claim.approved_score) if claim else "0.00",
                student_reason=ap.student_reason,
                status=ap.status,
                resolution=ap.resolution,
                new_score=format_score(ap.new_score),
                bcs_reason=ap.bcs_reason,
                evidence=evidence_files,
            )
        )

    return result


@router.post("/appeals/{appealId}/resolve", response_model=AppealSchema, dependencies=[Depends(verify_csrf)])
def resolve_appeal(
    appealId: str,
    payload: ResolveAppealRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    appeal = db.query(Appeal).filter(Appeal.id == appealId).first()
    if not appeal:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy khiếu nại.")

    case = db.query(Case).filter(Case.id == appeal.case_id).first()
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    _verify_bcs_class(user, class_ids, campaign.class_id)

    if appeal.status != "OPEN":
        raise AppError(status_code=409, code="INVALID_STATE", message="Khiếu nại này đã được xử lý trước đó.")

    if payload.resolution not in ["KEEP", "ADJUST"]:
        raise AppError(status_code=422, code="INVALID_RESOLUTION", message="Quyết định xử lý phải là KEEP hoặc ADJUST.")

    crit = db.query(Criterion).filter(Criterion.id == appeal.criterion_id).first()
    claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == crit.id).first()

    now = datetime.now(timezone.utc)
    old_score = claim.approved_score if claim else None
    parsed_new_score = None

    if payload.resolution == "ADJUST":
        if payload.new_score is None:
            raise AppError(status_code=422, code="SCORE_REQUIRED", message="Bắt buộc nhập điểm mới khi chọn Điều chỉnh điểm.")
        parsed_new_score = parse_score(payload.new_score)
        validate_score_bounds(parsed_new_score, crit.max_score, field_name=crit.code)

        if claim:
            claim.approved_score = parsed_new_score
            claim.bcs_reason = payload.reason
            claim.reviewed_by = user.id
            claim.reviewed_at = now

        # Recompute case proposed_total
        all_claims = db.query(Claim).filter(Claim.case_id == case.id).all()
        scores = [cl.approved_score for cl in all_claims if cl.id != (claim.id if claim else "")]
        scores.append(parsed_new_score)
        case.proposed_total = sum_scores(scores)
        case.version += 1
        case.updated_at = now

    appeal.status = "RESOLVED"
    appeal.resolution = payload.resolution
    appeal.new_score = parsed_new_score
    appeal.bcs_reason = payload.reason
    appeal.resolved_by = user.id
    appeal.resolved_at = now

    # Check if all appeals for this case are resolved
    remaining_open = (
        db.query(Appeal)
        .filter(Appeal.case_id == case.id, Appeal.id != appeal.id, Appeal.status == "OPEN")
        .count()
    )
    if remaining_open == 0:
        case.status = "RESOLVED"
        case.version += 1
        case.updated_at = now

    send_notification(
        db,
        user_id=case.student_id,
        type="APPEAL_RESOLVED",
        title="Khiếu nại điểm rèn luyện đã được xử lý",
        body=f"BCS đã giải quyết khiếu nại tiêu chí {crit.code} ({'Giữ nguyên' if payload.resolution == 'KEEP' else f'Điều chỉnh thành {parsed_new_score:.2f}'}). Lý do: {payload.reason}.",
        case_id=case.id,
        dedup_key=f"appeal_resolved_{appeal.id}",
    )
    log_audit(
        db,
        campaign_id=campaign.id,
        case_id=case.id,
        action="APPEAL_RESOLVED",
        actor_user_id=user.id,
        before_json={"old_score": str(old_score) if old_score else None},
        after_json={"resolution": payload.resolution, "new_score": str(parsed_new_score) if parsed_new_score else None, "reason": payload.reason},
    )
    db.commit()
    db.refresh(appeal)

    return AppealSchema(
        id=appeal.id,
        case_id=appeal.case_id,
        criterion_id=appeal.criterion_id,
        student_reason=appeal.student_reason,
        status=appeal.status,
        resolution=appeal.resolution,
        new_score=format_score(appeal.new_score),
        bcs_reason=appeal.bcs_reason,
        submitted_at=format_datetime(appeal.submitted_at),
        resolved_at=format_datetime(appeal.resolved_at),
    )


@router.post("/campaigns/{id}/finalize", response_model=FinalizeCampaignResponse, dependencies=[Depends(verify_csrf)])
def finalize_results(
    id: str,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)

    now = datetime.now(timezone.utc)
    updated_campaign = finalize_campaign(db, campaign, user, now)
    db.commit()
    db.refresh(updated_campaign)

    return FinalizeCampaignResponse(
        campaign_id=updated_campaign.id,
        status=updated_campaign.status,
        finalized_at=format_datetime(updated_campaign.finalized_at),
    )
