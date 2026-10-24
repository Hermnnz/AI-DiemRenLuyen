import csv
import io
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import Campaign, Criterion, Case, User, ClassMember
from api.app.schemas import AppError, format_score, format_datetime, CampaignSchema, CriterionSchema
from api.app.services.auth_service import require_roles

router = APIRouter(prefix="/gvcn", tags=["GVCN"])


@router.get("/campaigns/active", response_model=CampaignSchema)
def get_gvcn_active_campaign(
    auth_data: tuple[User, list[str]] = Depends(require_roles("GVCN")),
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
            title=c.title,
            description=c.description,
            max_score=format_score(c.max_score),
            requires_evidence=c.requires_evidence,
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
        open_at=format_datetime(campaign.open_at),
        submission_deadline_at=format_datetime(campaign.submission_deadline_at),
        supplement_period_hours=campaign.supplement_period_hours,
        appeal_period_hours=campaign.appeal_period_hours,
        reminder_after_hours=campaign.reminder_after_hours,
        max_info_rounds=campaign.max_info_rounds,
        max_proof_rounds=campaign.max_proof_rounds,
        criteria=crit_schemas,
    )


@router.get("/campaigns/{id}/final-scores.csv")
def download_final_scores_csv(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("GVCN")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")

    if campaign.class_id not in class_ids:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không phải GVCN của lớp này.")

    if campaign.status != "FINALIZED":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message="Chỉ có thể tải bảng điểm chính thức sau khi đợt đánh giá đã chốt hoàn tất (FINALIZED)."
        )

    cases = (
        db.query(Case, User)
        .join(User, Case.student_id == User.id)
        .filter(Case.campaign_id == campaign.id)
        .order_by(User.username.asc())
        .all()
    )

    output = io.StringIO()
    # Write UTF-8 BOM
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "Mã sinh viên",
        "Họ và tên",
        "Trạng thái hồ sơ",
        "Điểm tự khai",
        "Điểm dự kiến",
        "Điểm chốt chính thức",
        "Ghi chú",
    ])

    for c, u in cases:
        note = ""
        if c.status == "CLOSED_NO_SUBMIT":
            note = "Không nộp hồ sơ"
        elif c.status == "CLOSED_INCOMPLETE":
            note = "Hồ sơ không hoàn tất bổ sung"
        elif c.acceptance_source == "TIMEOUT":
            note = "Tự động chấp thuận sau hạn khiếu nại"
        elif c.acceptance_source == "EXPLICIT":
            note = "Sinh viên đã đồng ý"

        writer.writerow([
            u.username,
            u.full_name,
            c.status,
            format_score(c.claimed_total) or "0.00",
            format_score(c.proposed_total) or "0.00",
            format_score(c.final_total) or "0.00",
            note,
        ])

    csv_content = output.getvalue()
    filename = f"bang-diem-ren-luyen-{campaign.term}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
