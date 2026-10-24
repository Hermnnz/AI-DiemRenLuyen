"""
Kịch bản Demo Đầu-Cuối (End-to-End User Journey) cho Web Chấm Điểm Rèn Luyện V1.
Quy trình nghiệp vụ hoàn chỉnh:
1. Migration & Seed dữ liệu mẫu
2. ADMIN mở đợt đánh giá
3. Sinh viên tự chấm điểm, tải minh chứng và nộp hồ sơ
4. BCS kiểm tra thủ công, chấm điểm từng tiêu chí kèm lý do, tính điểm dự kiến
5. BCS ghi nhận biên bản 2 cuộc họp (BCS & Lớp)
6. BCS công bố điểm dự kiến công khai, mở thời hạn khiếu nại
7. Sinh viên xem bảng so sánh điểm: sv001 Đồng ý, sv002 Khiếu nại
8. BCS xem xét và giải quyết khiếu nại (ADJUST điểm)
9. BCS chốt điểm cả lớp (FINALIZED)
10. GVCN xem bảng điểm chính thức và xuất tệp CSV
"""
import io
import os
import sys
from datetime import datetime, timezone

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tests.fixtures.client import AcceptanceTestClient


def run_demo():
    print("=" * 70)
    print("🚀 BẮT ĐẦU KỊCH BẢN DEMO ĐẦU-CUỐI (E2E WORKFLOW) V1")
    print("   Hệ thống: Web Chấm Điểm Rèn Luyện (Không AI)")
    print("=" * 70)

    client = AcceptanceTestClient()
    campaign_id = "33333333-3333-3333-3333-333333333333"

    # -------------------------------------------------------------
    # BƯỚC 1: ADMIN LÊN LỊCH & MỞ ĐỢT ĐÁNH GIÁ
    # -------------------------------------------------------------
    print("\n[Bước 1] ADMIN ĐĂNG NHẬP VÀ MỞ ĐỢT ĐÁNH GIÁ...")
    client.login_as_admin("admin001")
    res_open = client.post(f"/api/v1/admin/campaigns/{campaign_id}/open")
    if res_open.status_code == 200:
        print(f"  ✓ Đợt đánh giá đã được mở thành công. Trạng thái: {res_open.json().get('status')}")
    else:
        print(f"  ℹ Đợt đánh giá đã ở trạng thái: {res_open.status_code}")

    # -------------------------------------------------------------
    # BƯỚC 2: SINH VIÊN TỰ CHẤM ĐIỂM, TẢI MINH CHỨNG VÀ NỘP HỒ SƠ
    # -------------------------------------------------------------
    print("\n[Bước 2] SINH VIÊN TỰ CHẤM ĐIỂM VÀ NỘP HỒ SƠ...")
    students = [
        {"username": "sv001", "scores": {"TC01": "9.00", "TC02": "8.50", "TC03": "9.00"}},
        {"username": "sv002", "scores": {"TC01": "7.50", "TC02": "8.00", "TC03": "7.00"}},
        {"username": "sv003", "scores": {"TC01": "8.00", "TC02": "8.00", "TC03": "8.00"}},
    ]

    for st in students:
        client.logout()
        client.login_as_student(st["username"])
        current_data = client.get("/api/v1/student/current").json()
        case_id = current_data["case"]["id"]
        version = current_data["case"]["version"]
        criteria = current_data["criteria"]

        # Điền điểm và upload minh chứng
        for crit in criteria:
            code = crit["code"]
            score = st["scores"].get(code, "8.00")
            put_res = client.put(
                f"/api/v1/student/cases/{case_id}/claims/{crit['id']}",
                json={"self_score": score, "student_note": f"Tự đánh giá {code}", "expected_version": version}
            )
            version = put_res.json().get("version", version + 1)

            if crit.get("requires_evidence"):
                pdf_bytes = io.BytesIO(f"%PDF-1.4 sample evidence for {st['username']} - {code}".encode("utf-8"))
                client.post(
                    f"/api/v1/student/cases/{case_id}/evidence",
                    data={"criterion_id": crit["id"]},
                    files={"file": (f"minh_chung_{code}.pdf", pdf_bytes, "application/pdf")}
                )

        # Nộp hồ sơ
        submit_res = client.post(
            f"/api/v1/student/cases/{case_id}/submit",
            json={"expected_version": version}
        )
        assert submit_res.status_code == 200
        sub_data = submit_res.json()
        print(f"  ✓ Sinh viên {st['username']} nộp hồ sơ thành công -> Trạng thái: {sub_data['status']} (Tổng điểm tự khai: {sub_data.get('claimed_total')} đ)")

    # -------------------------------------------------------------
    # BƯỚC 3: BCS KIỂM TRA THỦ CÔNG VÀ CHẤM ĐIỂM DỰ KIẾN (3 VÙNG)
    # -------------------------------------------------------------
    print("\n[Bước 3] BAN CÁN SỰ (BCS) ĐÁNH GIÁ THỦ CÔNG TỪNG TIÊU CHÍ...")
    client.logout()
    client.login_as_bcs("bcs001")

    cases_res = client.get(f"/api/v1/bcs/campaigns/{campaign_id}/cases").json()
    case_list = cases_res.get("items", []) if isinstance(cases_res, dict) else cases_res

    for c_item in case_list:
        c_id = c_item["id"]
        detail = client.get(f"/api/v1/bcs/cases/{c_id}").json()
        ver = detail["version"]
        st_name = detail["student"]["full_name"]
        st_code = detail["student"]["code"]

        # Duyệt từng claim
        for cl in detail["claims"]:
            crit_code = cl["criterion"]["code"]
            self_sc = float(cl["self_score"] or 8.0)

            # Chấm điểm duyệt: nếu sv001 điều chỉnh giảm nhẹ có lý do giải trình
            if "sv001" in st_code.lower() and crit_code == "TC01":
                appr_sc = "8.00"
                reason = "Minh chứng chỉ đạt 80% tiêu chuẩn theo quy chế"
            else:
                appr_sc = f"{self_sc:.2f}"
                reason = None

            res_review = client.put(
                f"/api/v1/bcs/cases/{c_id}/claims/{cl['criterion']['id']}/review",
                json={"approved_score": appr_sc, "reason": reason, "expected_version": ver}
            )
            assert res_review.status_code == 200
            ver = res_review.json().get("version", ver + 1)

        # Hoàn tất đánh giá hồ sơ
        comp_res = client.post(
            f"/api/v1/bcs/cases/{c_id}/complete-review",
            json={"expected_version": ver}
        )
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        print(f"  ✓ BCS hoàn tất đánh giá cho SV {st_name} -> Trạng thái: {comp_data['status']}, Điểm dự kiến: {comp_data['proposed_total']} đ")

    # -------------------------------------------------------------
    # BƯỚC 4: GHI NHẬN 2 BIÊN BẢN HỌP BÌNH XÉT (BCS & LỚP)
    # -------------------------------------------------------------
    print("\n[Bước 4] BCS GHI NHẬN BIÊN BẢN 2 CUỘC HỌP BÌNH XÉT BẮT BUỘC...")
    m1 = client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/meetings",
        json={"kind": "BCS", "held_at": datetime.now(timezone.utc).isoformat(), "note": "Họp Ban cán sự lớp thống nhất điểm dự kiến"}
    )
    assert m1.status_code in [200, 201]
    print("  ✓ Đã ghi nhận cuộc họp Ban Cán Sự (kind=BCS)")

    m2 = client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/meetings",
        json={"kind": "CLASS", "held_at": datetime.now(timezone.utc).isoformat(), "note": "Họp toàn thể sinh viên trong lớp bình xét điểm"}
    )
    assert m2.status_code in [200, 201]
    print("  ✓ Đã ghi nhận cuộc họp Toàn thể Lớp (kind=CLASS)")

    # -------------------------------------------------------------
    # BƯỚC 5: CÔNG BỐ ĐIỂM DỰ KIẾN (PUBLISHED)
    # -------------------------------------------------------------
    print("\n[Bước 5] BCS CÔNG BỐ BẢNG ĐIỂM DỰ KIẾN CHO CẢ LỚP...")
    ov = client.get(f"/api/v1/bcs/campaigns/{campaign_id}/overview").json()
    curr_camp_status = ov.get("status", "OPEN")
    pub_res = client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/publish",
        json={"expected_campaign_status": curr_camp_status}
    )
    assert pub_res.status_code == 200
    print("  ✓ Đợt đánh giá đã chuyển sang PUBLISHED. Thời hạn phản hồi/khiếu nại đã được kích hoạt!")

    # -------------------------------------------------------------
    # BƯỚC 6: SINH VIÊN PHẢN HỒI (ĐỒNG Ý HOẶC KHIẾU NẠI)
    # -------------------------------------------------------------
    print("\n[Bước 6] SINH VIÊN XEM KẾT QUẢ VÀ PHẢN HỒI...")
    # 6.1: sv001 xem bảng so sánh và bấm Đồng ý
    client.logout()
    client.login_as_student("sv001")
    sv1_curr = client.get("/api/v1/student/current").json()
    assert sv1_curr["case"]["proposed_total"] is not None
    acc_res = client.post(
        f"/api/v1/student/cases/{sv1_curr['case']['id']}/accept",
        json={"expected_version": sv1_curr["case"]["version"]}
    )
    assert acc_res.status_code == 200
    print(f"  ✓ Sinh viên sv001 đã xác nhận ĐỒNG Ý điểm dự kiến ({sv1_curr['case']['proposed_total']} đ) -> ACCEPTED")

    # 6.2: sv002 gửi khiếu nại
    client.logout()
    client.login_as_student("sv002")
    sv2_curr = client.get("/api/v1/student/current").json()
    crit_tc01 = sv2_curr["criteria"][0]
    app_res = client.post(
        f"/api/v1/student/cases/{sv2_curr['case']['id']}/appeals",
        json={
            "items": [{"criterion_id": crit_tc01["id"], "reason": "Em có tham gia NCKH bổ sung, xin xem xét nâng điểm"}],
            "expected_version": sv2_curr["case"]["version"]
        }
    )
    assert app_res.status_code == 200
    print(f"  ✓ Sinh viên sv002 đã gửi KHIẾU NẠI tiêu chí {crit_tc01['code']} -> APPEALED")

    # 6.3: sv003 xem kết quả và bấm Đồng ý
    client.logout()
    client.login_as_student("sv003")
    sv3_curr = client.get("/api/v1/student/current").json()
    acc3_res = client.post(
        f"/api/v1/student/cases/{sv3_curr['case']['id']}/accept",
        json={"expected_version": sv3_curr["case"]["version"]}
    )
    assert acc3_res.status_code == 200
    print(f"  ✓ Sinh viên sv003 đã xác nhận ĐỒNG Ý điểm dự kiến ({sv3_curr['case']['proposed_total']} đ) -> ACCEPTED")

    # -------------------------------------------------------------
    # BƯỚC 7: BCS XEM XÉT VÀ GIẢI QUYẾT KHIẾU NẠI
    # -------------------------------------------------------------
    print("\n[Bước 7] BCS GIẢI QUYẾT KHIẾU NẠI VÀ ĐIỀU CHỈNH ĐIỂM...")
    client.logout()
    client.login_as_bcs("bcs001")
    appeals_res = client.get(f"/api/v1/bcs/campaigns/{campaign_id}/appeals").json()
    appeals_list = appeals_res if isinstance(appeals_res, list) else appeals_res.get("items", [])
    open_appeal = [a for a in appeals_list if a["status"] == "OPEN"][0]

    resolve_res = client.post(
        f"/api/v1/bcs/appeals/{open_appeal['id']}/resolve",
        json={
            "resolution": "ADJUST",
            "new_score": "8.50",
            "reason": "BCS đã thẩm tra lại giấy xác nhận NCKH hợp lệ, đồng ý điều chỉnh lên 8.50 điểm"
        }
    )
    assert resolve_res.status_code == 200
    print(f"  ✓ BCS giải quyết khiếu nại thành công: ADJUST -> 8.50 đ (Lý do: giấy xác nhận hợp lệ)")

    # -------------------------------------------------------------
    # BƯỚC 8: BCS CHỐT ĐIỂM CẢ LỚP (FINALIZED)
    # -------------------------------------------------------------
    print("\n[Bước 8] BCS CHỐT ĐIỂM CHÍNH THỨC TOÀN BỘ LỚP...")
    fin_res = client.post(
        f"/api/v1/bcs/campaigns/{campaign_id}/finalize",
        json={"expected_campaign_status": "PUBLISHED"}
    )
    assert fin_res.status_code == 200
    print("  ✓ Đợt đánh giá đã được CHỐT THÀNH CÔNG (status: FINALIZED)! Điểm chính thức đã được lưu vĩnh viễn.")

    # -------------------------------------------------------------
    # BƯỚC 9: GVCN XEM BẢNG ĐIỂM CHÍNH THỨC VÀ XUẤT CSV
    # -------------------------------------------------------------
    print("\n[Bước 9] GIẢNG VIÊN CHỦ NHIỆM (GVCN) TẢI VÀ XEM BẢNG ĐIỂM CHÍNH THỨC (CSV)...")
    client.logout()
    client.login_as_gvcn("gvcn001")

    # Tải file CSV
    csv_res = client.get(f"/api/v1/gvcn/campaigns/{campaign_id}/final-scores.csv")
    assert csv_res.status_code == 200
    csv_content = csv_res.content.decode("utf-8-sig")
    lines = [line.strip() for line in csv_content.splitlines() if line.strip()]

    print(f"  ✓ Tải tệp CSV thành công ({len(csv_res.content)} bytes). Nội dung bảng điểm chính thức:")
    print("    " + "-" * 72)
    for i, line in enumerate(lines):
        if i == 0:
            print(f"    [TIÊU ĐỀ] {line}")
            print("    " + "-" * 72)
        else:
            print(f"    [DÒNG {i}]   {line}")
    print("    " + "-" * 72)

    print("\n" + "=" * 70)
    print("🎉 KỊCH BẢN DEMO ĐẦU-CUỐI ĐÃ HOÀN THÀNH 100% THÀNH CÔNG RỰC RỠ!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
