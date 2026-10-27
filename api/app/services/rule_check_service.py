"""Deterministic checks for structured claims and evidence metadata.

Findings advise a human reviewer; this module never approves evidence or scores.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from api.app.models.entities import Campaign, Case, Claim, Criterion, EvidenceFile


RULE_VERSION = "evidence-rules-v1"
DATE_PATTERN = re.compile(r"(?<!\d)(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)")


def _parse_date(value: str) -> date | None:
    matches = DATE_PATTERN.findall(value)
    if len(matches) != 1:
        return None
    candidate = matches[0]
    formats = ("%Y-%m-%d",) if candidate[:4].isdigit() and candidate[4:5] == "-" else ("%d/%m/%Y", "%d-%m-%Y")
    for fmt in formats:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def evaluate_case_rules(db: Session, case: Case, read_results: list[dict] | None = None) -> dict:
    campaign = db.query(Campaign).filter(Campaign.id == case.campaign_id).one()
    criteria = {item.id: item for item in db.query(Criterion).filter(Criterion.campaign_id == campaign.id).all()}
    claims = db.query(Claim).filter(Claim.case_id == case.id).all()
    claim_by_id = {item.id: item for item in claims}
    evidence = (
        db.query(EvidenceFile).filter(EvidenceFile.claim_id.in_(claim_by_id), EvidenceFile.is_current.is_(True)).all()
        if claim_by_id else []
    )
    evidence_by_claim: dict[str, list[EvidenceFile]] = defaultdict(list)
    for item in evidence:
        evidence_by_claim[item.claim_id].append(item)

    findings: list[dict] = []

    def add(code: str, level: str, message: str, criterion: Criterion | None = None,
            file_ids: list[str] | None = None, details: dict | None = None) -> None:
        findings.append({
            "code": code, "level": level, "message": message,
            "criterion_id": criterion.id if criterion else None,
            "criterion_code": criterion.code if criterion else None,
            "evidence_file_ids": sorted(file_ids or []),
            "details": details or {},
        })

    for claim in claims:
        criterion = criteria.get(claim.criterion_id)
        if criterion is None:
            add("CRITERION_NOT_IN_CAMPAIGN", "FLAGGED", "Tiêu chí của điểm tự khai không thuộc đợt đánh giá này.")
            continue
        if claim.self_score is None:
            continue
        score = Decimal(str(claim.self_score))
        max_score = Decimal(str(criterion.max_score))
        if campaign.template_code == "49K14_1_V1" and criterion.code == "8b":
            max_score = min(max_score, Decimal("2.00"))
        if score < 0 or score > max_score:
            add("SCORE_OUT_OF_RANGE", "FLAGGED", f"Điểm tự khai {score} nằm ngoài khoảng 0–{max_score}.", criterion,
                details={"self_score": str(score), "max_score": str(max_score)})
        config = criterion.rule_config or {}
        options = config.get("options") if config.get("type") == "OPTIONS" else None
        if options:
            try:
                levels = {Decimal(str(item["score"])) for item in options}
            except (KeyError, InvalidOperation, TypeError):
                levels = set()
            if levels and score not in levels:
                add("SCORE_LEVEL_NOT_ALLOWED", "FLAGGED", "Điểm tự khai không thuộc mức điểm được cấu hình.", criterion,
                    details={"self_score": str(score), "allowed_levels": sorted(str(level) for level in levels)})
        if score > 0 and criterion.requires_evidence and not evidence_by_claim[claim.id]:
            add("EVIDENCE_MISSING", "UNKNOWN", "Mục có điểm tự khai nhưng chưa có minh chứng bắt buộc.", criterion)
        if score > 0 and (config.get("mandatory_bcs_review_if_positive") or
                          (campaign.template_code == "49K14_1_V1" and criterion.code in {"8a", "8b", "8c"})):
            add("MANDATORY_BCS_REVIEW", "FLAGGED", "Ban cán sự phải xác minh và chốt mục tự khai này.", criterion)

    by_hash: dict[str, list[tuple[EvidenceFile, Criterion]]] = defaultdict(list)
    for file in evidence:
        claim = claim_by_id[file.claim_id]
        criterion = criteria.get(claim.criterion_id)
        if criterion and file.sha256:
            by_hash[file.sha256].append((file, criterion))
    for group in by_hash.values():
        # 4b is explicitly exempt from the one-evidence-per-item rule.
        constrained = [(file, criterion) for file, criterion in group
                       if not (campaign.template_code == "49K14_1_V1" and criterion.code.startswith("4b"))]
        codes = {criterion.code for _, criterion in constrained}
        if len(codes) > 1:
            add("DUPLICATE_EVIDENCE", "FLAGGED",
                "Cùng một tệp được dùng cho nhiều tiêu chí; Ban cán sự cần xem xét.",
                file_ids=[file.id for file, _ in constrained],
                details={"criterion_codes": sorted(codes)})

    term_ready = bool(campaign.term_start_on and campaign.term_end_on)
    if read_results:
        file_by_id = {item.id: item for item in evidence}
        for read_file in read_results:
            file = file_by_id.get(read_file.get("evidence_file_id"))
            if not file or file.sha256 != read_file.get("sha256"):
                continue  # Stale or foreign model output must not influence the rules.
            claim = claim_by_id[file.claim_id]
            criterion = criteria.get(claim.criterion_id)
            if criterion is None or claim.self_score is None or claim.self_score <= 0:
                continue
            if not read_file.get("readable"):
                add("EVIDENCE_UNREADABLE", "UNKNOWN", "Không đọc được ngày hoạt động trên minh chứng.",
                    criterion, [file.id])
                continue
            date_facts = [fact for fact in read_file.get("facts", []) if fact.get("kind") == "event_date"]
            if not date_facts:
                add("EVENT_DATE_NOT_FOUND", "UNKNOWN", "Chưa tìm thấy ngày hoạt động trên minh chứng.",
                    criterion, [file.id])
                continue
            dates = {_parse_date(str(fact.get("value", ""))) for fact in date_facts}
            if None in dates or len(dates) != 1:
                add("EVENT_DATE_AMBIGUOUS", "UNKNOWN", "Ngày hoạt động chưa đủ rõ để kiểm tra bằng luật.",
                    criterion, [file.id])
                continue
            event_date = next(iter(dates))
            if term_ready and not (campaign.term_start_on <= event_date <= campaign.term_end_on):
                add("EVENT_DATE_OUTSIDE_TERM", "FLAGGED", "Ngày hoạt động nằm ngoài khoảng học kỳ đã cấu hình.",
                    criterion, [file.id], details={"event_date": event_date.isoformat(),
                                                    "term_start_on": campaign.term_start_on.isoformat(),
                                                    "term_end_on": campaign.term_end_on.isoformat()})

    findings.sort(key=lambda item: (item["criterion_code"] or "", item["code"], item["evidence_file_ids"]))
    return {
        "case_id": case.id,
        "case_version": case.version,
        "rule_version": RULE_VERSION,
        "term_window": {
            "status": "CONFIGURED" if term_ready else "NOT_CONFIGURED",
            "start_on": campaign.term_start_on.isoformat() if campaign.term_start_on else None,
            "end_on": campaign.term_end_on.isoformat() if campaign.term_end_on else None,
        },
        "date_evidence_status": "CHECKED" if read_results else "WAITING_FOR_READ_DATA",
        "findings": findings,
        "counts": {
            "flagged": sum(item["level"] == "FLAGGED" for item in findings),
            "unknown": sum(item["level"] == "UNKNOWN" for item in findings),
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
