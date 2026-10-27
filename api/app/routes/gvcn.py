import csv
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from api.app.database import get_db
from api.app.models.entities import Campaign, Criterion, Case, User, ClassMember, FinalHandoff
from api.app.schemas import AppError, format_score, format_datetime, CampaignSchema, CriterionSchema, FinalHandoffSchema
from api.app.services.auth_service import require_roles, verify_csrf
from api.app.services.scoring_service import get_rating
from api.app.services.audit_service import log_audit
from api.app.services.final_handoff_service import final_score_fingerprint, handoff_status

router = APIRouter(prefix="/gvcn", tags=["GVCN"])


def _campaign_for_gvcn(db: Session, campaign_id: str, class_ids: list[str]) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")
    if campaign.class_id not in class_ids:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không phải GVCN của lớp này.")
    return campaign


@router.get("/campaigns/{id}/handoff", response_model=FinalHandoffSchema)
def get_final_handoff(id: str, auth_data: tuple[User, list[str]] = Depends(require_roles("GVCN")), db: Session = Depends(get_db)):
    _, class_ids = auth_data
    _campaign_for_gvcn(db, id, class_ids)
    return FinalHandoffSchema(**handoff_status(db.query(FinalHandoff).filter(FinalHandoff.campaign_id == id).first()))


@router.post("/campaigns/{id}/handoff/receive", response_model=FinalHandoffSchema, dependencies=[Depends(verify_csrf)])
def receive_final_handoff(id: str, auth_data: tuple[User, list[str]] = Depends(require_roles("GVCN")), db: Session = Depends(get_db)):
    user, class_ids = auth_data
    campaign = _campaign_for_gvcn(db, id, class_ids)
    handoff = db.query(FinalHandoff).filter(FinalHandoff.campaign_id == id).with_for_update().first()
    if not handoff:
        raise AppError(status_code=409, code="HANDOFF_NOT_SENT", message="BCS chưa gửi bảng điểm chính thức cho GVCN.")
    if handoff.snapshot_sha256 != final_score_fingerprint(db, campaign):
        raise AppError(status_code=409, code="SNAPSHOT_CHANGED", message="Bảng điểm đã thay đổi sau khi gửi. Hãy liên hệ BCS để kiểm tra.")
    if not handoff.received_at:
        handoff.received_at = datetime.now(timezone.utc)
        handoff.received_by = user.id
        log_audit(db, campaign_id=id, action="FINAL_SCORES_RECEIVED_BY_GVCN", actor_user_id=user.id,
                  after_json={"snapshot_sha256": handoff.snapshot_sha256, "received_at": handoff.received_at.isoformat()})
        db.commit()
    return FinalHandoffSchema(**handoff_status(handoff))


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


@router.get("/campaigns/{id}/final-scores.csv")
def download_final_scores_csv(
    id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("GVCN")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    campaign = _campaign_for_gvcn(db, id, class_ids)

    if campaign.status != "FINALIZED":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message="Chỉ có thể tải bảng điểm chính thức sau khi đợt đánh giá đã chốt hoàn tất (FINALIZED)."
        )

    handoff = db.query(FinalHandoff).filter(FinalHandoff.campaign_id == id).first()
    if not handoff:
        raise AppError(status_code=409, code="HANDOFF_NOT_SENT", message="BCS chưa gửi bảng điểm chính thức cho GVCN.")
    if handoff.snapshot_sha256 != final_score_fingerprint(db, campaign):
        raise AppError(status_code=409, code="SNAPSHOT_CHANGED", message="Bảng điểm đã thay đổi sau khi gửi. Hãy liên hệ BCS để kiểm tra.")

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
        "Xếp loại tham khảo",
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
            get_rating(c.final_total) or "",
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
