import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.database import SessionLocal
from api.app.models.entities import Campaign, Criterion, Case, Claim, User, UserPosition, EvaluationTemplate
from api.app.services.scoring_service import (
    validate_criterion_levels,
    convert_gpa_to_score,
    get_rating,
    parse_score,
    validate_score_bounds,
)
from api.app.services.template_service import (
    CRITERIA_49K14_1_DEFINITIONS,
    TEMPLATE_49K14_1_CODE,
    TEMPLATE_LEGACY_DEMO_CODE,
    ensure_templates_seeded,
)
from api.app.schemas.common import AppError


def test_template_criteria_definitions_23_rows_and_100_points():
    """Kiểm tra mẫu 49K14.1 có đúng 23 tiêu chí và tổng điểm tối đa là 100.00"""
    assert len(CRITERIA_49K14_1_DEFINITIONS) == 23

    section_totals = {}
    grand_total = Decimal("0.00")

    for crit in CRITERIA_49K14_1_DEFINITIONS:
        sec = crit["section_code"]
        sec_max = crit["section_max_score"]
        score = crit["max_score"]

        section_totals.setdefault(sec, {"max": sec_max, "sum": Decimal("0.00")})
        section_totals[sec]["sum"] += score
        grand_total += score

    # Điều 4 = 20, Điều 5 = 25, Điều 6 = 20, Điều 7 = 25, Điều 8 = 10
    assert section_totals["DIEU_4"]["sum"] == Decimal("20.00")
    assert section_totals["DIEU_4"]["max"] == Decimal("20.00")

    assert section_totals["DIEU_5"]["sum"] == Decimal("25.00")
    assert section_totals["DIEU_5"]["max"] == Decimal("25.00")

    assert section_totals["DIEU_6"]["sum"] == Decimal("20.00")
    assert section_totals["DIEU_6"]["max"] == Decimal("20.00")

    assert section_totals["DIEU_7"]["sum"] == Decimal("25.00")
    assert section_totals["DIEU_7"]["max"] == Decimal("25.00")

    assert section_totals["DIEU_8"]["sum"] == Decimal("10.00")
    assert section_totals["DIEU_8"]["max"] == Decimal("10.00")

    assert grand_total == Decimal("100.00")


def test_gpa_thresholds_conversion():
    """Kiểm tra chính xác các mốc GPA: 1.99, 2.00, 3.19, 3.20, 4.00"""
    assert convert_gpa_to_score(Decimal("1.99")) == Decimal("0.00")
    assert convert_gpa_to_score(Decimal("0.50")) == Decimal("0.00")
    assert convert_gpa_to_score(Decimal("0.00")) == Decimal("0.00")

    assert convert_gpa_to_score(Decimal("2.00")) == Decimal("2.00")
    assert convert_gpa_to_score(Decimal("2.50")) == Decimal("2.00")
    assert convert_gpa_to_score(Decimal("3.19")) == Decimal("2.00")

    assert convert_gpa_to_score(Decimal("3.20")) == Decimal("4.00")
    assert convert_gpa_to_score(Decimal("3.80")) == Decimal("4.00")
    assert convert_gpa_to_score(Decimal("4.00")) == Decimal("4.00")


def test_criterion_8b_strictly_capped_at_2():
    """Kiểm tra tiêu chí 8b bị chặn không được vượt quá 2.00 điểm dù Word có mô tả 1=>3"""
    validate_criterion_levels("8b", Decimal("0.00"))
    validate_criterion_levels("8b", Decimal("1.00"))
    validate_criterion_levels("8b", Decimal("2.00"))

    with pytest.raises(AppError) as exc_info:
        validate_criterion_levels("8b", Decimal("2.50"))
    assert exc_info.value.code in ["SCORE_OUT_OF_BOUNDS", "INVALID_SCORE_LEVEL"]

    with pytest.raises(AppError) as exc_info:
        validate_criterion_levels("8b", Decimal("3.00"))
    assert exc_info.value.code in ["SCORE_OUT_OF_BOUNDS", "INVALID_SCORE_LEVEL"]


def test_penalty_levels_and_exact_discrete_scores():
    """Kiểm tra các mức điểm rời rạc của các tiêu chí theo tài liệu"""
    # 4a: 4, 2, 0
    validate_criterion_levels("4a", Decimal("4.00"))
    validate_criterion_levels("4a", Decimal("2.00"))
    validate_criterion_levels("4a", Decimal("0.00"))
    with pytest.raises(AppError):
        validate_criterion_levels("4a", Decimal("3.00"))

    # 4c: 6, 4, 0
    validate_criterion_levels("4c", Decimal("6.00"))
    validate_criterion_levels("4c", Decimal("4.00"))
    validate_criterion_levels("4c", Decimal("0.00"))
    with pytest.raises(AppError):
        validate_criterion_levels("4c", Decimal("5.00"))

    # 5b1: 10, 8, 6, 0
    validate_criterion_levels("5b1", Decimal("10.00"))
    validate_criterion_levels("5b1", Decimal("8.00"))
    validate_criterion_levels("5b1", Decimal("6.00"))
    validate_criterion_levels("5b1", Decimal("0.00"))
    with pytest.raises(AppError):
        validate_criterion_levels("5b1", Decimal("7.00"))

    # 5b2: 5, 0
    validate_criterion_levels("5b2", Decimal("5.00"))
    validate_criterion_levels("5b2", Decimal("0.00"))
    with pytest.raises(AppError):
        validate_criterion_levels("5b2", Decimal("2.50"))

    # 6a1: 10, 8, 6, 0
    validate_criterion_levels("6a1", Decimal("10.00"))
    validate_criterion_levels("6a1", Decimal("8.00"))
    validate_criterion_levels("6a1", Decimal("6.00"))
    validate_criterion_levels("6a1", Decimal("0.00"))
    with pytest.raises(AppError):
        validate_criterion_levels("6a1", Decimal("9.00"))

    # 6a2: 6, 4, 2, 0
    validate_criterion_levels("6a2", Decimal("6.00"))
    validate_criterion_levels("6a2", Decimal("4.00"))
    validate_criterion_levels("6a2", Decimal("2.00"))
    validate_criterion_levels("6a2", Decimal("0.00"))

    # 7a1: 4, 2, 0
    validate_criterion_levels("7a1", Decimal("4.00"))
    validate_criterion_levels("7a1", Decimal("2.00"))
    validate_criterion_levels("7a1", Decimal("0.00"))

    # 7a2: 10, 0
    validate_criterion_levels("7a2", Decimal("10.00"))
    validate_criterion_levels("7a2", Decimal("0.00"))
    with pytest.raises(AppError):
        validate_criterion_levels("7a2", Decimal("5.00"))

    # 7a3: 5, 3, 0
    validate_criterion_levels("7a3", Decimal("5.00"))
    validate_criterion_levels("7a3", Decimal("3.00"))
    validate_criterion_levels("7a3", Decimal("0.00"))


def test_rating_classification_parameters_sheet():
    """Kiểm tra xếp loại theo thang điểm sheet Parameters"""
    assert get_rating(Decimal("100.00")) == "Xuất sắc"
    assert get_rating(Decimal("90.00")) == "Xuất sắc"
    assert get_rating(Decimal("89.99")) == "Tốt"
    assert get_rating(Decimal("80.00")) == "Tốt"
    assert get_rating(Decimal("79.50")) == "Khá"
    assert get_rating(Decimal("65.00")) == "Khá"
    assert get_rating(Decimal("64.99")) == "Trung bình"
    assert get_rating(Decimal("50.00")) == "Trung bình"
    assert get_rating(Decimal("49.00")) == "Yếu"
    assert get_rating(Decimal("35.00")) == "Yếu"
    assert get_rating(Decimal("34.99")) == "Kém"
    assert get_rating(Decimal("0.00")) == "Kém"


def test_student_cannot_submit_4e_via_api(client: TestClient, seed_data, db):
    """Kiểm tra sinh viên bị khóa không thể tự nhập điểm 4e qua API (trả về 403 FORBIDDEN_CRITERION_INPUT)"""
    admin_login = client.post("/api/v1/auth/login", json={"username": "admin001", "password": "Demo@123456"})
    assert admin_login.status_code == 200
    admin_csrf = admin_login.json()["csrf_token"]

    camp_payload = {
        "class_id": "c1111111-1111-1111-1111-111111111111",
        "title": "Đợt test mẫu 49K14.1",
        "term": "HK2-2025-2026",
        "template_code": "49K14_1_V1",
        "open_at": "2026-01-01T00:00:00Z",
        "submission_deadline_at": "2026-12-31T23:59:59Z",
        "criteria": [],  # Sẽ tự động nạp 23 tiêu chí
    }
    res_create = client.post("/api/v1/admin/campaigns", json=camp_payload, headers={"X-CSRF-Token": admin_csrf})
    assert res_create.status_code == 201
    camp_data = res_create.json()
    assert len(camp_data["criteria"]) == 23

    crit_4e = next(c for c in camp_data["criteria"] if c["code"] == "4e")

    # Mở đợt đánh giá
    res_open = client.post(f"/api/v1/admin/campaigns/{camp_data['id']}/open", headers={"X-CSRF-Token": admin_csrf})
    assert res_open.status_code == 200

    # Đăng nhập bằng tài khoản sinh viên sv002
    sv_login = client.post("/api/v1/auth/login", json={"username": "sv002", "password": "Demo@123456"})
    assert sv_login.status_code == 200
    sv_csrf = sv_login.json()["csrf_token"]

    # Lấy case hiện tại của sv002
    curr_res = client.get("/api/v1/student/current")
    assert curr_res.status_code == 200
    curr_data = curr_res.json()
    case_id = curr_data["case"]["id"]
    version = curr_data["case"]["version"]

    # Sinh viên cố gắng tự gửi điểm cho 4e
    claim_payload = {
        "self_score": "4.00",
        "student_note": "Em tự nhập GPA 3.5",
        "expected_version": version,
    }
    crit_4e_id = crit_4e["id"]
    put_res = client.put(
        f"/api/v1/student/cases/{case_id}/claims/{crit_4e_id}",
        json=claim_payload,
        headers={"X-CSRF-Token": sv_csrf},
    )
    assert put_res.status_code == 403
    assert put_res.json()["error"]["code"] == "FORBIDDEN_CRITERION_INPUT"


def test_positive_cadre_claim_is_allowed_for_bcs_review(client: TestClient, seed_data, db):
    """Sinh viên được tự khai 8a–8c; mọi điểm dương phải qua Ban cán sự."""
    admin_login = client.post("/api/v1/auth/login", json={"username": "admin001", "password": "Demo@123456"})
    assert admin_login.status_code == 200
    admin_csrf = admin_login.json()["csrf_token"]

    camp_payload = {
        "class_id": "c1111111-1111-1111-1111-111111111111",
        "title": "Đợt test quyền cán bộ",
        "term": "HK2-2025-2026-B",
        "template_code": "49K14_1_V1",
        "open_at": "2026-01-01T00:00:00Z",
        "submission_deadline_at": "2026-12-31T23:59:59Z",
        "criteria": [],
    }
    res_create = client.post("/api/v1/admin/campaigns", json=camp_payload, headers={"X-CSRF-Token": admin_csrf})
    camp_data = res_create.json()
    client.post(f"/api/v1/admin/campaigns/{camp_data['id']}/open", headers={"X-CSRF-Token": admin_csrf})

    sv_login = client.post("/api/v1/auth/login", json={"username": "sv002", "password": "Demo@123456"})
    assert sv_login.status_code == 200
    sv_csrf = sv_login.json()["csrf_token"]

    curr_res = client.get("/api/v1/student/current")
    assert curr_res.status_code == 200
    curr_data = curr_res.json()
    case_id = curr_data["case"]["id"]
    version = curr_data["case"]["version"]

    crit_8a = next((c for c in curr_data["criteria"] if c["code"] == "8a"), None)
    assert crit_8a is not None

    assert crit_8a["rule_config"]["mandatory_bcs_review_if_positive"] is True

    # sv002 chưa có chức vụ xác nhận vẫn được tự khai để Ban cán sự xem xét.
    claim_payload = {
        "self_score": "2.00",
        "student_note": "Em tự chấm 8a",
        "expected_version": version,
    }
    put_res = client.put(
        f"/api/v1/student/cases/{case_id}/claims/{crit_8a['id']}",
        json=claim_payload,
        headers={"X-CSRF-Token": sv_csrf},
    )
    assert put_res.status_code == 200
    assert put_res.json()["claim"]["self_score"] == "2.00"


def test_admin_import_academic_scores(client: TestClient, seed_data, db):
    """Kiểm tra admin import điểm GPA 4e thành công và tự động quy đổi"""
    admin_login = client.post("/api/v1/auth/login", json={"username": "admin001", "password": "Demo@123456"})
    assert admin_login.status_code == 200
    admin_csrf = admin_login.json()["csrf_token"]

    camp_payload = {
        "class_id": "c1111111-1111-1111-1111-111111111111",
        "title": "Đợt test import GPA",
        "term": "HK2-2025-2026-C",
        "template_code": "49K14_1_V1",
        "open_at": "2026-01-01T00:00:00Z",
        "submission_deadline_at": "2026-12-31T23:59:59Z",
        "criteria": [],
    }
    res_create = client.post("/api/v1/admin/campaigns", json=camp_payload, headers={"X-CSRF-Token": admin_csrf})
    camp_data = res_create.json()
    client.post(f"/api/v1/admin/campaigns/{camp_data['id']}/open", headers={"X-CSRF-Token": admin_csrf})

    import_payload = {
        "items": [
            {"student_code": "sv002", "gpa": 3.45},
            {"student_code": "sv003", "gpa": 2.75},
        ]
    }
    import_res = client.post(
        f"/api/v1/admin/campaigns/{camp_data['id']}/academic-scores",
        json=import_payload,
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert import_res.status_code == 200
    res_data = import_res.json()
    assert res_data["updated_count"] == 2

    details = {d["student_code"]: d for d in res_data["details"]}
    assert details["sv002"]["status"] == "UPDATED"
    assert details["sv002"]["converted_score"] == 4.0
    assert details["sv003"]["status"] == "UPDATED"
    assert details["sv003"]["converted_score"] == 2.0
