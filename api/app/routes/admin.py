from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import Campaign, Criterion, Class, User
from api.app.schemas import (
    CreateCampaignRequest,
    CampaignSchema,
    CriterionSchema,
    OpenCampaignResponse,
    AppError,
    format_datetime,
    format_score,
)
from api.app.services.auth_service import require_roles, verify_csrf
from api.app.services.workflow_service import open_campaign
from api.app.services.audit_service import log_audit
from api.app.services.scoring_service import parse_score

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
        raise AppError(status_code=422, code="CRITERIA_REQUIRED", message="Đợt đánh giá phải có ít nhất 1 tiêu chí.")

    seen_codes = set()
    for crit in payload.criteria:
        if crit.code in seen_codes:
            raise AppError(status_code=422, code="DUPLICATE_CRITERION_CODE", message=f"Mã tiêu chí '{crit.code}' bị trùng lặp.")
        seen_codes.add(crit.code)
        parse_score(crit.max_score)

    return open_at, sub_dl


@router.post("/campaigns", response_model=CampaignSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def create_campaign(
    payload: CreateCampaignRequest,
    auth_data: tuple[User, list[str]] = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    admin_user, _ = auth_data
    open_at, sub_dl = _validate_campaign_config(payload, db)

    now = datetime.now(timezone.utc)
    campaign = Campaign(
        class_id=payload.class_id,
        title=payload.title,
        term=payload.term,
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
            title=crit_in.title,
            description=crit_in.description,
            max_score=parse_score(crit_in.max_score),
            requires_evidence=crit_in.requires_evidence,
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
        after_json={"title": campaign.title, "term": campaign.term},
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

    open_at, sub_dl = _validate_campaign_config(payload, db)

    now = datetime.now(timezone.utc)
    campaign.class_id = payload.class_id
    campaign.title = payload.title
    campaign.term = payload.term
    campaign.open_at = open_at
    campaign.submission_deadline_at = sub_dl
    campaign.supplement_period_hours = payload.supplement_period_hours
    campaign.appeal_period_hours = payload.appeal_period_hours
    campaign.reminder_after_hours = payload.reminder_after_hours
    campaign.max_info_rounds = payload.max_info_rounds
    campaign.max_proof_rounds = payload.max_proof_rounds
    campaign.updated_at = now

    # Remove old criteria and insert updated criteria
    db.query(Criterion).filter(Criterion.campaign_id == campaign.id).delete()
    criteria_list = []
    for crit_in in payload.criteria:
        crit = Criterion(
            campaign_id=campaign.id,
            code=crit_in.code,
            title=crit_in.title,
            description=crit_in.description,
            max_score=parse_score(crit_in.max_score),
            requires_evidence=crit_in.requires_evidence,
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
