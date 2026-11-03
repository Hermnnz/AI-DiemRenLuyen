"""Type-specific evidence requirements shared by rules, prompts and acceptance."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime


DATE_PATTERN = re.compile(r"(?<!\d)(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def parse_date(value: str) -> date | None:
    matches = DATE_PATTERN.findall(value)
    if len(matches) != 1:
        return None
    candidate = matches[0]
    formats = ("%Y-%m-%d",) if candidate[4:5] == "-" and candidate[:4].isdigit() else ("%d/%m/%Y", "%d-%m-%Y")
    for fmt in formats:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class EvidencePolicy:
    code: str
    label: str
    required_groups: tuple[tuple[str, ...], ...]
    date_kind: str
    instructions: str
    document_markers: tuple[str, ...] = ()

    def as_context(self) -> dict:
        return {"type": self.code, "label": self.label,
                "required_fact_groups": [list(group) for group in self.required_groups],
                "date_kind": self.date_kind, "instructions": self.instructions}


ACTIVITY = EvidencePolicy(
    "ACTIVITY_CERTIFICATE", "Giấy chứng nhận hoạt động",
    (("recipient",), ("activity_name",), ("event_date",), ("issuer",)), "event_date",
    "Đối chiếu người tham gia, hoạt động, đơn vị cấp và ngày diễn ra hoạt động trong kỳ. "
    "Ngày cấp (issued_on) và ngày sinh (birth_date) không thay thế event_date.",
)
INSURANCE = EvidencePolicy(
    "HEALTH_INSURANCE", "Thẻ BHYT / VssID",
    (("document_type",), ("recipient",), ("issuer",), ("reference_code",), ("valid_from",)), "valid_from",
    "Chỉ nhận thẻ BHYT/ảnh thông tin BHYT trên VssID cho tiêu chí BHYT. Đối chiếu người được bảo hiểm, "
    "cơ quan BHXH, mã thẻ và ngày bắt đầu hiệu lực (valid_from); trích valid_until nếu có. "
    "Không yêu cầu tên/ngày hoạt động, không dùng ngày sinh, ngày ký/cấp hoặc mốc đủ 5 năm liên tục "
    "làm ngày hiệu lực. Cần có bằng chứng tham gia trong kỳ: khoảng hiệu lực giao với kỳ; nếu chỉ có "
    "valid_from thì ngày đó phải nằm trong kỳ. Nếu valid_from trước kỳ và không có valid_until, "
    "chưa đủ căn cứ; không đoán thẻ còn hạn vô thời hạn. Không yêu cầu bao phủ toàn bộ học kỳ.",
    ("bhyt", "bao hiem y te", "health insurance"),
)
SOCIAL_POST = EvidencePolicy(
    "SOCIAL_POST", "Ảnh bài đăng / chia sẻ",
    (("document_type",), ("recipient", "account_name"), ("post_content", "activity_name"),
     ("post_date",), ("source_name", "issuer")), "post_date",
    "Đối chiếu nội dung bài đăng với chủ đề chính xác của tiêu chí, tài khoản thực hiện, nguồn bài "
    "và ngày đăng/chia sẻ. Không bắt có đơn vị cấp giấy. Tên tài khoản rút gọn/biệt danh chưa chứng minh "
    "đó là sinh viên; không tự ghép với tên hồ sơ. Ngày thiếu năm không được tự suy ra. "
    "Ngày sự kiện được nhắc trong nội dung không thay thế ngày đăng/chia sẻ.",
    ("bai dang", "bai chia se", "facebook", "social post", "social media"),
)
BLOOD_DONATION = EvidencePolicy(
    "BLOOD_DONATION", "Giấy chứng nhận hiến máu",
    (("document_type",), ("recipient",), ("issuer",), ("event_date",)), "event_date",
    "Đối chiếu người hiến máu, đơn vị xác nhận và ngày hiến máu. Tiêu đề giấy chứng nhận hiến máu "
    "đã thể hiện loại hoạt động, không bắt có thêm activity_name trùng nghĩa. Ngày sinh, ngày cấp "
    "và ngày ký không thay thế ngày hiến máu. Vẫn phải phù hợp điều khoản cụ thể của tiêu chí.",
    ("hien mau", "blood donation", "blood donor"),
)


def _values(facts: list[dict], kinds: tuple[str, ...]) -> list[str]:
    return [item["value"] for item in facts if item.get("kind") in kinds
            and isinstance(item.get("value"), str) and item["value"].strip()]


def _document_matches(policy: EvidencePolicy, facts: list[dict]) -> bool:
    return any(
        any(marker in normalize_text(item.get("value", "")) for marker in policy.document_markers)
        and bool(item.get("source_excerpt", "").strip())
        and (policy == SOCIAL_POST or any(marker in normalize_text(item.get("source_excerpt", ""))
                                         for marker in policy.document_markers))
        for item in facts if item.get("kind") == "document_type"
    )


def policy_for(criterion_code: str, facts: list[dict], template_code: str | None) -> EvidencePolicy:
    # A model's label cannot switch arbitrary criteria to a weaker policy.
    if template_code == "49K14_1_V1":
        if criterion_code == "7a2":
            return INSURANCE
        if criterion_code == "6c" and _document_matches(SOCIAL_POST, facts):
            return SOCIAL_POST
        if criterion_code in {"7b", "7c"} and _document_matches(BLOOD_DONATION, facts):
            return BLOOD_DONATION
    return ACTIVITY


def context_for(criterion: dict, facts: list[dict]) -> dict:
    template = criterion.get("template_code") or str(criterion.get("clause_id", "")).partition(":")[0]
    return policy_for(criterion["code"], facts, template).as_context()


def required_facts_present(policy: EvidencePolicy, facts: list[dict]) -> bool:
    return all(_values(facts, group) for group in policy.required_groups)


def identity_matches(policy: EvidencePolicy, facts: list[dict], student_name: str) -> bool:
    kinds = ("recipient", "account_name") if policy == SOCIAL_POST else ("recipient",)
    names = {normalize_text(value) for value in _values(facts, kinds)}
    return bool(names) and names == {normalize_text(student_name)}


def policy_issues(
    policy: EvidencePolicy, facts: list[dict], term_start: date | None, term_end: date | None,
) -> list[dict]:
    """Return only findings backed by visible, typed facts; never infer an expiry."""
    def issue(code: str, level: str, message: str, **details) -> list[dict]:
        return [{"code": code, "level": level, "message": message,
                 "details": {"evidence_type": policy.code, **details}}]

    def missing_requirements() -> list[dict]:
        labels = {"document_type": "loại minh chứng", "recipient": "người được ghi nhận",
                  "account_name": "tài khoản thực hiện", "activity_name": "tên hoạt động",
                  "event_date": "ngày hoạt động", "issuer": "đơn vị cấp/xác nhận",
                  "reference_code": "mã thẻ", "valid_from": "ngày bắt đầu hiệu lực",
                  "post_content": "nội dung bài đăng", "post_date": "ngày đăng/chia sẻ",
                  "source_name": "nguồn bài đăng"}
        missing = [group for group in policy.required_groups if not _values(facts, group)]
        if not missing:
            return []
        names = [" hoặc ".join(labels[kind] for kind in group) for group in missing]
        return issue("EVIDENCE_FACTS_MISSING", "UNKNOWN",
                     f"{policy.label} còn thiếu căn cứ: {', '.join(names)}.",
                     missing_fact_groups=[list(group) for group in missing])

    if policy.document_markers and not _document_matches(policy, facts):
        return issue("EVIDENCE_TYPE_MISMATCH", "UNKNOWN", f"Chưa có căn cứ đọc được xác nhận đúng loại {policy.label}.")
    if policy == INSURANCE:
        issuers = _values(facts, ("issuer",))
        if issuers and not any(any(marker in normalize_text(value)
                                  for marker in ("bao hiem xa hoi", "bhxh", "vietnam social security"))
                               for value in issuers):
            return issue("INSURANCE_ISSUER_UNCLEAR", "UNKNOWN", "Chưa nhận diện được cơ quan BHXH trên minh chứng BHYT.")
    values = _values(facts, (policy.date_kind,))
    if not values:
        code = "INSURANCE_VALID_FROM_NOT_FOUND" if policy == INSURANCE else "POST_DATE_NOT_FOUND" if policy == SOCIAL_POST else "EVENT_DATE_NOT_FOUND"
        label = "ngày bắt đầu hiệu lực BHYT" if policy == INSURANCE else "ngày đăng/chia sẻ" if policy == SOCIAL_POST else "ngày hoạt động"
        return issue(code, "UNKNOWN", f"Chưa tìm thấy {label} rõ ràng trên minh chứng.")
    dates = {parse_date(value) for value in values}
    if None in dates or len(dates) != 1:
        code = "INSURANCE_VALIDITY_AMBIGUOUS" if policy == INSURANCE else "POST_DATE_AMBIGUOUS" if policy == SOCIAL_POST else "EVENT_DATE_AMBIGUOUS"
        return issue(code, "UNKNOWN", "Mốc thời gian cần kiểm tra chưa rõ hoặc có dữ kiện mâu thuẫn.")
    start = next(iter(dates))
    if policy == INSURANCE:
        end_values = _values(facts, ("valid_until",))
        ends = {parse_date(value) for value in end_values}
        if None in ends or len(ends) > 1:
            return issue("INSURANCE_VALIDITY_AMBIGUOUS", "UNKNOWN", "Ngày hết hiệu lực BHYT chưa rõ hoặc có mâu thuẫn.")
        end = next(iter(ends)) if ends else None
        if end is not None and end < start:
            return issue("INSURANCE_VALIDITY_INVALID", "FLAGGED", "Ngày hết hiệu lực BHYT đứng trước ngày bắt đầu.")
        if term_start is None or term_end is None:
            return missing_requirements()  # Outer acceptance requires a configured term.
        if start > term_end or end is not None and end < term_start:
            return issue("INSURANCE_OUTSIDE_TERM", "FLAGGED", "Thời gian hiệu lực BHYT không giao với học kỳ.")
        if start < term_start and end is None:
            return issue("INSURANCE_COVERAGE_UNCONFIRMED", "UNKNOWN", "Thẻ bắt đầu trước học kỳ nhưng thiếu hạn kết thúc để xác nhận tham gia trong kỳ.")
        return missing_requirements()
    if term_start is not None and term_end is not None and not term_start <= start <= term_end:
        code = "POST_DATE_OUTSIDE_TERM" if policy == SOCIAL_POST else "EVENT_DATE_OUTSIDE_TERM"
        return issue(code, "FLAGGED", "Ngày đăng/chia sẻ nằm ngoài học kỳ." if policy == SOCIAL_POST else "Ngày hoạt động nằm ngoài khoảng học kỳ đã cấu hình.",
                     event_date=start.isoformat(), term_start_on=term_start.isoformat(), term_end_on=term_end.isoformat())
    return missing_requirements()
