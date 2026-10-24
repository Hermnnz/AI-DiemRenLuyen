from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from api.app.models.entities import Campaign, Case, SupplementRequest, ClassMember
from api.app.services.workflow_service import initialize_campaign_cases
from api.app.services.notification_service import send_notification
from api.app.services.audit_service import log_audit


def run_deadline_tick(db: Session, target_time: datetime) -> Dict[str, Any]:
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    stats = {
        "opened_campaigns": 0,
        "reviewed_campaigns": 0,
        "closed_no_submit_cases": 0,
        "closed_incomplete_cases": 0,
        "returned_bcs_review_cases": 0,
        "reminded_cases": 0,
        "auto_accepted_cases": 0,
    }

    # 1. SCHEDULED -> OPEN
    scheduled_campaigns = db.query(Campaign).filter(Campaign.status == "SCHEDULED").all()
    for camp in scheduled_campaigns:
        camp_open_at = camp.open_at.replace(tzinfo=timezone.utc) if camp.open_at.tzinfo is None else camp.open_at
        if camp_open_at <= target_time:
            camp.status = "OPEN"
            camp.opened_at = target_time
            initialize_campaign_cases(db, camp)
            log_audit(db, campaign_id=camp.id, action="CAMPAIGN_OPENED_BY_TICK")
            stats["opened_campaigns"] += 1

    # 2. OPEN -> REVIEW (or all cases submitted/closed)
    open_campaigns = db.query(Campaign).filter(Campaign.status == "OPEN").all()
    for camp in open_campaigns:
        camp_sub_deadline = (
            camp.submission_deadline_at.replace(tzinfo=timezone.utc)
            if camp.submission_deadline_at.tzinfo is None
            else camp.submission_deadline_at
        )
        if camp_sub_deadline <= target_time:
            camp.status = "REVIEW"
            stats["reviewed_campaigns"] += 1

            # Transition any remaining DRAFT cases to CLOSED_NO_SUBMIT
            draft_cases = db.query(Case).filter(Case.campaign_id == camp.id, Case.status == "DRAFT").all()
            for dc in draft_cases:
                dc.status = "CLOSED_NO_SUBMIT"
                dc.version += 1
                stats["closed_no_submit_cases"] += 1
                send_notification(
                    db,
                    user_id=dc.student_id,
                    type="CLOSED_NO_SUBMIT",
                    title="Đã hết hạn nộp hồ sơ",
                    body="Đợt đánh giá đã kết thúc thời gian nộp hồ sơ. Hồ sơ của bạn đã được đóng do chưa nộp.",
                    case_id=dc.id,
                    dedup_key=f"closed_no_submit_{dc.id}",
                )
                log_audit(db, campaign_id=camp.id, case_id=dc.id, action="CASE_CLOSED_NO_SUBMIT")

    # 3. NEEDS_INFO timeouts -> CLOSED_INCOMPLETE
    needs_info_cases = db.query(Case).filter(Case.status == "NEEDS_INFO").all()
    for c in needs_info_cases:
        pending_req = (
            db.query(SupplementRequest)
            .filter(
                SupplementRequest.case_id == c.id,
                SupplementRequest.kind == "INFO",
                SupplementRequest.fulfilled_at.is_(None)
            )
            .first()
        )
        if pending_req:
            req_dl = (
                pending_req.deadline_at.replace(tzinfo=timezone.utc)
                if pending_req.deadline_at.tzinfo is None
                else pending_req.deadline_at
            )
            if req_dl <= target_time:
                c.status = "CLOSED_INCOMPLETE"
                c.version += 1
                stats["closed_incomplete_cases"] += 1
                send_notification(
                    db,
                    user_id=c.student_id,
                    type="CLOSED_INCOMPLETE",
                    title="Hồ sơ đã đóng do quá hạn bổ sung",
                    body="Đã quá thời hạn bổ sung thông tin. Hồ sơ của bạn được đóng ở trạng thái không hoàn tất.",
                    case_id=c.id,
                    dedup_key=f"closed_incomplete_timeout_{c.id}_{pending_req.id}",
                )
                log_audit(db, campaign_id=c.campaign_id, case_id=c.id, action="CASE_CLOSED_INCOMPLETE_TIMEOUT")

    # 4. NEEDS_PROOF timeouts -> BCS_REVIEW
    needs_proof_cases = db.query(Case).filter(Case.status == "NEEDS_PROOF").all()
    for c in needs_proof_cases:
        pending_req = (
            db.query(SupplementRequest)
            .filter(
                SupplementRequest.case_id == c.id,
                SupplementRequest.kind == "PROOF",
                SupplementRequest.fulfilled_at.is_(None)
            )
            .first()
        )
        if pending_req:
            req_dl = (
                pending_req.deadline_at.replace(tzinfo=timezone.utc)
                if pending_req.deadline_at.tzinfo is None
                else pending_req.deadline_at
            )
            if req_dl <= target_time:
                c.status = "BCS_REVIEW"
                c.version += 1
                pending_req.fulfilled_at = target_time
                stats["returned_bcs_review_cases"] += 1
                send_notification(
                    db,
                    user_id=c.student_id,
                    type="NEEDS_PROOF_TIMEOUT",
                    title="Hết hạn bổ sung minh chứng",
                    body="Đã hết thời hạn bổ sung minh chứng. Ban cán sự sẽ đánh giá dựa trên các minh chứng hiện có.",
                    case_id=c.id,
                    dedup_key=f"needs_proof_timeout_{c.id}_{pending_req.id}",
                )
                log_audit(db, campaign_id=c.campaign_id, case_id=c.id, action="CASE_NEEDS_PROOF_TIMEOUT_RETURN_BCS")

    # 5 & 6. PUBLISHED cases: Reminders & ACCEPTED_AUTO
    published_cases = db.query(Case).filter(Case.status == "PUBLISHED").all()
    for c in published_cases:
        camp = db.query(Campaign).filter(Campaign.id == c.campaign_id).first()
        if not camp or not c.published_at or not c.appeal_deadline_at:
            continue

        pub_at = c.published_at.replace(tzinfo=timezone.utc) if c.published_at.tzinfo is None else c.published_at
        app_dl = c.appeal_deadline_at.replace(tzinfo=timezone.utc) if c.appeal_deadline_at.tzinfo is None else c.appeal_deadline_at

        reminder_at = pub_at + timedelta(hours=camp.reminder_after_hours)
        if reminder_at <= target_time < app_dl:
            # Send reminder notification (idempotent via dedup_key)
            notif = send_notification(
                db,
                user_id=c.student_id,
                type="APPEAL_REMINDER",
                title="Nhắc hạn phản hồi điểm rèn luyện",
                body=f"Bạn còn thời gian đến {app_dl.strftime('%d/%m/%Y %H:%M')} để xác nhận hoặc khiếu nại điểm rèn luyện dự kiến.",
                case_id=c.id,
                dedup_key=f"appeal_reminder_{c.id}",
            )
            if notif:
                stats["reminded_cases"] += 1

        if app_dl <= target_time:
            c.status = "ACCEPTED_AUTO"
            c.acceptance_source = "TIMEOUT"
            c.version += 1
            stats["auto_accepted_cases"] += 1
            send_notification(
                db,
                user_id=c.student_id,
                type="ACCEPTED_AUTO",
                title="Điểm rèn luyện đã được tự động chấp nhận",
                body="Đã hết thời hạn phản hồi/khiếu nại. Điểm rèn luyện dự kiến đã được tự động ghi nhận là đồng ý.",
                case_id=c.id,
                dedup_key=f"accepted_auto_{c.id}",
            )
            log_audit(db, campaign_id=c.campaign_id, case_id=c.id, action="CASE_ACCEPTED_AUTO")

    db.commit()
    return stats
