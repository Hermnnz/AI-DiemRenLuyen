import os
import sys
import time
from datetime import datetime, timezone, timedelta

# Ensure root is in path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright, expect
from api.app.database import SessionLocal
from api.app.models import (
    Campaign,
    Case,
    Claim,
    Appeal,
    EvidenceFile,
    Meeting,
    Notification,
    AuditEvent,
    SupplementRequest,
    User,
    Class
)
from api.app.security import hash_password

BASE_URL = "http://127.0.0.1:5173"
DEMO_PASS = os.getenv("DEMO_PASSWORD", "Demo@123456")

def reset_db_to_clean_draft():
    """Reset the database to a clean campaign in DRAFT mode for Admin to open."""
    db = SessionLocal()
    try:
        print("[DB-Reset] Dọn dẹp dữ liệu giao dịch cũ...")
        db.query(Appeal).delete()
        db.query(SupplementRequest).delete()
        db.query(Claim).delete()
        db.query(Case).delete()
        db.query(EvidenceFile).delete()
        db.query(Meeting).delete()
        db.query(Notification).delete()
        db.query(AuditEvent).delete()
        
        # Reset default campaign
        c = db.query(Campaign).first()
        if c:
            now = datetime.now(timezone.utc)
            c.status = "DRAFT"
            c.open_at = now - timedelta(hours=1)
            c.submission_deadline_at = now + timedelta(days=7)
            db.commit()
            print(f"[DB-Reset] Đợt đánh giá [{c.title}] đã đặt về trạng thái DRAFT thành công.")
        else:
            raise RuntimeError("Không tìm thấy đợt đánh giá nào trong DB.")
    finally:
        db.close()


def run_browser_suite():
    console_errors = []
    
    reset_db_to_clean_draft()

    with sync_playwright() as p:
        print("\n[Playwright] Khởi chạy Google Chrome (Headless)...")
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Listen to console and page errors
        def handle_console(msg):
            if msg.type == "error":
                text = msg.text
                # Bỏ qua các log HTTP status network tự nhiên của browser khi test sai pass (401) hoặc logout/chưa mở đợt (404)
                if not any(ign in text for ign in ["favicon", "net::ERR", "Failed to load resource"]):
                    console_errors.append(f"Console error: {text}")

        def handle_pageerror(err):
            console_errors.append(f"Page unhandled error: {err}")

        page.on("console", handle_console)
        page.on("pageerror", handle_pageerror)

        # ----------------------------------------------------------------------
        # PHẦN 1: RÀ SOÁT CÁC TÌNH HUỐNG LỖI VÀ BẢO MẬT GIAO DIỆN (UI ERROR & RBAC)
        # ----------------------------------------------------------------------
        print("\n=======================================================")
        print(" PHẦN 1: KIỂM CHỨNG LỖI NGƯỜI DÙNG & PHÂN QUYỀN TRÊN UI")
        print("=======================================================")

        # 1.1 Sai mật khẩu
        print("\n[1.1] Kiểm tra đăng nhập sai mật khẩu...")
        page.goto(f"{BASE_URL}/login")
        page.fill('input[type="text"]', "sv001")
        page.fill('input[type="password"]', "MatKhauSai@999")
        page.click('button[type="submit"]')
        page.wait_for_selector(':has-text("Tên đăng nhập hoặc mật khẩu không chính xác")')
        assert "/login" in page.url, "URL phải vẫn ở /login khi đăng nhập sai!"
        print("  -> Bắt lỗi đăng nhập sai mật khẩu chuẩn xác qua UI.")

        # 1.2 Đăng nhập đúng và kiểm tra Route Guard / 403 Forbidden
        print("\n[1.2] Kiểm tra Phân quyền Tuyến đường (Route Guard 403)...")
        page.fill('input[type="text"]', "sv001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")
        print("  -> sv001 đăng nhập thành công vào giao diện sinh viên.")

        # Sinh viên cố tình gõ URL của BCS
        page.goto(f"{BASE_URL}/bcs")
        page.wait_for_selector(':has-text("403 — Không có quyền truy cập")')
        print("  -> sv001 vào /bcs bị chặn 403 Forbidden chính xác.")

        # Sinh viên cố tình gõ URL của Admin
        page.goto(f"{BASE_URL}/admin/campaigns")
        page.wait_for_selector(':has-text("403 — Không có quyền truy cập")')
        print("  -> sv001 vào /admin/campaigns bị chặn 403 Forbidden chính xác.")

        # Đăng xuất
        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")
        print("  -> Đăng xuất thành công, chuyển hướng về /login.")

        # 1.3 Rà soát Giao diện Responsive & Tràn ngang (CSS Overflow Check)
        print("\n[1.3] Rà soát Giao diện Responsive trên nhiều độ phân giải...")

        # Kích thước 390px (Mobile - iPhone 12/13/14)
        print("  * Kiểm tra ở kích thước Mobile 390px...")
        page.set_viewport_size({"width": 390, "height": 844})
        page.fill('input[type="text"]', "sv001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        # Kiểm tra tràn ngang trang Dashboard ở 390px
        is_overflowing_390 = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        print(f"    - Dashboard SV ở 390px: {'TRÀN NGANG' if is_overflowing_390 else 'Chuẩn responsive, không tràn ngang'}")
        assert not is_overflowing_390, "Dashboard bị tràn ngang ở 390px!"

        # Kích thước 768px (Tablet - iPad)
        print("  * Kiểm tra ở kích thước Tablet 768px...")
        page.set_viewport_size({"width": 768, "height": 1024})
        is_overflowing_768 = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        print(f"    - Dashboard SV ở 768px: {'TRÀN NGANG' if is_overflowing_768 else 'Chuẩn responsive, không tràn ngang'}")
        assert not is_overflowing_768, "Dashboard bị tràn ngang ở 768px!"

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # Kích thước 1366px (Desktop Laptop cho BCS)
        print("  * Kiểm tra ở kích thước Desktop 1366px (BCS)...")
        page.set_viewport_size({"width": 1366, "height": 768})
        page.fill('input[type="text"]', "bcs001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/bcs*")
        is_overflowing_1366 = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        print(f"    - Dashboard BCS ở 1366px: {'TRÀN NGANG' if is_overflowing_1366 else 'Chuẩn layout, không tràn ngang'}")
        assert not is_overflowing_1366, "BCS Dashboard bị tràn ngang ở 1366px!"

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # ----------------------------------------------------------------------
        # PHẦN 2: CHU TRÌNH ĐẦU-CUỐI HOÀN CHỈNH BẰNG TRÌNH DUYỆT (LIVE BROWSER E2E)
        # ADMIN -> SV001 & SV002 -> BCS -> SV001 & SV002 -> BCS -> GVCN
        # ----------------------------------------------------------------------
        print("\n=======================================================")
        print(" PHẦN 2: CHU TRÌNH ĐẦU-CUỐI TRÊN BROWSER (DATABASE THỰC)")
        print("=======================================================")

        # BƯỚC 1: ADMIN LÊN LỊCH / MỞ ĐỢT ĐÁNH GIÁ TRÊN UI
        print("\n[Bước 1] ADMIN đăng nhập và Mở đợt đánh giá...")
        page.set_viewport_size({"width": 1280, "height": 800})
        page.fill('input[type="text"]', "admin001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/admin/campaigns")
        page.wait_for_selector(':has-text("Quản trị Cấu hình Đợt Đánh giá")')

        # Click nút Lên lịch / Mở đợt
        open_btn = page.locator('button:has-text("Lên lịch / Mở đợt")')
        expect(open_btn).to_be_visible()
        open_btn.click()

        # Xác nhận trong ConfirmDialog
        page.wait_for_selector(':has-text("Xác nhận Lên lịch / Mở đợt đánh giá")')
        page.locator('button:has-text("Tiến hành Lên lịch/Mở")').click()

        # Chờ thông báo thành công
        page.wait_for_selector(':has-text("Đợt đánh giá đã chính thức MỞ")')
        print("  -> Admin đã mở đợt đánh giá thành công trên UI!")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 2: SV001 TỰ CHẤM, TẢI MINH CHỨNG & NỘP HỒ SƠ
        print("\n[Bước 2] Sinh viên sv001 tự chấm điểm và nộp hồ sơ...")
        page.fill('input[type="text"]', "sv001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        # Kiểm tra hiển thị thông tin sinh viên
        page.wait_for_selector(':has-text("Nguyễn Văn An")')
        print("  -> sv001 đã vào Dashboard, thấy tên: Nguyễn Văn An.")

        # Đi tới form nộp hồ sơ
        page.click('a[href="/student/submission"]')
        page.wait_for_url(f"{BASE_URL}/student/submission")

        # 2a. Thử nghiệm tải tệp không đúng định dạng (.txt)
        print("  * Kiểm thử validation tệp: tải tệp .txt sai định dạng...")
        txt_path = os.path.join(ROOT_DIR, "storage", "test_files", "sample.txt")
        file_inputs = page.locator('input[type="file"]')
        file_inputs.nth(0).set_input_files(txt_path)
        page.wait_for_selector(':has-text("Chỉ hỗ trợ tệp định dạng PDF, JPG hoặc PNG.")')
        print("    -> Form từ chối tệp sai định dạng chuẩn xác.")

        # 2b. Tải tệp hợp lệ cho TC01 (PDF) và TC03 (PNG)
        pdf_path = os.path.join(ROOT_DIR, "storage", "test_files", "sample.pdf")
        png_path = os.path.join(ROOT_DIR, "storage", "test_files", "sample.png")

        print("  * Tải tệp PDF thật cho TC01...")
        file_inputs.nth(0).set_input_files(pdf_path)
        page.wait_for_selector(':has-text("sample.pdf")')

        print("  * Tải tệp PNG thật cho TC03...")
        file_inputs.nth(2).set_input_files(png_path)
        page.wait_for_selector(':has-text("sample.png")')

        # 2c. Nhập điểm tự chấm cho 3 tiêu chí
        # TC01: 9.00
        score_inputs = page.locator('input[placeholder="0.00"]')
        score_inputs.nth(0).fill("9.00")
        # TC02: 8.00
        score_inputs.nth(1).fill("8.00")
        # TC03: 7.00
        score_inputs.nth(2).fill("7.00")

        # Lưu bản nháp
        print("  * Lưu bản nháp...")
        page.click('button:has-text("Lưu nháp")')
        page.wait_for_selector(':has-text("Đã lưu bản nháp thành công!")')

        # Nộp hồ sơ
        print("  * Nộp hồ sơ vào BCS_REVIEW...")
        page.click('button:has-text("Nộp hồ sơ")')
        page.wait_for_selector(':has-text("Xác nhận nộp hồ sơ rèn luyện")')
        page.locator('button:has-text("Đồng ý nộp")').click()
        page.wait_for_selector(':has-text("Nộp hồ sơ thành công!")')
        print("  -> sv001 đã nộp hồ sơ thành công vào hàng chờ chấm.")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 3: SV002 TỰ CHẤM & NỘP HỒ SƠ (KIỂM TRA CÁCH LY DỮ LIỆU ĐỘC LẬP)
        print("\n[Bước 3] Sinh viên sv002 đăng nhập (Kiểm tra cách ly dữ liệu)...")
        page.fill('input[type="text"]', "sv002")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        # Phải thấy Trần Thị Bình, không được thấy Nguyễn Văn An
        page.wait_for_selector(':has-text("Trần Thị Bình")')
        assert not page.locator('text="Nguyễn Văn An"').is_visible(), "Dữ liệu sinh viên bị lẫn lộn giữa sv001 và sv002!"
        print("  -> Dữ liệu cách ly tuyệt đối: sv002 chỉ thấy hồ sơ của chính mình.")

        page.click('a[href="/student/submission"]')
        page.wait_for_url(f"{BASE_URL}/student/submission")

        # Tải tệp và điền điểm cho sv002
        file_inputs = page.locator('input[type="file"]')
        file_inputs.nth(0).set_input_files(pdf_path)
        page.wait_for_selector(':has-text("sample.pdf")')

        file_inputs.nth(2).set_input_files(png_path)
        page.wait_for_selector(':has-text("sample.png")')

        score_inputs = page.locator('input[placeholder="0.00"]')
        score_inputs.nth(0).fill("10.00")
        score_inputs.nth(1).fill("8.00")
        score_inputs.nth(2).fill("7.00")

        page.click('button:has-text("Nộp hồ sơ")')
        page.wait_for_selector(':has-text("Xác nhận nộp hồ sơ rèn luyện")')
        page.locator('button:has-text("Đồng ý nộp")').click()
        page.wait_for_selector(':has-text("Nộp hồ sơ thành công!")')
        print("  -> sv002 đã hoàn tất nộp hồ sơ thành công.")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 3b: SV003 TỰ CHẤM & NỘP HỒ SƠ
        print("\n[Bước 3b] Sinh viên sv003 đăng nhập và nộp hồ sơ...")
        page.fill('input[type="text"]', "sv003")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        page.click('a[href="/student/submission"]')
        page.wait_for_url(f"{BASE_URL}/student/submission")

        file_inputs = page.locator('input[type="file"]')
        file_inputs.nth(0).set_input_files(pdf_path)
        page.wait_for_selector(':has-text("sample.pdf")')

        file_inputs.nth(2).set_input_files(png_path)
        page.wait_for_selector(':has-text("sample.png")')

        score_inputs = page.locator('input[placeholder="0.00"]')
        score_inputs.nth(0).fill("8.00")
        score_inputs.nth(1).fill("8.00")
        score_inputs.nth(2).fill("8.00")

        page.click('button:has-text("Nộp hồ sơ")')
        page.wait_for_selector(':has-text("Xác nhận nộp hồ sơ rèn luyện")')
        page.locator('button:has-text("Đồng ý nộp")').click()
        page.wait_for_selector(':has-text("Nộp hồ sơ thành công!")')
        print("  -> sv003 đã hoàn tất nộp hồ sơ thành công.")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 4: BCS DUYỆT ĐIỂM, XEM MINH CHỨNG THẬT & CÔNG BỐ
        print("\n[Bước 4] BCS đăng nhập để duyệt điểm hồ sơ...")
        page.fill('input[type="text"]', "bcs001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/bcs*")

        # Chuyển sang trang Hàng chờ hồ sơ
        page.click('a[href="/bcs/cases"]')
        page.wait_for_url(f"{BASE_URL}/bcs/cases")
        page.wait_for_selector(':has-text("Hàng chờ Hồ sơ Rèn luyện Lớp")')

        # Cả sv001, sv002, sv003 đều phải xuất hiện trong bảng
        page.wait_for_selector('text="sv001"')
        page.wait_for_selector('text="sv002"')
        page.wait_for_selector('text="sv003"')
        print("  -> BCS thấy cả ba hồ sơ của sv001, sv002 và sv003 trong hàng chờ.")

        # 4a. Duyệt hồ sơ của sv001
        print("  * Duyệt hồ sơ sv001 (Kiểm tra 3 vùng & xem tệp minh chứng)...")
        page.click('tr:has-text("sv001") a:has-text("Kiểm tra")')
        page.wait_for_url("**/bcs/cases/*")
        page.wait_for_selector(':has-text("Hồ sơ: sv001 · Nguyễn Văn An")')

        # Bấm xem tệp an toàn trong Vùng 1
        page.click('button:has-text("Xem an toàn")')
        page.wait_for_selector(':has-text("Xem trước minh chứng an toàn")')
        page.locator('button:has-text("Đóng")').click()
        print("    -> Modal xem tệp minh chứng an toàn mở và đóng chuẩn xác.")

        # Điều chỉnh điểm TC01 từ 9.00 xuống 8.00 và ghi lý do
        score_inputs = page.locator('input[type="text"][style*="text-align: right"]')
        reason_inputs = page.locator('input[placeholder*="lý do"], input[placeholder*="Lý do"]')
        save_buttons = page.locator('button[title="Lưu tiêu chí này"]')

        score_inputs.nth(0).fill("8.00")
        reason_inputs.nth(0).fill("Chưa đủ số giờ tình nguyện theo quy định")
        save_buttons.nth(0).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC01].")')
        print("    -> Đã chấm duyệt TC01 (8.00) có lý do hợp lệ.")

        # Lưu điểm cho TC02 và TC03
        save_buttons.nth(1).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC02].")')
        save_buttons.nth(2).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC03].")')
        print("    -> Đã lưu điểm duyệt đầy đủ cho TC02 và TC03.")

        # Hoàn tất kiểm tra hồ sơ sv001 -> PROPOSED
        page.click('button:has-text("Hoàn tất kiểm tra")')
        page.wait_for_selector(':has-text("Xác nhận Hoàn tất Kiểm tra Hồ sơ")')
        page.locator('button:has-text("Xác nhận hoàn tất")').click()
        page.wait_for_selector(':has-text("Đã hoàn tất kiểm tra hồ sơ")')
        expect(page.locator('text="Xác nhận Hoàn tất Kiểm tra Hồ sơ"')).not_to_be_visible()
        print("    -> Hồ sơ sv001 chuyển sang PROPOSED thành công.")

        # 4b. Duyệt hồ sơ của sv002
        print("  * Duyệt hồ sơ sv002...")
        page.click('a:has-text("Quay lại hàng chờ")')
        page.wait_for_url(f"{BASE_URL}/bcs/cases")
        page.click('tr:has-text("sv002") a:has-text("Kiểm tra")')
        page.wait_for_url("**/bcs/cases/*")
        page.wait_for_selector(':has-text("Hồ sơ: sv002 · Trần Thị Bình")')

        save_buttons = page.locator('button[title="Lưu tiêu chí này"]')
        save_buttons.nth(0).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC01].")')
        save_buttons.nth(1).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC02].")')
        save_buttons.nth(2).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC03].")')

        page.click('button:has-text("Hoàn tất kiểm tra")')
        page.wait_for_selector(':has-text("Xác nhận Hoàn tất Kiểm tra Hồ sơ")')
        page.locator('button:has-text("Xác nhận hoàn tất")').click()
        page.wait_for_selector(':has-text("Đã hoàn tất kiểm tra hồ sơ")')
        expect(page.locator('text="Xác nhận Hoàn tất Kiểm tra Hồ sơ"')).not_to_be_visible()
        print("    -> Hồ sơ sv002 chuyển sang PROPOSED thành công.")

        # 4c. Duyệt hồ sơ của sv003
        print("  * Duyệt hồ sơ sv003...")
        page.click('a:has-text("Quay lại hàng chờ")')
        page.wait_for_url(f"{BASE_URL}/bcs/cases")
        page.click('tr:has-text("sv003") a:has-text("Kiểm tra")')
        page.wait_for_url("**/bcs/cases/*")
        page.wait_for_selector(':has-text("Hồ sơ: sv003")')

        save_buttons = page.locator('button[title="Lưu tiêu chí này"]')
        save_buttons.nth(0).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC01].")')
        save_buttons.nth(1).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC02].")')
        save_buttons.nth(2).click()
        page.wait_for_selector(':has-text("Đã lưu quyết định chấm tiêu chí [TC03].")')

        page.click('button:has-text("Hoàn tất kiểm tra")')
        page.wait_for_selector(':has-text("Xác nhận Hoàn tất Kiểm tra Hồ sơ")')
        page.locator('button:has-text("Xác nhận hoàn tất")').click()
        page.wait_for_selector(':has-text("Đã hoàn tất kiểm tra hồ sơ")')
        expect(page.locator('text="Xác nhận Hoàn tất Kiểm tra Hồ sơ"')).not_to_be_visible()
        print("    -> Hồ sơ sv003 chuyển sang PROPOSED thành công.")

        # 4d. Ghi nhận biên bản 2 cuộc họp và Công bố điểm
        print("  * Chuyển sang Bảng điểm & Công bố...")
        page.click('a[href="/bcs/scores"]')
        page.wait_for_url(f"{BASE_URL}/bcs/scores")

        # Kiểm tra nút Công bố bị disable khi chưa đủ 2 cuộc họp
        pub_btn = page.locator('button[data-testid="publish-scores-btn"]')
        assert pub_btn.is_disabled(), "Nút công bố điểm phải bị khóa khi chưa đủ 2 cuộc họp!"
        print("    -> Cổng công bố điểm bị khóa đúng quy định khi chưa họp.")

        # Ghi nhận cuộc họp BCS
        print("    - Ghi nhận cuộc họp Ban cán sự...")
        page.click('button[data-testid="record-bcs-meeting"]')
        page.wait_for_selector(':has-text("Biên bản Họp Bình xét")')
        page.locator('button:has-text("Lưu biên bản họp")').click()
        page.wait_for_selector(':has-text("Đã ghi nhận biên bản cuộc họp: Họp Ban cán sự.")')

        # Ghi nhận cuộc họp LỚP
        print("    - Ghi nhận cuộc họp Toàn thể Lớp...")
        page.click('button[data-testid="record-class-meeting"]')
        page.wait_for_selector(':has-text("Biên bản Họp Bình xét")')
        page.locator('button:has-text("Lưu biên bản họp")').click()
        page.wait_for_selector(':has-text("Đã ghi nhận biên bản cuộc họp: Họp toàn thể Lớp.")')

        # Nút Công bố điểm mở khóa
        expect(pub_btn).to_be_enabled()
        print("    -> Đủ 2 cuộc họp và tất cả hồ sơ PROPOSED: nút Công bố điểm đã mở khóa!")

        pub_btn.click()
        page.wait_for_selector(':has-text("Xác nhận công bố điểm rèn luyện dự kiến")')
        page.locator('button:has-text("Công bố ngay")').click()
        page.wait_for_selector(':has-text("Đã công bố điểm rèn luyện dự kiến")')
        print("  -> Điểm đã được CÔNG BỐ (PUBLISHED) toàn lớp.")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 5: SV001 XEM ĐIỂM ĐÃ CÔNG BỐ VÀ GỬI KHIẾU NẠI
        print("\n[Bước 5] sv001 xem kết quả dự kiến và gửi Khiếu nại...")
        page.fill('input[type="text"]', "sv001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        page.click('a[href="/student/result"]')
        page.wait_for_url(f"{BASE_URL}/student/result")

        # sv001 thấy điểm dự kiến 23.00 và lý do bị trừ của BCS
        page.wait_for_selector('text="23.00"')
        page.wait_for_selector(':has-text("Chưa đủ số giờ tình nguyện theo quy định")')
        print("  -> sv001 thấy đúng điểm công bố 23.00 và lý do chấm của BCS.")

        # Bấm gửi khiếu nại
        page.click('button:has-text("Khiếu nại điểm")')
        page.wait_for_url(f"{BASE_URL}/student/appeal")

        # Nhập lý do khiếu nại cho TC01
        reason_area = page.locator('textarea')
        reason_area.nth(0).fill("Em đã nộp bổ sung giấy chứng nhận hoạt động hè 5 giờ.")

        page.click('button:has-text("Gửi khiếu nại")')
        page.wait_for_selector(':has-text("Xác nhận gửi khiếu nại điểm rèn luyện")')
        page.locator('button:has-text("Đồng ý gửi")').click()
        page.wait_for_selector(':has-text("Gửi khiếu nại thành công!")')
        print("  -> sv001 gửi khiếu nại thành công (Hồ sơ sang APPEALED).")

        # Quay lại trang Kết quả: kiểm tra nút Đồng ý bị vô hiệu hóa (Mutual Exclusion)
        page.click('a[href="/student/result"]')
        page.wait_for_url(f"{BASE_URL}/student/result")
        accept_btn = page.locator('button:has-text("Đồng ý với điểm dự kiến")')
        assert not accept_btn.is_visible() or accept_btn.is_disabled(), "Mutual Exclusion vi phạm: Khiếu nại rồi vẫn cho bấm Đồng ý!"
        print("  -> Tính loại trừ tương hỗ chuẩn xác: Không thể bấm Đồng ý khi đang khiếu nại.")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 6: SV002 ĐỒNG Ý VỚI ĐIỂM DỰ KIẾN (ACCEPT)
        print("\n[Bước 6] sv002 đồng ý với điểm dự kiến (ACCEPT)...")
        page.fill('input[type="text"]', "sv002")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        page.click('a[href="/student/result"]')
        page.wait_for_url(f"{BASE_URL}/student/result")
        page.wait_for_selector('text="25.00"')

        page.click('button:has-text("Đồng ý với điểm dự kiến")')
        page.wait_for_selector(':has-text("Xác nhận đồng ý điểm rèn luyện dự kiến")')
        page.locator('button:has-text("Đồng ý kết quả")').click()
        page.wait_for_selector(':has-text("Bạn đã xác nhận đồng ý với điểm dự kiến thành công!")')
        print("  -> sv002 đồng ý điểm thành công (Hồ sơ sang ACCEPTED).")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 6b: SV003 ĐỒNG Ý VỚI ĐIỂM DỰ KIẾN (ACCEPT)
        print("\n[Bước 6b] sv003 đồng ý với điểm dự kiến (ACCEPT)...")
        page.fill('input[type="text"]', "sv003")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/student*")

        page.click('a[href="/student/result"]')
        page.wait_for_url(f"{BASE_URL}/student/result")
        page.wait_for_selector('text="24.00"')

        page.click('button:has-text("Đồng ý với điểm dự kiến")')
        page.wait_for_selector(':has-text("Xác nhận đồng ý điểm rèn luyện dự kiến")')
        page.locator('button:has-text("Đồng ý kết quả")').click()
        page.wait_for_selector(':has-text("Bạn đã xác nhận đồng ý với điểm dự kiến thành công!")')
        print("  -> sv003 đồng ý điểm thành công (Hồ sơ sang ACCEPTED).")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 7: BCS GIẢI QUYẾT KHIẾU NẠI & CHỐT BẢNG ĐIỂM (FINALIZE)
        print("\n[Bước 7] BCS giải quyết khiếu nại và Chốt bảng điểm...")
        page.fill('input[type="text"]', "bcs001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/bcs*")

        page.click('a[href="/bcs/appeals"]')
        page.wait_for_url(f"{BASE_URL}/bcs/appeals")
        page.wait_for_selector(':has-text("Danh sách Khiếu nại từ Sinh viên")')

        # Thấy khiếu nại của sv001
        page.wait_for_selector(':has-text("sv001")')
        print("  -> BCS thấy đơn khiếu nại của sv001 trong danh sách OPEN.")

        # Chọn Điều chỉnh điểm (ADJUST), nhập 9.00 và lý do
        page.check('input[type="radio"][value="ADJUST"]')
        page.fill('input[placeholder="vd: 8.00"]', "9.00")
        page.fill('input[placeholder="Bắt buộc nhập lý do kết luận của Ban cán sự..."]', "BCS chấp nhận giấy chứng nhận bổ sung hợp lệ.")

        page.click('button:has-text("Lưu kết luận")')
        page.wait_for_selector(':has-text("Đã giải quyết khiếu nại thành công")')
        print("  -> BCS đã giải quyết khiếu nại thành công -> RESOLVED.")

        # Chốt bảng điểm chính thức (FINALIZE)
        print("  * Chốt bảng điểm chính thức toàn lớp (FINALIZE)...")
        fin_btn = page.locator('button:has-text("Chốt điểm cả lớp")')
        expect(fin_btn).to_be_enabled()
        fin_btn.click()

        page.wait_for_selector(':has-text("Xác nhận chốt điểm rèn luyện toàn bộ lớp")')
        page.locator('button:has-text("Chốt điểm ngay")').click()
        page.wait_for_selector(':has-text("Đã chốt bảng điểm chính thức toàn bộ lớp thành công!")')
        print("  -> Đợt đánh giá đã được Chốt chính thức (FINALIZED).")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        # BƯỚC 8: GVCN ĐĂNG NHẬP, XEM VÀ TẢI BẢNG ĐIỂM CSV CHÍNH THỨC
        print("\n[Bước 8] GVCN đăng nhập, kiểm tra bảng điểm và tải CSV...")
        page.fill('input[type="text"]', "gvcn001")
        page.fill('input[type="password"]', DEMO_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/gvcn/final-scores")
        page.wait_for_selector(':has-text("Bảng điểm Rèn luyện Chính thức (GVCN)")')

        # Kiểm tra bảng điểm hiển thị đầy đủ sv001, sv002 và sv003
        page.wait_for_selector(':has-text("sv001")')
        page.wait_for_selector(':has-text("sv002")')
        page.wait_for_selector(':has-text("sv003")')
        page.wait_for_selector(':has-text("Đã chốt chính thức")')
        print("  -> GVCN thấy bảng điểm chính thức đầy đủ các sinh viên với trạng thái FINALIZED.")

        # Tải tệp CSV
        print("  * Thử nghiệm tải tệp CSV chính thức...")
        with page.expect_download() as download_info:
            page.click('button[data-testid="export-csv-btn"]')
        download = download_info.value
        csv_file_path = os.path.join(ROOT_DIR, "storage", "test_files", "downloaded_final.csv")
        download.save_as(csv_file_path)

        with open(csv_file_path, "r", encoding="utf-8-sig") as f:
            csv_content = f.read()

        print(f"    - Nội dung CSV tải về ({len(csv_content)} bytes):")
        for line in csv_content.strip().split("\n")[:5]:
            print(f"      {line}")

        assert "Mã SV" in csv_content or "sv001" in csv_content, "CSV không chứa mã sinh viên!"
        assert "sv002" in csv_content, "CSV không chứa sv002!"
        assert "sv003" in csv_content, "CSV không chứa sv003!"
        print("  -> GVCN tải và xác nhận tệp CSV thành công 100%!")

        page.click('button:has-text("Đăng xuất")')
        page.wait_for_url(f"{BASE_URL}/login")

        browser.close()

    print("\n=======================================================")
    print(" KẾT QUẢ KIỂM TRA BROWSER CONSOLE VÀ UNCAUGHT ERRORS")
    print("=======================================================")
    if console_errors:
        print(f"  Cảnh báo: Có {len(console_errors)} lỗi console:")
        for err in console_errors:
            print(f"    ! {err}")
    else:
        print("  HOÀN TOÀN KHÔNG CÓ BẤT KỲ LỖI CONSOLE NÀO (0 console errors)!")

    assert len(console_errors) == 0, f"Có lỗi console phát sinh: {console_errors}"
    print("\n>>> TẤT CẢ CÁC TIÊU CHÍ GIAI ĐOẠN 3 TRÊN TRÌNH DUYỆT ĐÃ ĐẠT 100%! <<<\n")


if __name__ == "__main__":
    run_browser_suite()
