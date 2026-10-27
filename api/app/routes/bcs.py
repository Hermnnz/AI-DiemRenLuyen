from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Header, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from api.app.database import get_db
from api.app.models.entities import (
    User,
    Campaign,
    Criterion,
    Case,
    Claim,
    EvidenceFile,
    BcsEvidenceDecision,
    SupplementRequest,
    Meeting,
    Appeal,
    AuditEvent,
    ClassMember,
    FinalHandoff,
)
from api.app.schemas import (
    CampaignSchema,
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
    BcsEvidenceDecisionSchema,
    SetEvidenceDecisionRequest,
    SetEvidenceDecisionResponse,
    FinalHandoffSchema,
    ConfirmDraftReviewRequest,
    DraftReviewStatus,
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
from api.app.services.scoring_service import parse_score, validate_score_bounds, validate_criterion_levels, sum_scores
from api.app.services.workflow_service import complete_bcs_case_review, publish_campaign, finalize_campaign
from api.app.services.audit_service import log_audit
from api.app.services.notification_service import send_notification
from api.app.services.evidence_decision_service import required_evidence_file_ids
from api.app.services.final_handoff_service import final_score_fingerprint, handoff_status
from api.app.services.draft_review_service import draft_review_status
from api.app.services.ai_feedback_service import record_bcs_ai_feedback

router = APIRouter(prefix="/bcs", tags=["BCS"])


def _verify_bcs_class(user: User, class_ids: List[str], campaign_class_id: str):
    if campaign_class_id not in class_ids:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Bạn không có quyền quản lý đợt đánh giá của lớp này.",
        )


@router.get("/campaigns/active", response_model=CampaignSchema)
def get_bcs_active_campaign(
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = (
        db.query(Campaign)
        .filter(Campaign.class_id.in_(class_ids))
        .order_by(Campaign.created_at.desc())
        .first()
    )
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá nào cho lớp của bạn.")

    crit_list = (
        db.query(Criterion)
        .filter(Criterion.campaign_id == campaign.id)
        .order_by(Criterion.sort_order)
        .all()
    )
    crit_schemas = [
        CriterionSchema(
            id=c.id,
            campaign_id=c.campaign_id,
            code=c.code,
            section_code=c.section_code,
            section_title=c.section_title,
            section_max_score=format_score(c.section_max_score) if c.section_max_score is not None else None,
            title=c.title,
            description=c.description,
            max_score=format_score(c.max_score),
            requires_evidence=c.requires_evidence,
            evidence_notes=c.evidence_notes,
            allowed_input_roles=c.allowed_input_roles,
            rule_config=c.rule_config,
            sort_order=c.sort_order,
        )
        for c in crit_list
    ]

    return CampaignSchema(
        id=campaign.id,
        class_id=campaign.class_id,
        title=campaign.title,
        term=campaign.term,
        status=campaign.status,
        template_code=campaign.template_code or "LEGACY_DEMO",
        open_at=format_datetime(campaign.open_at),
        submission_deadline_at=format_datetime(campaign.submission_deadline_at),
        supplement_period_hours=campaign.supplement_period_hours,
        appeal_period_hours=campaign.appeal_period_hours,
        reminder_after_hours=campaign.reminder_after_hours,
        max_info_rounds=campaign.max_info_rounds,
        max_proof_rounds=campaign.max_proof_rounds,
        criteria=crit_schemas,
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
    claims = (
        db.query(Claim)
        .options(joinedload(Claim.evidence_files))
        .filter(Claim.case_id == case.id)
        .all()
    )
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
                    section_code=crit.section_code,
                    section_title=crit.section_title,
                    section_max_score=format_score(crit.section_max_score) if crit.section_max_score is not None else None,
                    title=crit.title,
                    description=crit.description,
                    max_score=format_score(crit.max_score),
                    requires_evidence=crit.requires_evidence,
                    evidence_notes=crit.evidence_notes,
                    allowed_input_roles=crit.allowed_input_roles,
                    rule_config=crit.rule_config,
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
    meeting_kinds = {item.kind for item in db.query(Meeting).filter(Meeting.campaign_id == campaign.id).all()}
    draft_editable = (case.status == "PROPOSED" and campaign.status in {"OPEN", "REVIEW"}
                      and "BCS" in meeting_kinds and "CLASS" not in meeting_kinds)
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

    current_file_ids = [ev.id for cl in claims for ev in cl.evidence_files if ev.is_current]
    evidence_decisions = (
        db.query(BcsEvidenceDecision).filter(BcsEvidenceDecision.evidence_file_id.in_(current_file_ids)).all()
        if current_file_ids else []
    )

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
        evidence_decisions=[_evidence_decision_schema(item) for item in evidence_decisions],
        evidence_review_required_ids=sorted(required_evidence_file_ids(db, case)),
        draft_editable=draft_editable,
        supplement_requests=supp_schemas,
        review_mode="MANUAL",
        history=history_items,
    )


def _evidence_decision_schema(item: BcsEvidenceDecision) -> BcsEvidenceDecisionSchema:
    return BcsEvidenceDecisionSchema(
        evidence_file_id=item.evidence_file_id,
        decision=item.decision,
        reason=item.reason,
        reviewed_by=item.reviewed_by,
        reviewed_at=format_datetime(item.reviewed_at),
    )


@router.put("/cases/{caseId}/evidence/{evidenceId}/decision", response_model=SetEvidenceDecisionResponse, dependencies=[Depends(verify_csrf)])
def set_evidence_decision(
    caseId: str,
    evidenceId: str,
    payload: SetEvidenceDecisionRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    case = db.query(Case).filter(Case.id == caseId).with_for_update().first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    _verify_bcs_class(user, class_ids, campaign.class_id)
    if case.version != payload.expected_version:
        raise AppError(status_code=409, code="CASE_CHANGED", message="Hồ sơ đã thay đổi, vui lòng tải lại.")
    if case.status != "BCS_REVIEW":
        raise AppError(status_code=409, code="INVALID_STATE", message="Chỉ có thể kết luận minh chứng khi hồ sơ đang chờ BCS xem xét.")

    evidence = (
        db.query(EvidenceFile).join(Claim, EvidenceFile.claim_id == Claim.id)
        .filter(EvidenceFile.id == evidenceId, EvidenceFile.is_current.is_(True), Claim.case_id == case.id)
        .first()
    )
    if not evidence:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy minh chứng hiện hành trong hồ sơ này.")
    reason = payload.reason.strip()
    if not reason:
        raise AppError(status_code=422, code="REASON_REQUIRED", message="Hãy ghi rõ căn cứ cho quyết định về minh chứng.")

    now = datetime.now(timezone.utc)
    previous = db.query(BcsEvidenceDecision).filter(BcsEvidenceDecision.evidence_file_id == evidence.id).first()
    before_json = {"decision": previous.decision, "reason": previous.reason} if previous else None
    if payload.decision == "REQUEST_SUPPLEMENT":
        if case.proof_round >= campaign.max_proof_rounds:
            raise AppError(status_code=422, code="MAX_ROUNDS_EXCEEDED", message=f"Đã đạt giới hạn {campaign.max_proof_rounds} lượt bổ sung minh chứng. BCS cần chốt quyết định trên hồ sơ hiện có.")
        case.proof_round += 1
        case.status = "NEEDS_PROOF"
        deadline = now + timedelta(hours=campaign.supplement_period_hours)
        db.add(SupplementRequest(
            case_id=case.id, kind="PROOF", criterion_id=evidence.claim.criterion_id,
            reason=reason, round_no=case.proof_round, requested_by=user.id,
            requested_at=now, deadline_at=deadline,
        ))
        send_notification(
            db, user_id=case.student_id, type="NEEDS_PROOF", title="Yêu cầu bổ sung minh chứng",
            body=f"BCS yêu cầu bạn bổ sung: {reason}. Hạn bổ sung: {deadline.strftime('%d/%m/%Y %H:%M')}.",
            case_id=case.id, dedup_key=f"needs_proof_{case.id}_{case.proof_round}",
        )

    if previous:
        previous.decision = payload.decision
        previous.reason = reason
        previous.reviewed_by = user.id
        previous.reviewed_at = now
        item = previous
    else:
        item = BcsEvidenceDecision(
            evidence_file_id=evidence.id, decision=payload.decision, reason=reason,
            reviewed_by=user.id, reviewed_at=now,
        )
        db.add(item)
    case.version += 1
    case.updated_at = now
    log_audit(
        db, campaign_id=campaign.id, case_id=case.id, action="BCS_EVIDENCE_DECIDED",
        actor_user_id=user.id, before_json=before_json,
        after_json={"evidence_file_id": evidence.id, "criterion_id": evidence.claim.criterion_id,
                    "decision": payload.decision, "reason": reason, "version": case.version},
    )
    record_bcs_ai_feedback(
        db, evidence=evidence, case=case, bcs_decision=payload.decision,
        bcs_reason=reason, user_id=user.id, now=now,
    )
    db.commit()
    return SetEvidenceDecisionResponse(
        case_id=case.id, version=case.version, status=case.status,
        evidence_decision=_evidence_decision_schema(item),
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

    meeting_kinds = {item.kind for item in db.query(Meeting).filter(Meeting.campaign_id == campaign.id).all()}
    editing_draft = (case.status == "PROPOSED" and campaign.status in {"OPEN", "REVIEW"}
                     and "BCS" in meeting_kinds and "CLASS" not in meeting_kinds)
    if case.status != "BCS_REVIEW" and not editing_draft:
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể chấm điểm khi hồ sơ chờ BCS, hoặc sửa dự thảo sau họp BCS và trước họp lớp (hiện tại: {case.status})."
        )

    crit = db.query(Criterion).filter(Criterion.id == criterionId, Criterion.campaign_id == campaign.id).first()
    if not crit:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy tiêu chí đánh giá.")

    parsed_approved = parse_score(payload.approved_score)
    validate_score_bounds(parsed_approved, crit.max_score, field_name=crit.code)
    validate_criterion_levels(crit.code, parsed_approved)

    claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == crit.id).first()
    if not claim:
        claim = Claim(case_id=case.id, criterion_id=crit.id)
        db.add(claim)
        db.flush()

    if editing_draft and (not payload.reason or not payload.reason.strip()):
        raise AppError(status_code=422, code="REASON_REQUIRED", message="Điều chỉnh dự thảo sau họp BCS phải ghi lý do, kể cả khi giữ nguyên điểm.")
    if editing_draft and parsed_approved == claim.approved_score and payload.reason.strip() == (claim.bcs_reason or "").strip():
        raise AppError(status_code=422, code="NO_CHANGE", message="Điểm và lý do chưa thay đổi so với bản dự thảo hiện tại.")
    if editing_draft and parsed_approved != claim.approved_score and payload.reason.strip() == (claim.bcs_reason or "").strip():
        raise AppError(status_code=422, code="REASON_REQUIRED", message="Khi đổi điểm dự thảo, hãy ghi căn cứ điều chỉnh mới.")

    # Reason required if approved_score != self_score
    if claim.self_score is not None and parsed_approved != claim.self_score:
        if not payload.reason or not payload.reason.strip():
            raise AppError(
                status_code=422,
                code="REASON_REQUIRED",
                message=f"Bắt buộc nhập lý do khi điểm duyệt ({parsed_approved}) khác điểm tự khai ({claim.self_score}) ở tiêu chí {crit.code}."
            )

    now = datetime.now(timezone.utc)
    old_score = format_score(claim.approved_score)
    old_reason = claim.bcs_reason
    claim.approved_score = parsed_approved
    claim.bcs_reason = payload.reason
    claim.reviewed_by = user.id
    claim.reviewed_at = now
    if editing_draft:
        all_claims = db.query(Claim).filter(Claim.case_id == case.id).all()
        scores = [item.approved_score for item in all_claims]
        if any(score is None for score in scores):
            raise AppError(status_code=422, code="UNREVIEWED_CRITERIA", message="Hồ sơ còn tiêu chí chưa được BCS duyệt điểm.")
        section_totals = {}
        for item in all_claims:
            item_criterion = db.query(Criterion).filter(Criterion.id == item.criterion_id).first()
            if item_criterion and item_criterion.section_code and item_criterion.section_max_score is not None:
                group = section_totals.setdefault(item_criterion.section_code, {"total": 0, "max": item_criterion.section_max_score})
                group["total"] += item.approved_score
        for code, group in section_totals.items():
            if group["total"] > group["max"]:
                raise AppError(status_code=422, code="SECTION_SCORE_OUT_OF_BOUNDS", message=f"Tổng điểm mục {code} vượt trần {group['max']}.")
        case.proposed_total = sum_scores(scores)
        if case.proposed_total > 100 and section_totals:
            raise AppError(status_code=422, code="TOTAL_SCORE_OUT_OF_BOUNDS", message="Tổng điểm dự thảo không được vượt 100.")
        log_audit(
            db, campaign_id=campaign.id, case_id=case.id, action="DRAFT_SCORE_REVISED",
            actor_user_id=user.id,
            before_json={"criterion_id": crit.id, "approved_score": old_score, "reason": old_reason},
            after_json={"criterion_id": crit.id, "approved_score": format_score(parsed_approved), "reason": payload.reason},
        )
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
            academic_gpa=format_score(claim.academic_gpa) if claim.academic_gpa is not None else None,
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
    if campaign.status not in {"OPEN", "REVIEW"}:
        raise AppError(status_code=409, code="INVALID_STATE", message="Không thể sửa biên bản sau khi đã công bố điểm.")
    if payload.kind == "CLASS":
        if not db.query(Meeting).filter(Meeting.campaign_id == id, Meeting.kind == "BCS").first():
            raise AppError(status_code=422, code="BCS_MEETING_REQUIRED", message="Hãy ghi nhận họp BCS trước khi họp lớp.")
        if not draft_review_status(db, campaign)["reviewed"]:
            raise AppError(status_code=422, code="DRAFT_REVIEW_REQUIRED", message="BCS cần rà soát và xác nhận bảng điểm dự thảo trước khi ghi họp lớp.")
    elif db.query(Meeting).filter(Meeting.campaign_id == id, Meeting.kind == "CLASS").first():
        raise AppError(status_code=409, code="MEETING_ORDER_LOCKED", message="Không thể sửa biên bản họp BCS sau khi đã ghi nhận họp lớp.")

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


@router.post("/campaigns/{id}/review-draft", response_model=DraftReviewStatus, dependencies=[Depends(verify_csrf)])
def confirm_draft_review(
    id: str,
    payload: ConfirmDraftReviewRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).with_for_update().first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)
    if campaign.status not in {"OPEN", "REVIEW"}:
        raise AppError(status_code=409, code="INVALID_STATE", message="Chỉ rà soát dự thảo trước khi công bố.")
    kinds = {item.kind for item in db.query(Meeting).filter(Meeting.campaign_id == id).all()}
    if "BCS" not in kinds or "CLASS" in kinds:
        raise AppError(status_code=422, code="MEETING_ORDER", message="Rà soát dự thảo sau họp BCS và trước họp lớp.")
    cases = db.query(Case).filter(Case.campaign_id == id).all()
    if not cases or any(item.status not in {"PROPOSED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"} for item in cases):
        raise AppError(status_code=422, code="CASES_NOT_READY", message="Hãy hoàn tất điểm dự kiến của mọi hồ sơ trước khi xác nhận dự thảo.")
    if not payload.note.strip():
        raise AppError(status_code=422, code="REASON_REQUIRED", message="Ghi chú rà soát phải nêu căn cứ BCS đã đối chiếu.")
    status = draft_review_status(db, campaign)
    if status["fingerprint"] != payload.expected_fingerprint:
        raise AppError(status_code=409, code="DRAFT_CHANGED", message="Bảng điểm dự thảo đã thay đổi. Hãy tải lại và rà soát lần nữa.")
    if status["reviewed"]:
        return DraftReviewStatus(**status)
    log_audit(
        db, campaign_id=id, action="DRAFT_REVIEW_CONFIRMED", actor_user_id=user.id,
        after_json={"fingerprint": status["fingerprint"], "note": payload.note.strip(), "case_count": len(cases)},
    )
    db.commit()
    return DraftReviewStatus(**draft_review_status(db, campaign))


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


@router.get("/campaigns/{id}/handoff", response_model=FinalHandoffSchema)
def get_final_handoff(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)
    return FinalHandoffSchema(**handoff_status(db.query(FinalHandoff).filter(FinalHandoff.campaign_id == id).first()))


@router.post("/campaigns/{id}/handoff", response_model=FinalHandoffSchema, dependencies=[Depends(verify_csrf)])
def send_final_handoff(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).with_for_update().first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    _verify_bcs_class(user, class_ids, campaign.class_id)
    if campaign.status != "FINALIZED":
        raise AppError(status_code=409, code="INVALID_STATE", message="Chỉ gửi bảng điểm cho GVCN sau khi đã chốt điểm chính thức.")
    existing = db.query(FinalHandoff).filter(FinalHandoff.campaign_id == id).first()
    if existing:
        return FinalHandoffSchema(**handoff_status(existing))
    recipients = (
        db.query(ClassMember.user_id).join(User, ClassMember.user_id == User.id)
        .filter(ClassMember.class_id == campaign.class_id, ClassMember.member_role == "GVCN",
                User.role == "GVCN", User.is_active.is_(True)).all()
    )
    if not recipients:
        raise AppError(status_code=422, code="NO_GVCN", message="Lớp chưa có GVCN đang hoạt động để nhận bảng điểm.")
    now = datetime.now(timezone.utc)
    handoff = FinalHandoff(
        campaign_id=id, snapshot_sha256=final_score_fingerprint(db, campaign),
        sent_by=user.id, sent_at=now,
    )
    db.add(handoff)
    for (recipient_id,) in recipients:
        send_notification(
            db, user_id=recipient_id, type="FINAL_HANDOFF",
            title="BCS đã gửi bảng điểm rèn luyện chính thức",
            body=f"Bảng điểm đợt {campaign.title} đã được chốt và gửi. Vui lòng mở mục kết quả cuối để xác nhận đã nhận.",
            dedup_key=f"final_handoff_{id}_{recipient_id}",
        )
    log_audit(
        db, campaign_id=id, action="FINAL_SCORES_SENT_TO_GVCN", actor_user_id=user.id,
        after_json={"snapshot_sha256": handoff.snapshot_sha256, "recipient_ids": [item[0] for item in recipients]},
    )
    db.commit()
    return FinalHandoffSchema(**handoff_status(handoff))


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

    draft_review = draft_review_status(db, campaign)
    can_publish = (campaign.status in ["OPEN", "REVIEW"]) and has_all_meetings and all_cases_ready and draft_review["reviewed"]

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
        draft_review=DraftReviewStatus(**draft_review),
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
        claim = (
            db.query(Claim)
            .options(joinedload(Claim.evidence_files))
            .filter(Claim.case_id == c.id, Claim.criterion_id == crit.id)
            .first()
        )
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
