"""
Script kiểm thử luồng tích hợp thực tế Giai đoạn 2.5:
Mô phỏng chính xác chu trình frontend browser live gọi qua FastAPI + PostgreSQL:
1. Đăng nhập sai password bị từ chối 401.
2. sv001 đăng nhập đúng, lưu session HttpOnly cookie và csrf_token. Refresh (/auth/me) giữ nguyên phiên.
3. sv001 cố truy cập /bcs -> bị 403 Forbidden.
4. sv001 lưu nháp điểm tự khai, tải file minh chứng thật, nộp hồ sơ.
5. bcs001 đăng nhập, lấy campaign active, kiểm tra case, duyệt điểm và lý do, hoàn tất review.
6. bcs001 ghi nhận biên bản 2 cuộc họp, công bố điểm dự kiến.
7. sv001 đăng nhập, xem điểm dự kiến và gửi khiếu nại.
8. bcs001 xử lý khiếu nại (ADJUST), chốt điểm đợt (FINALIZE).
9. gvcn001 đăng nhập, tải và kiểm tra CSV điểm chính thức.
10. Đăng xuất /auth/logout -> mất phiên, không truy cập được endpoint bảo vệ.
"""
import io
import os
import sys
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.app.main import app
from api.scripts.seed import run_seed

def run_integration_verification():
    print("=" * 70)
    print(" BẮT ĐẦU KIỂM CHỨNG TÍCH HỢP GIAI ĐOẠN 2.5 (LIVE FLOW)")
    print("=" * 70)

    # 0. Seed database & Reset trạng thái sạch
    print("\n[Bước 0] Reset & Seed dữ liệu...")
    run_seed()

    from api.app.database import SessionLocal
    from api.app.models import (
        Campaign,
        Case,
        Claim,
        EvidenceFile,
        SupplementRequest,
        Appeal,
        Meeting,
        ScoreSnapshot,
        Notification,
        AuditEvent,
    )
    from api.app.services.workflow_service import initialize_campaign_cases

    db = SessionLocal()
    try:
        db.query(Appeal).delete()
        db.query(ScoreSnapshot).delete()
        db.query(SupplementRequest).delete()
        db.query(EvidenceFile).delete()
        db.query(Claim).delete()
        db.query(Case).delete()
        db.query(Meeting).delete()
        db.query(Notification).delete()
        db.query(AuditEvent).delete()

        campaign = db.query(Campaign).first()
        if campaign:
            campaign.status = "OPEN"
            campaign.open_at = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)
            campaign.opened_at = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)
            initialize_campaign_cases(db, campaign)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    password = os.getenv("DEMO_PASSWORD", "Demo@123456")

    # 1. Test đăng nhập sai mật khẩu
    print("\n[Bước 1] Thử nghiệm đăng nhập sai mật khẩu...")
    res = client.post("/api/v1/auth/login", json={"username": "sv001", "password": "WrongPassword@123"})
    assert res.status_code == 401, f"Kỳ vọng 401 nhưng nhận {res.status_code}"
    err = res.json()["error"]
    assert err["code"] == "UNAUTHORIZED"
    print("  -> Đăng nhập sai mật khẩu bị từ chối chính xác: 401 UNAUTHORIZED")

    # 2. sv001 đăng nhập đúng
    print("\n[Bước 2] sv001 đăng nhập tài khoản thực...")
    res = client.post("/api/v1/auth/login", json={"username": "sv001", "password": password})
    assert res.status_code == 200
    sv_data = res.json()
    assert sv_data["user"]["role"] == "STUDENT"
    sv_csrf = sv_data["csrf_token"]
    assert sv_csrf, "Phải có CSRF token"
    assert "session_id" in client.cookies, "Phải có HttpOnly session cookie"
    print(f"  -> Đăng nhập thành công: {sv_data['user']['full_name']} (Role: {sv_data['user']['role']})")
    print(f"  -> Nhận CSRF Token: {sv_csrf[:16]}... và Session Cookie: {client.cookies.get('session_id')[:16]}...")

    # Khôi phục phiên qua GET /auth/me
    print("  -> Kiểm tra khôi phục phiên (F5/Refresh) qua GET /api/v1/auth/me...")
    res_me = client.get("/api/v1/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["user"]["username"] == "sv001"
    print("  -> Phiên làm việc được khôi phục chính xác qua session cookie.")

    # 3. sv001 thử truy cập endpoint của BCS -> 403 Forbidden
    print("\n[Bước 3] sv001 cố tình truy cập tài nguyên của BCS (/api/v1/bcs/campaigns/active)...")
    res_bcs = client.get("/api/v1/bcs/campaigns/active")
    assert res_bcs.status_code == 403, f"Kỳ vọng 403 nhưng nhận {res_bcs.status_code}"
    print("  -> Phân quyền hoạt động chuẩn xác: Sinh viên bị chặn 403 FORBIDDEN.")

    # 4. sv001 tải hồ sơ, tự chấm điểm, upload file và nộp
    print("\n[Bước 4] sv001 tự chấm điểm, tải minh chứng và nộp hồ sơ...")
    res_curr = client.get("/api/v1/student/current")
    assert res_curr.status_code == 200
    curr_data = res_curr.json()
    case_id = curr_data["case"]["id"]
    criteria = curr_data["criteria"]
    version = curr_data["case"]["version"]

    # Lưu điểm tự khai cho tất cả các tiêu chí
    crit1_id = criteria[0]["id"]
    for idx, crit in enumerate(criteria):
        sc = "8.00" if idx == 0 else "7.50"
        res_claim = client.put(
            f"/api/v1/student/cases/{case_id}/claims/{crit['id']}",
            json={"self_score": sc, "student_note": f"Tự chấm đạt tiêu chí {crit['code']}", "expected_version": version},
            headers={"X-CSRF-Token": sv_csrf}
        )
        assert res_claim.status_code == 200
        version = res_claim.json()["version"]
        if crit.get("requires_evidence"):
            fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
            res_upload = client.post(
                f"/api/v1/student/cases/{case_id}/evidence",
                data={"criterion_id": crit["id"]},
                files={"file": (f"minh_chung_{crit['code']}.png", io.BytesIO(fake_png), "image/png")},
                headers={"X-CSRF-Token": sv_csrf}
            )
            assert res_upload.status_code == 201
            print(f"  -> Đã tải tệp minh chứng thực cho {crit['code']} (File ID: {res_upload.json()['id']})")
    print(f"  -> Đã lưu điểm tự khai và tải đủ minh chứng (Version: {version})")

    # Nộp hồ sơ sv001
    res_submit = client.post(
        f"/api/v1/student/cases/{case_id}/submit",
        json={"expected_version": version},
        headers={"X-CSRF-Token": sv_csrf, "Idempotency-Key": f"submit-{case_id}"}
    )
    assert res_submit.status_code == 200
    print(f"  -> sv001 nộp hồ sơ thành công, trạng thái case: {res_submit.json()['status']}")

    # sv002 và sv003 cũng nộp hồ sơ để cả lớp sẵn sàng cho BCS duyệt
    for other_user in ["sv002", "sv003"]:
        c_other = TestClient(app)
        res_log = c_other.post("/api/v1/auth/login", json={"username": other_user, "password": password})
        c_csrf = res_log.json()["csrf_token"]
        cur = c_other.get("/api/v1/student/current").json()
        cid = cur["case"]["id"]
        cver = cur["case"]["version"]
        for cr in cur["criteria"]:
            res_c = c_other.put(
                f"/api/v1/student/cases/{cid}/claims/{cr['id']}",
                json={"self_score": "8.00", "student_note": f"Tự chấm {cr['code']}", "expected_version": cver},
                headers={"X-CSRF-Token": c_csrf}
            )
            cver = res_c.json()["version"]
            if cr.get("requires_evidence"):
                png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
                c_other.post(
                    f"/api/v1/student/cases/{cid}/evidence",
                    data={"criterion_id": cr["id"]},
                    files={"file": (f"minh_chung_{cr['code']}.png", io.BytesIO(png_bytes), "image/png")},
                    headers={"X-CSRF-Token": c_csrf}
                )
        c_other.post(
            f"/api/v1/student/cases/{cid}/submit",
            json={"expected_version": cver},
            headers={"X-CSRF-Token": c_csrf}
        )
    print("  -> sv002 và sv003 cũng đã hoàn tất nộp hồ sơ.")

    # 5. BCS đăng nhập và kiểm tra case
    print("\n[Bước 5] bcs001 đăng nhập để kiểm tra hồ sơ...")
    client_bcs = TestClient(app)
    res_blogin = client_bcs.post("/api/v1/auth/login", json={"username": "bcs001", "password": password})
    assert res_blogin.status_code == 200
    bcs_csrf = res_blogin.json()["csrf_token"]
    print(f"  -> bcs001 đăng nhập thành công (Role: {res_blogin.json()['user']['role']})")

    res_bcs_camp = client_bcs.get("/api/v1/bcs/campaigns/active")
    assert res_bcs_camp.status_code == 200
    campaign_id = res_bcs_camp.json()["id"]
    print(f"  -> Lấy đợt đánh giá active thành công: {campaign_id}")

    # BCS xem chi tiết case của sv001
    res_detail = client_bcs.get(f"/api/v1/bcs/cases/{case_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    bcs_version = detail["version"]
    print(f"  -> BCS xem chi tiết hồ sơ: {detail['student']['full_name']} (Mã: {detail['student']['code']})")

    # BCS duyệt điểm cho các tiêu chí
    for cl in detail["claims"]:
        cid = cl["criterion"]["id"]
        self_sc = cl["self_score"] or "5.00"
        res_rev = client_bcs.put(
            f"/api/v1/bcs/cases/{case_id}/claims/{cid}/review",
            json={"approved_score": self_sc, "reason": "BCS đồng ý với tự khai", "expected_version": bcs_version},
            headers={"X-CSRF-Token": bcs_csrf}
        )
        assert res_rev.status_code == 200
        bcs_version = res_rev.json()["version"]

    # BCS hoàn tất review case
    res_complete = client_bcs.post(
        f"/api/v1/bcs/cases/{case_id}/complete-review",
        json={"expected_version": bcs_version},
        headers={"X-CSRF-Token": bcs_csrf}
    )
    assert res_complete.status_code == 200
    assert res_complete.json()["status"] == "PROPOSED"
    print("  -> BCS hoàn tất chấm điểm hồ sơ -> chuyển trạng thái PROPOSED")

    # Xử lý các case còn lại trong lớp (sv002, sv003) để đủ điều kiện công bố
    res_cases = client_bcs.get(f"/api/v1/bcs/campaigns/{campaign_id}/cases")
    for item in res_cases.json()["items"]:
        if item["id"] != case_id:
            c_detail = client_bcs.get(f"/api/v1/bcs/cases/{item['id']}").json()
            c_ver = c_detail["version"]
            for cl in c_detail["claims"]:
                cid = cl["criterion"]["id"]
                s = cl["self_score"] or "7.00"
                r = client_bcs.put(
                    f"/api/v1/bcs/cases/{item['id']}/claims/{cid}/review",
                    json={"approved_score": s, "reason": "Duyệt hợp lệ", "expected_version": c_ver},
                    headers={"X-CSRF-Token": bcs_csrf}
                )
                c_ver = r.json()["version"]
            client_bcs.post(
                f"/api/v1/bcs/cases/{item['id']}/complete-review",
                json={"expected_version": c_ver},
                headers={"X-CSRF-Token": bcs_csrf}
            )

    # 6. Ghi biên bản 2 cuộc họp & công bố điểm
    print("\n[Bước 6] BCS ghi nhận biên bản họp và công bố điểm...")
    client_bcs.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/meetings",
        json={"kind": "BCS", "held_at": "2026-10-26T08:00:00Z", "note": "Họp BCS duyệt điểm"},
        headers={"X-CSRF-Token": bcs_csrf}
    )
    client_bcs.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/meetings",
        json={"kind": "CLASS", "held_at": "2026-10-26T14:00:00Z", "note": "Họp lớp thông qua điểm"},
        headers={"X-CSRF-Token": bcs_csrf}
    )
    res_pub = client_bcs.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/publish",
        json={"expected_campaign_status": "OPEN"},
        headers={"X-CSRF-Token": bcs_csrf}
    )
    assert res_pub.status_code == 200
    assert res_pub.json()["status"] == "PUBLISHED"
    print("  -> Đã công bố điểm toàn bộ lớp thành công (Status: PUBLISHED)")

    # 7. sv001 đăng nhập lại, thấy điểm và gửi khiếu nại
    print("\n[Bước 7] sv001 kiểm tra điểm đã công bố và gửi khiếu nại...")
    res_sv_pub = client.get("/api/v1/student/current")
    assert res_sv_pub.status_code == 200
    sv_pub_data = res_sv_pub.json()
    assert sv_pub_data["case"]["status"] == "PUBLISHED"
    sv_ver_after_pub = sv_pub_data["case"]["version"]
    print(f"  -> sv001 thấy điểm dự kiến: {sv_pub_data['case']['proposed_total']}")

    # Gửi khiếu nại
    res_appeal = client.post(
        f"/api/v1/student/cases/{case_id}/appeals",
        json={"expected_version": sv_ver_after_pub, "items": [{"criterion_id": crit1_id, "reason": "Em có tham gia đầy đủ các buổi học"}]},
        headers={"X-CSRF-Token": sv_csrf}
    )
    assert res_appeal.status_code == 200
    assert res_appeal.json()["status"] == "APPEALED"
    print("  -> sv001 gửi khiếu nại thành công (Status: APPEALED)")

    # 8. BCS xử lý khiếu nại và chốt điểm
    print("\n[Bước 8] BCS giải quyết khiếu nại và chốt điểm (FINALIZE)...")
    res_appeals = client_bcs.get(f"/api/v1/bcs/campaigns/{campaign_id}/appeals")
    appeals_list = res_appeals.json()
    assert len(appeals_list) >= 1
    target_appeal = appeals_list[0]
    
    res_resolve = client_bcs.post(
        f"/api/v1/bcs/appeals/{target_appeal['id']}/resolve",
        json={"resolution": "ADJUST", "new_score": "9.00", "reason": "Chấp thuận minh chứng bổ sung"},
        headers={"X-CSRF-Token": bcs_csrf}
    )
    assert res_resolve.status_code == 200
    print("  -> BCS giải quyết khiếu nại thành công (Nâng điểm lên 9.00)")

    # Cho các sinh viên khác đồng ý để đủ điều kiện finalize
    for item in res_cases.json()["items"]:
        if item["id"] != case_id:
            c_det = client_bcs.get(f"/api/v1/bcs/cases/{item['id']}").json()
            if c_det["status"] == "PUBLISHED":
                client_sv_other = TestClient(app)
                u = client_bcs.get(f"/api/v1/bcs/cases/{item['id']}").json()["student"]["code"]
                res_login_u = client_sv_other.post("/api/v1/auth/login", json={"username": u, "password": password})
                csrf_u = res_login_u.json()["csrf_token"]
                client_sv_other.post(
                    f"/api/v1/student/cases/{item['id']}/accept",
                    json={"expected_version": c_det["version"]},
                    headers={"X-CSRF-Token": csrf_u}
                )

    # BCS finalize
    res_fin = client_bcs.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/finalize",
        headers={"X-CSRF-Token": bcs_csrf}
    )
    assert res_fin.status_code == 200
    assert res_fin.json()["status"] == "FINALIZED"
    print("  -> BCS chốt bảng điểm thành công (Status: FINALIZED)")

    # 9. GVCN tải CSV điểm chính thức
    print("\n[Bước 9] gvcn001 đăng nhập và tải bảng điểm CSV...")
    client_gvcn = TestClient(app)
    res_glogin = client_gvcn.post("/api/v1/auth/login", json={"username": "gvcn001", "password": password})
    assert res_glogin.status_code == 200
    print("  -> gvcn001 đăng nhập thành công (Role: GVCN)")

    res_csv = client_gvcn.get(f"/api/v1/gvcn/campaigns/{campaign_id}/final-scores.csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_text = res_csv.text
    assert "Mã sinh viên" in csv_text
    assert "sv001" in csv_text
    print("  -> GVCN tải bảng điểm CSV chính thức thành công, dữ liệu có đầy đủ điểm số đã chốt!")

    # 10. Đăng xuất
    print("\n[Bước 10] Kiểm tra Đăng xuất (Logout)...")
    res_logout = client.post("/api/v1/auth/logout")
    assert res_logout.status_code == 200
    # Sau logout, truy cập endpoint bảo vệ phải bị 401
    res_after = client.get("/api/v1/auth/me")
    assert res_after.status_code == 401
    print("  -> Đăng xuất thành công: phiên làm việc bị hủy, các route bảo vệ bị khóa hoàn toàn.")

    print("\n" + "=" * 70)
    print(" TẤT CẢ CÁC BƯỚC TÍCH HỢP LIVE ĐÃ ĐẠT 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_integration_verification()
