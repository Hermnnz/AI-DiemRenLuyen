from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import Campaign, Criterion, Class, User, EvaluationTemplate, TemplateCriterion, UserPosition, Case, Claim, BcsAiFeedback, EvidenceFile
from api.app.schemas import (
    CreateCampaignRequest,
    CampaignSchema,
    CriterionSchema,
    OpenCampaignResponse,
    CreateCriterionInput,
    EvaluationTemplateSchema,
    TemplateCriterionSchema,
    UserPositionSchema,
    CreateUserPositionRequest,
    ImportAcademicScoresRequest,
    ImportAcademicScoresResponse,
    BcsAiFeedbackItemSchema,
    BcsAiFeedbackDetailSchema,
    VerifyGroundTruthRequest,
    AiFeedbackMetricsResponse,
    AiFeedbackListResponse,
    AppError,
    format_datetime,
    format_score,
)
from api.app.services.ai_feedback_service import (
    verify_ground_truth,
    calculate_ai_feedback_metrics,
    get_feedback_audit_history,
)
from api.app.services.auth_service import require_roles, verify_csrf
from api.app.services.file_service import get_file_path
from api.app.services.remote_storage import create_download_url, remote_storage_enabled
from api.app.services.workflow_service import open_campaign
from api.app.services.audit_service import log_audit
from api.app.services.scoring_service import parse_score, convert_gpa_to_score, sum_scores
from api.app.services.template_service import (
    CRITERIA_49K14_1_DEFINITIONS,
    CRITERIA_LEGACY_DEMO_DEFINITIONS,
    ensure_templates_seeded,
    TEMPLATE_49K14_1_CODE,
    TEMPLATE_LEGACY_DEMO_CODE,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _validate_campaign_config(payload: CreateCampaignRequest, db: Session):
    cls = db.query(Class).filter(Class.id == payload.class_id).first()
    if not cls:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy lớp học.")

    try:
        open_at = datetime.fromisoformat(payload.open_at.replace("Z", "+00:00"))
        sub_dl = datetime.fromisoformat(payload.submission_deadline_at.replace("Z", "+00:00"))
    except Exception:
        raise AppError(status_code=422, code="INVALID_DATE_FORMAT", message="Định dạng ngày giờ không hợp lệ.")

    if open_at >= sub_dl:
        raise AppError(
            status_code=422,
            code="INVALID_DEADLINE",
            message="Thời gian mở đợt phải trước hạn nộp hồ sơ.",
            fields={"open_at": "open_at phải nhỏ hơn submission_deadline_at"}
        )

    if bool(payload.term_start_on) != bool(payload.term_end_on):
        raise AppError(status_code=422, code="TERM_WINDOW_INCOMPLETE",
                       message="Cần nhập cả ngày bắt đầu và kết thúc học kỳ.")
    try:
        term_start_on = date.fromisoformat(payload.term_start_on) if payload.term_start_on else None
        term_end_on = date.fromisoformat(payload.term_end_on) if payload.term_end_on else None
    except ValueError as exc:
        raise AppError(status_code=422, code="INVALID_TERM_DATE", message="Ngày học kỳ phải theo dạng YYYY-MM-DD.") from exc
    if term_start_on and term_start_on > term_end_on:
        raise AppError(status_code=422, code="INVALID_TERM_WINDOW",
                       message="Ngày bắt đầu học kỳ phải trước hoặc bằng ngày kết thúc.")

    if not (0 < payload.reminder_after_hours < payload.appeal_period_hours):
        raise AppError(
            status_code=422,
            code="INVALID_REMINDER_HOURS",
            message="Thời gian nhắc hạn phải lớn hơn 0 và nhỏ hơn thời hạn khiếu nại.",
            fields={"reminder_after_hours": "Phải nhỏ hơn appeal_period_hours và lớn hơn 0"}
        )

    if payload.supplement_period_hours <= 0:
        raise AppError(status_code=422, code="INVALID_HOURS", message="Thời gian bổ sung phải lớn hơn 0.")

    if payload.max_info_rounds < 0 or payload.max_proof_rounds < 0:
        raise AppError(status_code=422, code="INVALID_ROUNDS", message="Số vòng bổ sung tối đa không được âm.")

    if not payload.criteria:
        # Tự động nạp tiêu chí từ mẫu nếu được chỉ định
        if payload.template_code == TEMPLATE_49K14_1_CODE:
            payload.criteria = [
                CreateCriterionInput(
                    code=c["code"],
                    section_code=c["section_code"],
                    section_title=c["section_title"],
                    section_max_score=str(c["section_max_score"]),
                    title=c["title"],
                    description=c["description"],
                    max_score=str(c["max_score"]),
                    requires_evidence=c["requires_evidence"],
                    evidence_notes=c.get("evidence_notes"),
                    allowed_input_roles=c.get("allowed_input_roles"),
                    rule_config=c.get("rule_config"),
                    sort_order=c["sort_order"],
                )
                for c in CRITERIA_49K14_1_DEFINITIONS
            ]
        elif payload.template_code == TEMPLATE_LEGACY_DEMO_CODE:
            payload.criteria = [
                CreateCriterionInput(
                    code=c["code"],
                    section_code=c.get("section_code"),
                    section_title=c.get("section_title"),
                    section_max_score=str(c["section_max_score"]) if c.get("section_max_score") else None,
                    title=c["title"],
                    description=c["description"],
                    max_score=str(c["max_score"]),
                    requires_evidence=c["requires_evidence"],
                    evidence_notes=c.get("evidence_notes"),
                    allowed_input_roles=c.get("allowed_input_roles"),
                    rule_config=c.get("rule_config"),
                    sort_order=c["sort_order"],
                )
                for c in CRITERIA_LEGACY_DEMO_DEFINITIONS
            ]
        else:
            raise AppError(status_code=422, code="CRITERIA_REQUIRED", message="Đợt đánh giá phải có ít nhất 1 tiêu chí hoặc chọn mẫu hợp lệ.")

    seen_codes = set()
    for crit in payload.criteria:
        if crit.code in seen_codes:
            raise AppError(status_code=422, code="DUPLICATE_CRITERION_CODE", message=f"Mã tiêu chí '{crit.code}' bị trùng lặp.")
        seen_codes.add(crit.code)
        parse_score(crit.max_score)

    return open_at, sub_dl, term_start_on, term_end_on


@router.post("/campaigns", response_model=CampaignSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def create_campaign(
    payload: CreateCampaignRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    admin_user, _ = auth_data
    open_at, sub_dl, term_start_on, term_end_on = _validate_campaign_config(payload, db)

    now = datetime.now(timezone.utc)
    campaign = Campaign(
        class_id=payload.class_id,
        title=payload.title,
        term=payload.term,
        term_start_on=term_start_on,
        term_end_on=term_end_on,
        template_code=payload.template_code or TEMPLATE_49K14_1_CODE,
        status="DRAFT",
        open_at=open_at,
        submission_deadline_at=sub_dl,
        supplement_period_hours=payload.supplement_period_hours,
        appeal_period_hours=payload.appeal_period_hours,
        reminder_after_hours=payload.reminder_after_hours,
        max_info_rounds=payload.max_info_rounds,
        max_proof_rounds=payload.max_proof_rounds,
        created_by=admin_user.id,
        created_at=now,
    )
    db.add(campaign)
    db.flush()

    criteria_list = []
    for crit_in in payload.criteria:
        crit = Criterion(
            campaign_id=campaign.id,
            code=crit_in.code,
            section_code=crit_in.section_code,
            section_title=crit_in.section_title,
            section_max_score=parse_score(crit_in.section_max_score) if crit_in.section_max_score else None,
            title=crit_in.title,
            description=crit_in.description,
            max_score=parse_score(crit_in.max_score),
            requires_evidence=crit_in.requires_evidence,
            evidence_notes=crit_in.evidence_notes,
            allowed_input_roles=crit_in.allowed_input_roles,
            rule_config=crit_in.rule_config,
            sort_order=crit_in.sort_order,
            created_at=now,
        )
        db.add(crit)
        criteria_list.append(crit)

    log_audit(
        db,
        campaign_id=campaign.id,
        action="CAMPAIGN_CREATED",
        actor_user_id=admin_user.id,
        after_json={"title": campaign.title, "term": campaign.term, "template_code": campaign.template_code},
    )
    db.commit()
    db.refresh(campaign)

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
        for c in criteria_list
    ]

    return CampaignSchema(
        id=campaign.id,
        class_id=campaign.class_id,
        title=campaign.title,
        term=campaign.term,
        term_start_on=campaign.term_start_on.isoformat() if campaign.term_start_on else None,
        term_end_on=campaign.term_end_on.isoformat() if campaign.term_end_on else None,
        status=campaign.status,
        template_code=campaign.template_code,
        open_at=format_datetime(campaign.open_at),
        submission_deadline_at=format_datetime(campaign.submission_deadline_at),
        supplement_period_hours=campaign.supplement_period_hours,
        appeal_period_hours=campaign.appeal_period_hours,
        reminder_after_hours=campaign.reminder_after_hours,
        max_info_rounds=campaign.max_info_rounds,
        max_proof_rounds=campaign.max_proof_rounds,
        criteria=crit_schemas,
    )


@router.put("/campaigns/{id}", response_model=CampaignSchema, dependencies=[Depends(verify_csrf)])
def update_campaign(
    id: str,
    payload: CreateCampaignRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    admin_user, _ = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")

    if campaign.status != "DRAFT":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể chỉnh sửa cấu hình khi đợt ở trạng thái DRAFT (hiện tại: {campaign.status})."
        )

    open_at, sub_dl, term_start_on, term_end_on = _validate_campaign_config(payload, db)

    now = datetime.now(timezone.utc)
    campaign.class_id = payload.class_id
    campaign.title = payload.title
    campaign.term = payload.term
    campaign.term_start_on = term_start_on
    campaign.term_end_on = term_end_on
    campaign.open_at = open_at
    campaign.submission_deadline_at = sub_dl
    campaign.supplement_period_hours = payload.supplement_period_hours
    campaign.appeal_period_hours = payload.appeal_period_hours
    campaign.reminder_after_hours = payload.reminder_after_hours
    campaign.max_info_rounds = payload.max_info_rounds
    campaign.max_proof_rounds = payload.max_proof_rounds
    campaign.updated_at = now

    # Remove old criteria and insert updated criteria
    previous_criteria = {item.code: item for item in db.query(Criterion).filter(Criterion.campaign_id == campaign.id).all()}
    db.query(Criterion).filter(Criterion.campaign_id == campaign.id).delete()
    criteria_list = []
    for crit_in in payload.criteria:
        previous = previous_criteria.get(crit_in.code)
        crit = Criterion(
            campaign_id=campaign.id,
            code=crit_in.code,
            section_code=crit_in.section_code or (previous.section_code if previous else None),
            section_title=crit_in.section_title or (previous.section_title if previous else None),
            section_max_score=(parse_score(crit_in.section_max_score) if crit_in.section_max_score
                               else previous.section_max_score if previous else None),
            title=crit_in.title,
            description=crit_in.description,
            max_score=parse_score(crit_in.max_score),
            requires_evidence=crit_in.requires_evidence,
            evidence_notes=crit_in.evidence_notes if crit_in.evidence_notes is not None else previous.evidence_notes if previous else None,
            allowed_input_roles=crit_in.allowed_input_roles if crit_in.allowed_input_roles is not None else previous.allowed_input_roles if previous else None,
            rule_config=crit_in.rule_config if crit_in.rule_config is not None else previous.rule_config if previous else None,
            sort_order=crit_in.sort_order,
            created_at=now,
        )
        db.add(crit)
        criteria_list.append(crit)

    log_audit(
        db,
        campaign_id=campaign.id,
        action="CAMPAIGN_UPDATED",
        actor_user_id=admin_user.id,
    )
    db.commit()
    db.refresh(campaign)

    crit_schemas = [
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
        for c in criteria_list
    ]

    return CampaignSchema(
        id=campaign.id,
        class_id=campaign.class_id,
        title=campaign.title,
        term=campaign.term,
        term_start_on=campaign.term_start_on.isoformat() if campaign.term_start_on else None,
        term_end_on=campaign.term_end_on.isoformat() if campaign.term_end_on else None,
        status=campaign.status,
        open_at=format_datetime(campaign.open_at),
        submission_deadline_at=format_datetime(campaign.submission_deadline_at),
        supplement_period_hours=campaign.supplement_period_hours,
        appeal_period_hours=campaign.appeal_period_hours,
        reminder_after_hours=campaign.reminder_after_hours,
        max_info_rounds=campaign.max_info_rounds,
        max_proof_rounds=campaign.max_proof_rounds,
        criteria=crit_schemas,
    )


@router.post("/campaigns/{id}/open", response_model=OpenCampaignResponse, dependencies=[Depends(verify_csrf)])
def trigger_open_campaign(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    admin_user, _ = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")

    now = datetime.now(timezone.utc)
    open_campaign(db, campaign, admin_user.id, now)
    db.commit()
    db.refresh(campaign)

    return OpenCampaignResponse(
        id=campaign.id,
        status=campaign.status,
    )


@router.get("/campaigns", response_model=List[CampaignSchema])
def list_campaigns(
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    result = []
    for camp in campaigns:
        crit_list = (
            db.query(Criterion)
            .filter(Criterion.campaign_id == camp.id)
            .order_by(Criterion.sort_order)
            .all()
        )
        crit_schemas = [
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
            for c in crit_list
        ]
        result.append(
            CampaignSchema(
                id=camp.id,
                class_id=camp.class_id,
                title=camp.title,
                term=camp.term,
                term_start_on=camp.term_start_on.isoformat() if camp.term_start_on else None,
                term_end_on=camp.term_end_on.isoformat() if camp.term_end_on else None,
                status=camp.status,
                open_at=format_datetime(camp.open_at),
                submission_deadline_at=format_datetime(camp.submission_deadline_at),
                supplement_period_hours=camp.supplement_period_hours,
                appeal_period_hours=camp.appeal_period_hours,
                reminder_after_hours=camp.reminder_after_hours,
                max_info_rounds=camp.max_info_rounds,
                max_proof_rounds=camp.max_proof_rounds,
                criteria=crit_schemas,
            )
        )
    return result


@router.get("/campaigns/{id}", response_model=CampaignSchema)
def get_campaign_by_id(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    camp = db.query(Campaign).filter(Campaign.id == id).first()
    if not camp:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")

    crit_list = (
        db.query(Criterion)
        .filter(Criterion.campaign_id == camp.id)
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
        id=camp.id,
        class_id=camp.class_id,
        title=camp.title,
        term=camp.term,
        term_start_on=camp.term_start_on.isoformat() if camp.term_start_on else None,
        term_end_on=camp.term_end_on.isoformat() if camp.term_end_on else None,
        status=camp.status,
        template_code=camp.template_code or "LEGACY_DEMO",
        open_at=format_datetime(camp.open_at),
        submission_deadline_at=format_datetime(camp.submission_deadline_at),
        supplement_period_hours=camp.supplement_period_hours,
        appeal_period_hours=camp.appeal_period_hours,
        reminder_after_hours=camp.reminder_after_hours,
        max_info_rounds=camp.max_info_rounds,
        max_proof_rounds=camp.max_proof_rounds,
        criteria=crit_schemas,
    )


# -------------------------------------------------------------
# Quản lý Mẫu Quy tắc chấm (Evaluation Templates)
# -------------------------------------------------------------
@router.get("/evaluation-templates", response_model=List[EvaluationTemplateSchema])
def list_evaluation_templates(
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    ensure_templates_seeded(db)
    templates = db.query(EvaluationTemplate).filter(EvaluationTemplate.is_active.is_(True)).order_by(EvaluationTemplate.version.desc()).all()

    result = []
    for tpl in templates:
        crits = db.query(TemplateCriterion).filter(TemplateCriterion.template_id == tpl.id).order_by(TemplateCriterion.sort_order).all()
        crit_schemas = [
            TemplateCriterionSchema(
                id=c.id,
                template_id=c.template_id,
                code=c.code,
                section_code=c.section_code,
                section_title=c.section_title,
                section_max_score=format_score(c.section_max_score),
                title=c.title,
                description=c.description,
                max_score=format_score(c.max_score),
                requires_evidence=c.requires_evidence,
                evidence_notes=c.evidence_notes,
                allowed_input_roles=c.allowed_input_roles,
                rule_config=c.rule_config,
                sort_order=c.sort_order,
            )
            for c in crits
        ]
        result.append(
            EvaluationTemplateSchema(
                id=tpl.id,
                code=tpl.code,
                name=tpl.name,
                description=tpl.description,
                version=tpl.version,
                total_max_score=format_score(tpl.total_max_score),
                criteria_count=len(crits),
                criteria=crit_schemas,
            )
        )
    return result


# -------------------------------------------------------------
# Quản lý Chức vụ Cán bộ theo Học kỳ (Cadre Positions)
# -------------------------------------------------------------
@router.get("/users/{userId}/positions", response_model=List[UserPositionSchema])
def get_user_positions(
    userId: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == userId).first()
    if not user:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy người dùng.")

    positions = db.query(UserPosition).filter(UserPosition.user_id == userId).all()
    return [
        UserPositionSchema(
            id=p.id,
            user_id=p.user_id,
            term=p.term,
            position_title=p.position_title,
            organization=p.organization,
            is_confirmed=p.is_confirmed,
            confirmed_by=p.confirmed_by,
            created_at=format_datetime(p.created_at),
        )
        for p in positions
    ]


@router.post("/users/{userId}/positions", response_model=UserPositionSchema, dependencies=[Depends(verify_csrf)])
def add_user_position(
    userId: str,
    payload: CreateUserPositionRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    admin_user, _ = auth_data
    target_user = db.query(User).filter(User.id == userId).first()
    if not target_user:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy người dùng.")

    pos = UserPosition(
        user_id=userId,
        term=payload.term,
        position_title=payload.position_title,
        organization=payload.organization,
        is_confirmed=payload.is_confirmed,
        confirmed_by=admin_user.id if payload.is_confirmed else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)

    log_audit(
        db,
        campaign_id="SYSTEM",
        action="USER_CADRE_POSITION_CONFIRMED",
        actor_user_id=admin_user.id,
        after_json={
            "user_id": userId,
            "username": target_user.username,
            "position": pos.position_title,
            "org": pos.organization,
            "term": pos.term,
        },
    )

    return UserPositionSchema(
        id=pos.id,
        user_id=pos.user_id,
        term=pos.term,
        position_title=pos.position_title,
        organization=pos.organization,
        is_confirmed=pos.is_confirmed,
        confirmed_by=pos.confirmed_by,
        created_at=format_datetime(pos.created_at),
    )


# -------------------------------------------------------------
# Nhập / Đồng bộ Kết quả học tập Mục 4e có phân quyền & audit
# -------------------------------------------------------------
@router.post("/campaigns/{id}/academic-scores", response_model=ImportAcademicScoresResponse, dependencies=[Depends(verify_csrf)])
def import_academic_scores(
    id: str,
    payload: ImportAcademicScoresRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    admin_user, _ = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")

    crit_4e = db.query(Criterion).filter(Criterion.campaign_id == campaign.id, Criterion.code == "4e").first()
    if not crit_4e:
        raise AppError(status_code=400, code="CRITERION_NOT_FOUND", message="Đợt đánh giá này không có tiêu chí 4e.")

    now = datetime.now(timezone.utc)
    updated_count = 0
    details = []

    for item in payload.items:
        user = db.query(User).filter(User.username == item.student_code).first()
        if not user:
            details.append({"student_code": item.student_code, "status": "SKIPPED", "reason": "Không tìm thấy tài khoản"})
            continue

        case = db.query(Case).filter(Case.campaign_id == campaign.id, Case.student_id == user.id).first()
        if not case:
            details.append({"student_code": item.student_code, "status": "SKIPPED", "reason": "Chưa có hồ sơ trong đợt"})
            continue

        dec_gpa = Decimal(str(item.gpa)).quantize(Decimal("0.01"))
        converted_score = convert_gpa_to_score(dec_gpa)

        claim = db.query(Claim).filter(Claim.case_id == case.id, Claim.criterion_id == crit_4e.id).first()
        if not claim:
            claim = Claim(
                case_id=case.id,
                criterion_id=crit_4e.id,
                self_score=converted_score,
                academic_gpa=dec_gpa,
                student_note=f"Hệ thống quy đổi từ GPA {dec_gpa:.2f}",
                created_at=now,
            )
            db.add(claim)
        else:
            claim.academic_gpa = dec_gpa
            claim.self_score = converted_score
            claim.student_note = f"Hệ thống quy đổi từ GPA {dec_gpa:.2f}"
            claim.updated_at = now

        # Nếu case đang ở BCS_REVIEW và chưa duyệt 4e, tự động gán approved_score = converted_score
        if case.status == "BCS_REVIEW" and claim.approved_score is None:
            claim.approved_score = converted_score
            claim.bcs_reason = "Tự động đồng bộ theo kết quả học tập từ Nhà trường"

        # Cập nhật tổng claimed_total
        all_claims = db.query(Claim).filter(Claim.case_id == case.id).all()
        scores = [cl.self_score for cl in all_claims if cl.id != (claim.id or "")]
        scores.append(converted_score)
        case.claimed_total = sum_scores(scores)
        case.version += 1
        case.updated_at = now

        updated_count += 1
        details.append({
            "student_code": item.student_code,
            "status": "UPDATED",
            "gpa": float(dec_gpa),
            "converted_score": float(converted_score),
            "new_claimed_total": float(case.claimed_total),
        })

    db.commit()

    log_audit(
        db,
        campaign_id=campaign.id,
        action="ACADEMIC_SCORES_IMPORTED",
        actor_user_id=admin_user.id,
        after_json={"updated_count": updated_count, "details": details},
    )

    return ImportAcademicScoresResponse(updated_count=updated_count, details=details)


def _serialize_feedback_item(fb: BcsAiFeedback) -> BcsAiFeedbackItemSchema:
    return BcsAiFeedbackItemSchema(
        id=fb.id,
        evidence_file_id=fb.evidence_file_id,
        file_sha256=fb.file_sha256,
        file_version_no=fb.file_version_no,
        case_id=fb.case_id,
        criterion_id=fb.criterion_id,
        criterion_code=fb.criterion_code,
        bcs_decision=fb.bcs_decision,
        bcs_reason=fb.bcs_reason,
        reviewer_name=fb.reviewer.full_name if fb.reviewer else None,
        reviewed_at=format_datetime(fb.reviewed_at),
        ai_run_id=fb.ai_run_id,
        ai_model=fb.ai_model,
        ai_prompt_version=fb.ai_prompt_version,
        ai_verdict=fb.ai_verdict,
        ai_reason=fb.ai_reason,
        matching_status=fb.matching_status,
        discrepancy_status=fb.discrepancy_status,
        ground_truth_status=fb.ground_truth_status,
        ground_truth_label=fb.ground_truth_label,
        verification_reason=fb.verification_reason,
        verifier_name=fb.verifier.full_name if fb.verifier else None,
        verified_at=format_datetime(fb.verified_at) if fb.verified_at else None,
        created_at=format_datetime(fb.created_at),
        updated_at=format_datetime(fb.updated_at),
    )


def _serialize_feedback_detail(db: Session, fb: BcsAiFeedback) -> BcsAiFeedbackDetailSchema:
    item = _serialize_feedback_item(fb)
    file = fb.evidence_file
    audit_history = get_feedback_audit_history(db, fb.evidence_file_id)
    return BcsAiFeedbackDetailSchema(
        **item.model_dump(),
        ai_assessment=fb.ai_assessment_json,
        file_original_name=file.original_name if file else None,
        file_mime_type=file.mime_type if file else None,
        audit_history=audit_history,
    )


@router.get("/ai-feedback", response_model=AiFeedbackListResponse)
def list_ai_feedback(
    discrepancy_status: Optional[str] = None,
    ground_truth_status: Optional[str] = None,
    campaign_id: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    query = db.query(BcsAiFeedback)
    if campaign_id:
        query = query.join(Case, BcsAiFeedback.case_id == Case.id).filter(Case.campaign_id == campaign_id)
    if discrepancy_status:
        query = query.filter(BcsAiFeedback.discrepancy_status == discrepancy_status)
    if ground_truth_status:
        query = query.filter(BcsAiFeedback.ground_truth_status == ground_truth_status)

    total = query.count()
    items = (
        query.order_by(BcsAiFeedback.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return AiFeedbackListResponse(
        items=[_serialize_feedback_item(fb) for fb in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/ai-feedback-metrics", response_model=AiFeedbackMetricsResponse)
def get_ai_feedback_metrics_endpoint(
    campaign_id: Optional[str] = None,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    metrics = calculate_ai_feedback_metrics(db, campaign_id=campaign_id)
    return AiFeedbackMetricsResponse(**metrics)


@router.get("/ai-feedback/{feedback_id}", response_model=BcsAiFeedbackDetailSchema)
def get_ai_feedback_detail(
    feedback_id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    fb = db.query(BcsAiFeedback).filter(BcsAiFeedback.id == feedback_id).first()
    if not fb:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy bản ghi phản hồi.")
    return _serialize_feedback_detail(db, fb)


@router.post("/ai-feedback/{feedback_id}/verify", response_model=BcsAiFeedbackDetailSchema, dependencies=[Depends(verify_csrf)])
def verify_feedback_ground_truth(
    feedback_id: str,
    payload: VerifyGroundTruthRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    user, _ = auth_data
    fb = verify_ground_truth(
        db,
        feedback_id=feedback_id,
        ground_truth_label=payload.ground_truth_label,
        reason=payload.reason,
        user_id=user.id,
    )
    return _serialize_feedback_detail(db, fb)


@router.get("/files/{fileId}")
def get_admin_evidence_file(
    fileId: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == fileId).first()
    if not ev:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy tệp minh chứng.")

    if remote_storage_enabled():
        return RedirectResponse(url=create_download_url(ev.storage_key), status_code=307)

    file_path = get_file_path(ev.storage_key)
    return FileResponse(
        path=file_path,
        media_type=ev.mime_type,
        filename=ev.original_name,
    )
