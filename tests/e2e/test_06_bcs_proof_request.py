"""
Acceptance Test 06 - Section 9.6:
BCS yêu cầu PROOF, SV nộp lại; quá hạn PROOF quay BCS để kết luận, không tự trừ điểm.
"""
import io
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
import pytest
from tests.fixtures.client import AcceptanceTestClient

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not os.getenv("RUN_ACCEPTANCE_TESTS"),
        reason="Chờ ghép backend/UI ở Giai đoạn 2 (Backend routes hiện là shell từ foundation-v1)"
    )
]


def test_06_bcs_proof_request_and_timeout_behavior(api_client: AcceptanceTestClient):
    """
    Kịch bản:
    1. Sinh viên sv001 nộp đầy đủ hồ sơ và minh chứng -> hồ sơ chuyển sang BCS_REVIEW.
    2. BCS xem hồ sơ đang ở BCS_REVIEW và phát hiện minh chứng chưa rõ.
    3. BCS gọi POST /bcs/cases/{caseId}/supplement-requests với kind=PROOF.
    4. Kỳ vọng:
       - Hồ sơ chuyển sang NEEDS_PROOF.
       - proof_round tăng lên 1 (không vượt quá max_proof_rounds).
       - Sinh viên nhận thông báo yêu cầu minh chứng bổ sung.
    5. Quá hạn PROOF mà sinh viên không nộp lại:
       - Hệ thống (qua tick) chuyển hồ sơ quay lại BCS_REVIEW để BCS đưa ra kết luận thủ công.
       - Hệ thống KHÔNG tự ý trừ điểm của sinh viên.
    """
    # 1. Sinh viên sv001 nộp hồ sơ hoàn chỉnh sang BCS_REVIEW
    api_client.login_as_student("sv001")
    sv_data = api_client.get("/api/v1/student/current").json()
    case_id = sv_data["case"]["id"]
    version = sv_data["case"]["version"]
    criteria = sv_data["criteria"]

    for crit in criteria:
        put_res = api_client.put(
            f"/api/v1/student/cases/{case_id}/claims/{crit['id']}",
            json={"self_score": "8.00", "student_note": "Tự chấm", "expected_version": version}
        )
        assert put_res.status_code == 200
        version = put_res.json().get("version", version + 1)

        if crit.get("requires_evidence"):
            pdf = io.BytesIO(b"%PDF-1.4 evidence")
            up_res = api_client.post(
                f"/api/v1/student/cases/{case_id}/evidence",
                data={"criterion_id": crit["id"]},
                files={"file": (f"{crit['code']}.pdf", pdf, "application/pdf")}
            )
            assert up_res.status_code in [200, 201]

    sub_res = api_client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version}
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "BCS_REVIEW"
    case_version = sub_res.json()["version"]

    # 2. BCS xem hồ sơ và gửi yêu cầu PROOF
    api_client.logout()
    api_client.login_as_bcs("bcs001")
    tc01_id = criteria[0]["id"]

    req_res = api_client.post(
        f"/api/v1/bcs/cases/{case_id}/supplement-requests",
        json={
            "kind": "PROOF",
            "criterion_id": tc01_id,
            "reason": "Ảnh chụp chứng chỉ mờ, đề nghị chụp lại rõ nét",
            "expected_version": case_version
        }
    )
    assert req_res.status_code in [200, 201]
    req_data = req_res.json()
    assert req_data["kind"] == "PROOF"
    supp_id = req_data["id"]

    # 3. Kiểm tra hồ sơ chuyển sang NEEDS_PROOF
    case_detail = api_client.get(f"/api/v1/bcs/cases/{case_id}").json()
    assert case_detail["status"] == "NEEDS_PROOF"
    assert case_detail["rounds"]["proof"] == 1

    # 4. Mô phỏng quá hạn PROOF: cập nhật deadline của yêu cầu lùi về quá khứ
    from api.app.database import SessionLocal
    from api.app.models.entities import SupplementRequest
    db = SessionLocal()
    try:
        supp_obj = db.query(SupplementRequest).filter(SupplementRequest.id == supp_id).first()
        supp_obj.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    # Chạy deadline tick để quét hạn
    simulated_now = datetime.now(timezone.utc).isoformat()
    cmd = [sys.executable, "-m", "api.app.jobs.tick", "--now", simulated_now]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0

    # 5. Kiểm tra hồ sơ đã tự động quay lại BCS_REVIEW và giữ nguyên self_score
    case_reloaded = api_client.get(f"/api/v1/bcs/cases/{case_id}").json()
    assert case_reloaded["status"] == "BCS_REVIEW"
    for claim in case_reloaded["claims"]:
        assert claim["self_score"] is not None, "Self score must not be erased"
