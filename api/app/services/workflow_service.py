from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from api.app.models.entities import (
    Campaign,
    Criterion,
    Case,
    Claim,
    EvidenceFile,
    BcsEvidenceDecision,
    SupplementRequest,
    Meeting,
    Appeal,
    ScoreSnapshot,
    ClassMember,
    User,
)
from api.app.review.provider import ManualReviewProvider
from api.app.schemas.common import AppError, format_score
from api.app.services.audit_service import log_audit
from api.app.services.notification_service import send_notification
from api.app.services.scoring_service import parse_score, validate_score_bounds, sum_scores
from api.app.services.evidence_decision_service import required_evidence_file_ids
from api.app.services.draft_review_service import draft_review_status


def initialize_campaign_cases(db: Session, campaign: Campaign):
    students = (
        db.query(ClassMember)
        .filter(ClassMember.class_id == campaign.class_id, ClassMember.member_role == "STUDENT")
        .all()
    )
    criteria = db.query(Criterion).filter(Criterion.campaign_id == campaign.id).order_by(Criterion.sort_order).all()

    for st in students:
        existing_case = (
            db.query(Case)
            .filter(Case.campaign_id == campaign.id, Case.student_id == st.user_id)
            .first()
        )
        if not existing_case:
            new_case = Case(
                campaign_id=campaign.id,
                student_id=st.user_id,
                status="DRAFT",
                version=1,
                info_round=0,
                proof_round=0,
                created_at=datetime.now(timezone.utc),
            )
            db.add(new_case)
            db.flush()

            for crit in criteria:
                claim = Claim(
                    case_id=new_case.id,
                    criterion_id=crit.id,
                    self_score=None,
                    student_note=None,
                    approved_score=None,
                    bcs_reason=None,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(claim)


def open_campaign(db: Session, campaign: Campaign, actor_user_id: Optional[str], now: datetime):
    if campaign.status != "DRAFT":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể lên lịch hoặc mở đợt khi đang ở trạng thái DRAFT (hiện tại: {campaign.status})."
        )

    # Convert open_at to utc-aware for comparison if naive
    open_at = campaign.open_at
    if open_at.tzinfo is None:
        open_at = open_at.replace(tzinfo=timezone.utc)

    if open_at > now:
        campaign.status = "SCHEDULED"
        log_audit(db, campaign_id=campaign.id, action="CAMPAIGN_SCHEDULED", actor_user_id=actor_user_id)
    else:
        campaign.status = "OPEN"
        campaign.opened_at = now
        initialize_campaign_cases(db, campaign)
        log_audit(db, campaign_id=campaign.id, action="CAMPAIGN_OPENED", actor_user_id=actor_user_id)


def submit_student_case(
    db: Session,
    case: Case,
    actor_user: User,
    expected_version: int,
    now: datetime,
) -> Tuple[Case, List[str]]:
    if case.student_id != actor_user.id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn chỉ có thể nộp hồ sơ của chính mình.")

    if case.version != expected_version:
        raise AppError(
            status_code=409,
            code="CASE_CHANGED",
            message="Hồ sơ đã thay đổi, vui lòng tải lại trước khi nộp."
        )

    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    if not campaign:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy đợt đánh giá.")

    if campaign.status != "OPEN":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message="Đợt đánh giá hiện không mở để nhận nộp hồ sơ."
        )

    deadline = campaign.submission_deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if now > deadline and case.status == "DRAFT":
        raise AppError(
            status_code=422,
            code="DEADLINE_EXPIRED",
            message="Đã hết hạn nộp hồ sơ tự đánh giá."
        )

    if case.status not in ["DRAFT", "NEEDS_INFO", "NEEDS_PROOF"]:
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Không thể nộp hồ sơ khi đang ở trạng thái {case.status}."
        )

    # Check that all criteria have self_score
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    criteria_map = {
        c.id: c
        for c in db.query(Criterion).filter(Criterion.campaign_id == campaign.id).all()
    }

    missing_items = []
    claimed_scores = []

    for cl in claims:
        crit = criteria_map.get(cl.criterion_id)
        if not crit:
            continue
        is_system_criterion = crit.code == "4e" or (crit.allowed_input_roles and "STUDENT" not in crit.allowed_input_roles)
        if cl.self_score is None:
            if is_system_criterion:
                # 4e do Nhà trường quy đổi, sinh viên chưa có điểm vẫn cho phép nộp
                pass
            else:
                raise AppError(
                    status_code=422,
                    code="MISSING_SELF_SCORE",
                    message=f"Vui lòng tự chấm điểm cho tiêu chí {crit.code} - {crit.title} trước khi nộp."
                )
        else:
            validate_score_bounds(cl.self_score, crit.max_score, field_name=crit.code)
            claimed_scores.append(cl.self_score)

        if crit.requires_evidence and cl.self_score is not None and cl.self_score > 0:
            has_evidence = (
                db.query(EvidenceFile)
                .filter(EvidenceFile.claim_id == cl.id, EvidenceFile.is_current.is_(True))
                .first()
            )
            if not has_evidence:
                missing_items.append(f"{crit.code}: {crit.title}")

    case.claimed_total = sum_scores(claimed_scores)

    # Structural check
    if missing_items:
        if case.info_round < campaign.max_info_rounds:
            case.info_round += 1
            case.status = "NEEDS_INFO"
            supp_deadline = now + timedelta(hours=campaign.supplement_period_hours)
            supp_req = SupplementRequest(
                case_id=case.id,
                kind="INFO",
                round_no=case.info_round,
                reason=f"Hồ sơ thiếu minh chứng bắt buộc cho: {'; '.join(missing_items)}",
                requested_by=None,
                requested_at=now,
                deadline_at=supp_deadline,
            )
            db.add(supp_req)
            send_notification(
                db,
                user_id=case.student_id,
                type="NEEDS_INFO",
                title="Yêu cầu bổ sung thông tin hồ sơ",
                body=f"Hồ sơ của bạn thiếu minh chứng bắt buộc ({'; '.join(missing_items)}). Vui lòng bổ sung trước hạn {supp_deadline.strftime('%d/%m/%Y %H:%M')}.",
                case_id=case.id,
                dedup_key=f"needs_info_{case.id}_{case.info_round}",
            )
        else:
            case.status = "CLOSED_INCOMPLETE"
            send_notification(
                db,
                user_id=case.student_id,
                type="CLOSED_INCOMPLETE",
                title="Hồ sơ đã đóng do không hoàn tất",
                body="Hồ sơ của bạn đã quá số lần bổ sung thông tin và được đánh dấu không hoàn tất.",
                case_id=case.id,
                dedup_key=f"closed_incomplete_{case.id}",
            )
    else:
        # Review Provider evaluates
        review_result = ManualReviewProvider().review(case.id)
        case.status = "BCS_REVIEW"

        # Fulfill any open supplement requests
        open_requests = (
            db.query(SupplementRequest)
            .filter(SupplementRequest.case_id == case.id, SupplementRequest.fulfilled_at.is_(None))
            .all()
        )
        for req in open_requests:
            req.fulfilled_at = now

    if case.submitted_at is None:
        case.submitted_at = now
    case.version += 1

    log_audit(
        db,
        campaign_id=campaign.id,
        case_id=case.id,
        action="CASE_SUBMITTED",
        actor_user_id=actor_user.id,
        after_json={"status": case.status, "version": case.version, "missing_items": missing_items},
    )

    return case, missing_items


def complete_bcs_case_review(
    db: Session,
    case: Case,
    actor_user: User,
    expected_version: int,
    now: datetime,
) -> Case:
    if case.version != expected_version:
        raise AppError(
            status_code=409,
            code="CASE_CHANGED",
            message="Hồ sơ đã thay đổi, vui lòng tải lại."
        )

    if case.status != "BCS_REVIEW":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Không thể hoàn tất kiểm tra hồ sơ ở trạng thái {case.status} (yêu cầu BCS_REVIEW)."
        )

    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    criteria_map = {
        c.id: c
        for c in db.query(Criterion).filter(Criterion.campaign_id == campaign.id).all()
    }

    required_files = required_evidence_file_ids(db, case)
    decisions = {
        item.evidence_file_id: item.decision
        for item in db.query(BcsEvidenceDecision)
        .filter(BcsEvidenceDecision.evidence_file_id.in_(required_files)).all()
    } if required_files else {}
    unresolved = required_files - {file_id for file_id, decision in decisions.items()
                                   if decision in {"ACCEPT", "REJECT_ITEM"}}
    if unresolved:
        raise AppError(
            status_code=422,
            code="EVIDENCE_DECISION_REQUIRED",
            message=f"Còn {len(unresolved)} minh chứng được gắn cờ hoặc đã phân tích AI chưa có quyết định cuối cùng của BCS. Hãy chấp nhận hoặc từ chối từng tệp trước khi hoàn tất.",
            fields={"evidence_file_ids": ",".join(sorted(unresolved))},
        )

    approved_scores = []
    current_evidence = (db.query(EvidenceFile).join(Claim, EvidenceFile.claim_id == Claim.id)
                        .filter(Claim.case_id == case.id, EvidenceFile.is_current.is_(True)).all())
    evidence_by_claim = {}
    for file in current_evidence:
        evidence_by_claim.setdefault(file.claim_id, []).append(file)
    all_decisions = {
        item.evidence_file_id: item.decision
        for item in db.query(BcsEvidenceDecision)
        .filter(BcsEvidenceDecision.evidence_file_id.in_([file.id for file in current_evidence])).all()
    } if current_evidence else {}
    for cl in claims:
        crit = criteria_map.get(cl.criterion_id)
        if not crit:
            continue
        if cl.approved_score is None:
            raise AppError(
                status_code=422,
                code="UNREVIEWED_CRITERIA",
                message=f"Chưa chấm điểm duyệt cho tiêu chí {crit.code} - {crit.title}."
            )
        validate_score_bounds(cl.approved_score, crit.max_score, field_name=crit.code)
        if (crit.requires_evidence and cl.approved_score > 0
                and evidence_by_claim.get(cl.id)
                and all(all_decisions.get(file.id) == "REJECT_ITEM"
                        for file in evidence_by_claim[cl.id])):
            raise AppError(status_code=422, code="REJECTED_EVIDENCE_WITH_POSITIVE_SCORE",
                           message=f"Tiêu chí {crit.code} có toàn bộ minh chứng bị BCS từ chối. Hãy chỉnh điểm duyệt về 0 hoặc xem lại quyết định minh chứng.")
        
        # Reason mandatory if approved_score != self_score
        if cl.self_score is not None and cl.approved_score != cl.self_score:
            if not cl.bcs_reason or not cl.bcs_reason.strip():
                raise AppError(
                    status_code=422,
                    code="REASON_REQUIRED",
                    message=f"Bắt buộc nhập lý do khi điểm duyệt ({cl.approved_score}) khác điểm tự khai ({cl.self_score}) ở tiêu chí {crit.code}."
                )
        approved_scores.append(cl.approved_score)

    # Validate section caps if configured
    section_scores_map = {}
    for cl in claims:
        crit = criteria_map.get(cl.criterion_id)
        if crit and crit.section_code and crit.section_max_score:
            section_scores_map.setdefault(crit.section_code, {"max": crit.section_max_score, "title": crit.section_title, "scores": []})
            section_scores_map[crit.section_code]["scores"].append(cl.approved_score)

    for sec_code, sec_info in section_scores_map.items():
        sec_sum = sum_scores(sec_info["scores"])
        if sec_sum > sec_info["max"]:
            raise AppError(
                status_code=422,
                code="SECTION_SCORE_OUT_OF_BOUNDS",
                message=f"Tổng điểm duyệt của mục '{sec_info['title'] or sec_code}' đạt {sec_sum:.2f}, vượt quá mức tối đa {sec_info['max']:.2f} điểm.",
                fields={sec_code: f"Tối đa {sec_info['max']:.2f} điểm"}
            )

    case.proposed_total = sum_scores(approved_scores)
    if case.proposed_total > Decimal("100.00") and any(c.section_code for c in criteria_map.values()):
        raise AppError(
            status_code=422,
            code="TOTAL_SCORE_OUT_OF_BOUNDS",
            message=f"Tổng điểm đề xuất của lớp ({case.proposed_total:.2f}) không được vượt quá 100.00 điểm.",
            fields={"proposed_total": "Tối đa 100.00 điểm"}
        )
    case.status = "PROPOSED"
    case.version += 1

    log_audit(
        db,
        campaign_id=campaign.id,
        case_id=case.id,
        action="BCS_REVIEW_COMPLETED",
        actor_user_id=actor_user.id,
        after_json={"status": case.status, "proposed_total": str(case.proposed_total)},
    )
    return case


def publish_campaign(
    db: Session,
    campaign: Campaign,
    actor_user: User,
    expected_status: Optional[str],
    now: datetime,
) -> Campaign:
    if expected_status and campaign.status != expected_status:
        raise AppError(
            status_code=409,
            code="CAMPAIGN_CHANGED",
            message=f"Đợt đánh giá đã thay đổi trạng thái (hiện tại: {campaign.status}, mong đợi: {expected_status})."
        )

    if campaign.status not in ["OPEN", "REVIEW"]:
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể công bố khi đợt ở trạng thái REVIEW hoặc OPEN (hiện tại: {campaign.status})."
        )

    # Check meetings: BCS and CLASS meetings must exist
    meetings = db.query(Meeting).filter(Meeting.campaign_id == campaign.id).all()
    meeting_kinds = {m.kind for m in meetings}
    if not ("BCS" in meeting_kinds and "CLASS" in meeting_kinds):
        raise AppError(
            status_code=422,
            code="MEETINGS_INCOMPLETE",
            message="Chưa đủ biên bản họp BCS và họp Lớp để công bố kết quả."
        )
    if not draft_review_status(db, campaign)["reviewed"]:
        raise AppError(status_code=422, code="DRAFT_REVIEW_REQUIRED", message="BCS chưa xác nhận bản dự thảo hiện hành sau họp BCS.")

    # Check all cases in campaign: must be PROPOSED or CLOSED_*
    cases = db.query(Case).filter(Case.campaign_id == campaign.id).all()
    for c in cases:
        if c.status not in ["PROPOSED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"]:
            raise AppError(
                status_code=422,
                code="CASES_NOT_READY",
                message=f"Vẫn còn hồ sơ chưa hoàn tất kiểm tra điểm dự kiến (Hồ sơ {c.id} ở trạng thái {c.status})."
            )

    appeal_deadline = now + timedelta(hours=campaign.appeal_period_hours)
    campaign.status = "PUBLISHED"
    campaign.published_at = now

    criteria_list = db.query(Criterion).filter(Criterion.campaign_id == campaign.id).order_by(Criterion.sort_order).all()

    for c in cases:
        if c.status == "PROPOSED":
            c.status = "PUBLISHED"
            c.published_at = now
            c.appeal_deadline_at = appeal_deadline

            # Build immutable snapshot
            claims = db.query(Claim).filter(Claim.case_id == c.id).all()
            claims_dict = {cl.criterion_id: cl for cl in claims}
            snapshot_items = []
            for crit in criteria_list:
                cl = claims_dict.get(crit.id)
                snapshot_items.append({
                    "criterion_id": crit.id,
                    "code": crit.code,
                    "title": crit.title,
                    "max_score": format_score(crit.max_score),
                    "self_score": format_score(cl.self_score if cl else None),
                    "approved_score": format_score(cl.approved_score if cl else None),
                    "bcs_reason": cl.bcs_reason if cl else None,
                })

            existing_snap = (
                db.query(ScoreSnapshot)
                .filter(ScoreSnapshot.case_id == c.id, ScoreSnapshot.kind == "PUBLISHED")
                .first()
            )
            if not existing_snap:
                snap = ScoreSnapshot(
                    case_id=c.id,
                    kind="PUBLISHED",
                    per_criterion_json=snapshot_items,
                    total=c.proposed_total or Decimal("0.00"),
                    created_by=actor_user.id,
                    created_at=now,
                )
                db.add(snap)

            send_notification(
                db,
                user_id=c.student_id,
                type="PUBLISHED",
                title="Điểm rèn luyện dự kiến đã được công bố",
                body=f"Điểm rèn luyện dự kiến của bạn là {c.proposed_total:.2f}. Hạn phản hồi/khiếu nại đến {appeal_deadline.strftime('%d/%m/%Y %H:%M')}.",
                case_id=c.id,
                dedup_key=f"published_{c.id}",
            )

    log_audit(
        db,
        campaign_id=campaign.id,
        action="CAMPAIGN_PUBLISHED",
        actor_user_id=actor_user.id,
        after_json={"status": "PUBLISHED", "appeal_deadline_at": appeal_deadline.isoformat()},
    )
    return campaign


def finalize_campaign(
    db: Session,
    campaign: Campaign,
    actor_user: User,
    now: datetime,
) -> Campaign:
    if campaign.status != "PUBLISHED":
        raise AppError(
            status_code=409,
            code="INVALID_STATE",
            message=f"Chỉ có thể chốt điểm khi đợt ở trạng thái PUBLISHED (hiện tại: {campaign.status})."
        )

    cases = db.query(Case).filter(Case.campaign_id == campaign.id).all()
    for c in cases:
        if c.status not in ["ACCEPTED", "ACCEPTED_AUTO", "RESOLVED", "CLOSED_INCOMPLETE", "CLOSED_NO_SUBMIT"]:
            raise AppError(
                status_code=422,
                code="CASES_NOT_FINALIZABLE",
                message=f"Còn hồ sơ chưa được phản hồi hoặc chưa xử lý xong khiếu nại (Hồ sơ {c.id} ở trạng thái {c.status})."
            )

    campaign.status = "FINALIZED"
    campaign.finalized_at = now

    criteria_list = db.query(Criterion).filter(Criterion.campaign_id == campaign.id).order_by(Criterion.sort_order).all()

    for c in cases:
        if c.status in ["ACCEPTED", "ACCEPTED_AUTO", "RESOLVED"]:
            c.status = "FINALIZED"
            c.final_total = c.proposed_total

            claims = db.query(Claim).filter(Claim.case_id == c.id).all()
            claims_dict = {cl.criterion_id: cl for cl in claims}
            snapshot_items = []
            for crit in criteria_list:
                cl = claims_dict.get(crit.id)
                snapshot_items.append({
                    "criterion_id": crit.id,
                    "code": crit.code,
                    "title": crit.title,
                    "max_score": format_score(crit.max_score),
                    "self_score": format_score(cl.self_score if cl else None),
                    "approved_score": format_score(cl.approved_score if cl else None),
                    "bcs_reason": cl.bcs_reason if cl else None,
                })

            existing_snap = (
                db.query(ScoreSnapshot)
                .filter(ScoreSnapshot.case_id == c.id, ScoreSnapshot.kind == "FINAL")
                .first()
            )
            if not existing_snap:
                snap = ScoreSnapshot(
                    case_id=c.id,
                    kind="FINAL",
                    per_criterion_json=snapshot_items,
                    total=c.final_total or Decimal("0.00"),
                    created_by=actor_user.id,
                    created_at=now,
                )
                db.add(snap)

    log_audit(
        db,
        campaign_id=campaign.id,
        action="CAMPAIGN_FINALIZED",
        actor_user_id=actor_user.id,
        after_json={"status": "FINALIZED", "finalized_at": now.isoformat()},
    )
    return campaign
