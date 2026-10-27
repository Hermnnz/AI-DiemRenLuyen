from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.app.database import get_db
from api.app.models.entities import AiReviewRun, Campaign, Case, User
from api.app.schemas.ai_reviews import AiLatestResponse, AiReviewResponse, RuleCheckResponse, ScoreSuggestionResponse
from api.app.schemas.common import AppError
from api.app.services.ai_review_service import build_case_snapshot, enqueue_ai_review, is_stale, serialize_run
from api.app.services.rule_check_service import evaluate_case_rules
from api.app.services.score_decision_service import evaluate_score_suggestions
from api.app.services.auth_service import require_roles, verify_csrf


router = APIRouter(prefix="/bcs", tags=["BCS AI Reviews"])


def _authorized_case(db: Session, case_id: str, class_ids: list[str]) -> Case:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy hồ sơ.")
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).first()
    if not campaign or campaign.class_id not in class_ids:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền xem hồ sơ này.")
    return case


@router.get("/cases/{case_id}/rule-checks", response_model=RuleCheckResponse)
def get_rule_checks(
    case_id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    _, class_ids = auth_data
    return evaluate_case_rules(db, _authorized_case(db, case_id, class_ids))


@router.get("/cases/{case_id}/score-suggestions", response_model=ScoreSuggestionResponse)
def get_score_suggestions(
    case_id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    _, class_ids = auth_data
    case = _authorized_case(db, case_id, class_ids)
    run = (db.query(AiReviewRun).filter(AiReviewRun.case_id == case.id)
           .order_by(AiReviewRun.created_at.desc(), AiReviewRun.id.desc()).first())
    if run and is_stale(db, run):
        run = None
    read = next((step for step in run.steps if step.kind == "AI_READ" and step.status == "COMPLETED"), None) if run else None
    transparency = next((step for step in run.steps if step.kind == "AI_TRANSPARENCY" and step.status == "COMPLETED"), None) if run else None
    checks = evaluate_case_rules(db, case, (read.output_json or {}).get("files") if read else None)
    rubric_version, _, _ = build_case_snapshot(db, case)
    return evaluate_score_suggestions(
        db, case,
        assessments=(transparency.output_json or {}).get("assessments") if transparency else None,
        rule_checks=checks, rubric_version=rubric_version,
        source_run_id=run.id if run else None,
    )


@router.post("/cases/{case_id}/ai-reviews", response_model=AiReviewResponse,
             status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_csrf)])
def create_ai_review(
    case_id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    user, class_ids = auth_data
    case = _authorized_case(db, case_id, class_ids)
    run = enqueue_ai_review(db, case, user.id)
    return serialize_run(db, run)


@router.get("/cases/{case_id}/ai-reviews/latest", response_model=AiLatestResponse)
def latest_ai_review(
    case_id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    _, class_ids = auth_data
    _authorized_case(db, case_id, class_ids)
    run = (
        db.query(AiReviewRun)
        .filter(AiReviewRun.case_id == case_id)
        .order_by(AiReviewRun.created_at.desc(), AiReviewRun.id.desc())
        .first()
    )
    return {"run": serialize_run(db, run) if run else None}


@router.get("/cases/{case_id}/ai-reviews/{run_id}", response_model=AiReviewResponse)
def get_ai_review(
    case_id: str,
    run_id: str,
    auth_data: tuple[User, list[str]] = Depends(require_roles("BCS")),
    db: Session = Depends(get_db),
):
    _, class_ids = auth_data
    _authorized_case(db, case_id, class_ids)
    run = db.query(AiReviewRun).filter(AiReviewRun.id == run_id, AiReviewRun.case_id == case_id).first()
    if not run:
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy lượt phân tích.")
    return serialize_run(db, run)
