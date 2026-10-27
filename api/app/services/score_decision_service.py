"""Deterministic draft scores for BCS review; never writes approved scores."""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from api.app.models.entities import Campaign, Case, Claim, Criterion, EvidenceFile
from api.app.services.rule_check_service import evaluate_case_rules
from api.app.services.scoring_service import convert_gpa_to_score, sum_scores


DECISION_VERSION = "score-decision-v1"


def _score_text(value: Decimal | None) -> str | None:
    return f"{value:.2f}" if value is not None else None


def _allowed_option(criterion: Criterion, score: Decimal) -> str | None:
    config = criterion.rule_config or {}
    if config.get("type") != "OPTIONS" or not isinstance(config.get("options"), list):
        return None
    for option in config["options"]:
        try:
            if Decimal(str(option["score"])) == score:
                return str(option.get("label") or "Mức điểm đã cấu hình")
        except (KeyError, InvalidOperation, TypeError):
            continue
    return None


def evaluate_score_suggestions(
    db: Session, case: Case, *, assessments: list[dict] | None = None,
    rule_checks: dict | None = None, rubric_version: str | None = None,
    source_run_id: str | None = None,
) -> dict:
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).one()
    criteria = (db.query(Criterion).filter(Criterion.campaign_id == campaign.id)
                .order_by(Criterion.sort_order, Criterion.code).all())
    claims = {item.criterion_id: item for item in db.query(Claim).filter(Claim.case_id == case.id).all()}
    claim_ids = [item.id for item in claims.values()]
    files = (db.query(EvidenceFile).filter(EvidenceFile.claim_id.in_(claim_ids),
                                           EvidenceFile.is_current.is_(True)).all() if claim_ids else [])
    files_by_claim: dict[str, list[EvidenceFile]] = defaultdict(list)
    for file in files:
        files_by_claim[file.claim_id].append(file)

    checks = rule_checks or evaluate_case_rules(db, case)
    finding_codes: dict[str, set[str]] = defaultdict(set)
    for finding in checks["findings"]:
        if finding["criterion_code"]:
            finding_codes[finding["criterion_code"]].add(finding["code"])
        for code in finding.get("details", {}).get("criterion_codes", []):
            finding_codes[code].add(finding["code"])

    assessment_by_file = {
        (item.get("evidence_file_id"), item.get("sha256")): item
        for item in (assessments or [])
        if item.get("evidence_file_id") and item.get("sha256")
    }
    items: list[dict] = []
    section_items: dict[str, list[dict]] = defaultdict(list)
    section_max: dict[str, Decimal] = {}

    for criterion in criteria:
        claim = claims.get(criterion.id)
        score = Decimal(str(claim.self_score)) if claim and claim.self_score is not None else None
        evidence = files_by_claim.get(claim.id, []) if claim else []
        item = {
            "criterion_id": criterion.id, "criterion_code": criterion.code,
            "clause_id": f"{campaign.template_code}:{criterion.code}",
            "self_score": _score_text(score), "draft_score": None,
            "status": "REVIEW_REQUIRED", "reason": "", "calculation": None,
            "evidence_file_ids": sorted(file.id for file in evidence),
            "finding_codes": sorted(finding_codes.get(criterion.code, set())),
        }
        items.append(item)
        if criterion.section_code and criterion.section_max_score is not None:
            section_items[criterion.section_code].append(item)
            section_max[criterion.section_code] = Decimal(str(criterion.section_max_score))

        if campaign.template_code != "49K14_1_V1":
            item["reason"] = "Bộ quy tắc này chưa được cấu hình để đề xuất điểm bằng luật."
            continue
        if claim is None or score is None:
            item["reason"] = "Chưa có điểm tự khai hoặc dữ liệu quy đổi chính thức."
            continue
        if item["finding_codes"]:
            item["reason"] = "Tầng luật có cảnh báo hoặc thiếu dữ kiện; Ban cán sự cần xử lý trước."
            continue

        config = criterion.rule_config or {}
        if config.get("type") == "GPA_CONVERSION" and criterion.code == "4e":
            gpa = Decimal(str(claim.academic_gpa)) if claim.academic_gpa is not None else None
            if gpa is None or not (Decimal("0") <= gpa <= Decimal("4")):
                item["reason"] = "Chưa có GPA hợp lệ từ nguồn quản trị để quy đổi."
                continue
            converted = convert_gpa_to_score(gpa)
            if score != converted:
                item["reason"] = "Điểm đã lưu khác kết quả quy đổi GPA; Ban cán sự cần kiểm tra dữ liệu import."
                continue
            item.update(status="READY", draft_score=_score_text(converted),
                        reason="Quy đổi theo GPA do quản trị viên nhập; Ban cán sự kiểm tra nguồn trước khi chốt.",
                        calculation=f"GPA {gpa:.2f} → {converted:.2f} điểm")
            continue

        option = _allowed_option(criterion, score)
        if option is None or score < 0 or score > Decimal(str(criterion.max_score)):
            item["reason"] = "Mức điểm tự khai không khớp các lựa chọn hoặc vượt trần tiêu chí."
            continue
        if score > 0 and criterion.code in {"8a", "8b", "8c"}:
            item["reason"] = "Mục 8a–8c có điểm dương bắt buộc Ban cán sự xác minh và chốt."
            continue
        if score > 0 and criterion.requires_evidence and not evidence:
            item["reason"] = "Thiếu minh chứng bắt buộc."
            continue
        if score > 0 and evidence:
            review = [assessment_by_file.get((file.id, file.sha256)) for file in evidence]
            if any(result is None for result in review):
                item["reason"] = "Chưa có kết quả đối chiếu đầy đủ cho tất cả minh chứng."
                continue
            if any(result.get("criterion_code") != criterion.code or
                   result.get("verdict") != "SUPPORTED" or
                   result.get("authenticity") == "SUSPICIOUS" or
                   not result.get("citations") for result in review):
                item["reason"] = "Minh chứng bị đánh cờ hoặc chưa đủ căn cứ để gợi ý mức điểm."
                continue

        item.update(status="READY", draft_score=_score_text(score),
                    reason="Mức tự khai hợp lệ theo cấu hình; Ban cán sự vẫn phải kiểm tra và lưu quyết định.",
                    calculation=f"{option} → {score:.2f} điểm")

    section_checks = []
    for section_code, grouped in section_items.items():
        subtotal = sum_scores([Decimal(item["draft_score"]) for item in grouped if item["draft_score"] is not None])
        cap = section_max[section_code]
        over_cap = subtotal > cap
        section_checks.append({"section_code": section_code, "draft_subtotal": _score_text(subtotal),
                               "max_score": _score_text(cap), "over_cap": over_cap})
        if over_cap:
            for item in grouped:
                if item["draft_score"] is not None:
                    item.update(status="REVIEW_REQUIRED", draft_score=None, calculation=None,
                                reason=f"Tổng mục {section_code} vượt trần {cap:.2f}; Ban cán sự cần phân bổ lại.")

    all_ready = bool(items) and all(item["status"] == "READY" for item in items)
    total = sum_scores([Decimal(item["draft_score"]) for item in items if item["draft_score"] is not None])
    if total > Decimal("100.00"):
        all_ready = False
        for item in items:
            if item["status"] == "READY":
                item.update(status="REVIEW_REQUIRED", draft_score=None, calculation=None,
                            reason="Tổng điểm vượt trần 100; Ban cán sự cần rà soát.")
    return {
        "case_id": case.id, "case_version": case.version,
        "rubric_version": rubric_version or campaign.template_code or "UNKNOWN",
        "decision_version": DECISION_VERSION, "rule_version": checks["rule_version"],
        "source_run_id": source_run_id,
        "items": items, "section_checks": section_checks,
        "draft_total": _score_text(total) if all_ready else None,
        "ready_count": sum(item["status"] == "READY" for item in items),
        "review_required_count": sum(item["status"] == "REVIEW_REQUIRED" for item in items),
        "requires_bcs_approval": True,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
