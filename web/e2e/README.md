# Playwright E2E BPMN Test Suite — AI Điểm Rèn Luyện (V1)

Thư mục này chứa bộ kịch bản kiểm thử giao diện người dùng tự động (End-to-End UI Testing) đối chiếu với quy trình BPMN 2.0 (`Nhom8_TOBE_NangCao_BPMN20_v6.bpmn`).

---

## 1. Mục đích & Nguyên tắc kiểm thử

1. **Kiểm thử qua giao diện (UI Only):** Mọi hành động nghiệp vụ được kích hoạt trực tiếp từ trình duyệt Chromium/Google Chrome thông qua Playwright.
2. **Không ép trạng thái:** Tuyệt đối không dùng SQL hoặc gọi mutation API để cưỡng ép trạng thái nghiệp vụ.
3. **Bảo mật thông tin xác thực:** Không hardcode mật khẩu trong mã nguồn, console log, JSON hay báo cáo. Mật khẩu được nạp an toàn từ tệp bí mật cục bộ `deploy/.env.pilot_accounts.local` hoặc biến môi trường `PILOT_PASSWORD_<ROLE>`.
4. **Không tạo kết quả giả:**
   - Chỉ đánh giá `PASS` khi có đủ 3 điều kiện:
     - Thao tác thực tế qua UI.
     - Assertion trên DOM/API đạt yêu cầu.
     - Tệp ảnh chụp màn hình chứng minh tồn tại với dung lượng > 0 và phản ánh đúng trạng thái hoàn tất (không chụp skeleton placeholder).
   - Tuyệt đối không dùng giá trị mặc định (fallback default) trong các phép đo định lượng (ví dụ: không gán chiều cao nút bấm bằng 44px nếu không tìm thấy phần tử).
   - Không tự suy diễn môi trường "đã sửa" nếu không có dữ liệu thực tế để đối chiếu (ví dụ: thẻ ưu tiên thiếu dữ liệu case để so khớp link).
   - Happy Path live cần manifest minh chứng `deploy/.env.e2e_evidence.local.json` (đã được `.gitignore` loại trừ), đúng sinh viên pilot `sv003`, ví dụ `{"student_code":"sv003","human_verified":true,"files":{"7b":"D:/duong-dan/minh-chung-7b.png"}}`. Tệp phải do người phụ trách xác nhận phù hợp với tiêu chí. Thiếu manifest thì bước HP-01 ghi `BLOCKED`; không dùng ảnh tổng hợp của bộ đánh giá AI làm minh chứng thật.
5. **Quản lý lỗi từng bước (Step Error Pinpointing):**
   - Theo dõi từng bước Happy Path đang chạy (`HP-01` -> `HP-06`).
   - Ngoại lệ hoặc lỗi assertion xảy ra ở bước nào thì ghi nhận `FAIL` chính xác cho bước đó (không luôn gán `HP-01`).
   - Các bước kế tiếp phía sau được ghi nhận trạng thái `BLOCKED` kèm lý do phụ thuộc bước lỗi.
6. **Đồng bộ hóa báo cáo tự động:** Báo cáo Markdown `docs/e2e_ui_bpmn_test_report.md` được sinh từ `output/e2e_ui_bpmn/run_06/results.json`. Các ca mock được báo riêng, không cộng vào kết quả live.

---

## 2. Cấu trúc thư mục

```text
web/e2e/
├── README.md               # Tài liệu hướng dẫn này
└── run_e2e_bpmn.py         # Kịch bản kiểm thử E2E tự động chính

output/e2e_ui_bpmn/
└── run_06/                 # Thư mục lưu trữ kết quả và bằng chứng của lượt chạy 05
    ├── results.json        # Tệp kết quả máy đọc được (JSON có cấu trúc)
    ├── ENV-01_version_mismatch.png
    ├── SMK-01_student.png
    ├── SMK-01_bcs.png
    ├── SMK-01_route_guard_403.png
    ├── SMK-01_gvcn.png
    ├── SMK-01_admin.png
    ├── SMK-01_login_rbac.png
    ├── EX-01_validation.png
    ├── EX-04_max_score_error.png
    ├── EX-05-A_invalid_file_type.png
    ├── EX-05-B_file_too_large.png
    ├── EX-10_partial_error_state.png
    ├── UX-01_mobile_login.png
    ├── UX-01_mobile_student_form.png
    ├── UX-01_mobile_bcs_dashboard.png
    ├── UX-01_mobile_bcs_cases.png
    ├── UX-01_mobile_responsive.png
    ├── BRANCH_01_missing_evidence.png
    ├── BRANCH_02_local_wrong_link.png
    ├── BRANCH_03_hp04_error.png
    ├── BRANCH_04_gate_closed.png
    ├── BRANCH_05_hp06_no_finalized.png
    └── BRANCH_06_mock_ui_flow.png
```

---

## 3. Cơ chế kiểm tra môi trường & Phiên bản (`ENV-01`)

Script kiểm tra chéo hai môi trường theo các điều kiện nghiêm ngặt:
1. **Kiểm tra Backend:**
   - Đợt đánh giá kích hoạt (`/bcs/campaigns/active`) phải có ít nhất 22 tiêu chí; số tiêu chí sinh viên tự chấm được đối chiếu với dữ liệu thực tế của đợt.
   - Kiểm tra hàng chờ `BCS_REVIEW` để lấy ID case thật.
2. **Kiểm tra Frontend:**
   - Đăng nhập Ban cán sự qua UI, mở Dashboard.
   - So khớp liên kết trên thẻ ưu tiên với ID case thật từ API của chính môi trường đó.
   - Nếu liên kết chứa UUID viết cứng `/bcs/cases/55555555-5555-5555-5555-555555555001` $\rightarrow$ Ghi nhận lỗi lệch phiên bản Frontend.
   - Nếu không có case để đối chiếu $\rightarrow$ Ghi nhận `BLOCKED_ENV_UNVERIFIED` (không suy diễn "đã sửa").
3. **Nguyên tắc không ghép chéo:** Không ghép Frontend của môi trường này với Backend của môi trường khác.
4. **Quyết định thực thi:**
   - Nếu tồn tại một môi trường duy nhất đạt cả 2 điều kiện $\rightarrow$ Tự động thực thi toàn bộ luồng Happy Path (`HP-01`..`HP-06`) qua UI trên môi trường đó.
   - Nếu chưa có môi trường nào thỏa mãn $\rightarrow$ Dừng và ghi nhận các test phụ thuộc là `BLOCKED` kèm lý do trung thực.

---

## 4. Danh mục ca kiểm thử & Nhánh kiểm chứng

### A. Main Suite (Live Environment)
| Test ID | Tên ca kiểm thử | Vai trò | BPMN Task / Gateway | Kết quả kỳ vọng |
|:---|:---|:---|:---|:---|
| **ENV-01** | Kiểm tra môi trường & Phiên bản | ALL | `System_Audit` | Kiểm tra tính đồng bộ giữa 22 tiêu chí và case ID động |
| **SMK-01** | Đăng nhập & Phân quyền RBAC | ALL | `ST_Login`, `Gateway_Security` | Đăng nhập đúng 4 vai trò, Admin nạp xong đợt (0 skeleton), Route Guard chặn 403 |
| **EX-01** | Nộp hồ sơ trống | STUDENT | `SC_CheckCompleteness` | Chặn nộp, hiển thị cảnh báo đỏ, giữ `DRAFT` |
| **EX-04** | Nhập điểm tự chấm vượt trần | STUDENT | `SC_CheckCompleteness` | Chặn ngay trên UI, hiển thị thông báo vượt trần tối đa |
| **EX-05-A** | Tải tệp sai định dạng (.txt) | STUDENT | `SC_CheckEvidenceRules` | Client validation từ chối, yêu cầu PDF/JPG/PNG |
| **EX-05-B** | Tải tệp dung lượng > 10MB | STUDENT | `SC_CheckEvidenceRules` | Client validation từ chối, cảnh báo vượt 10MB |
| **EX-10** | Trạng thái lỗi một phần Dashboard BCS | BCS | `SC_ReviewDraft` | Overview 200, Priority Case 500 $\rightarrow$ hiển thị cảnh báo hổ phách + CTA hàng chờ, 0 NaN |
| **UX-01** | Đánh giá Responsive Mobile (390×844) | ALL | `UX_Audit` | Kiểm toán đủ 4 màn hình bằng phép đo bounding box thật $\ge 44\text{px}$, không tràn ngang |
| **HP-01..06** | Chuỗi Happy Path xử lý hồ sơ | ALL | BPMN Flow | Chỉ PASS khi thực thi trọn vẹn qua UI trên môi trường đồng bộ |
| **EX-02..08** | Các nhánh ngoại lệ BPMN khác | ALL | BPMN Flow | Trạng thái tương ứng theo điều kiện thực thi |

### B. Mock/Fixture Branch Verification Suite
| Mã nhánh | Nhánh nghiệp vụ kiểm chứng | Mục tiêu xác minh |
|:---|:---|:---|
| **BRANCH-MISSING-PROOF** | Thiếu minh chứng bắt buộc | UI phát hiện tiêu chí thiếu tệp minh chứng và cảnh báo/chặn nộp |
| **BRANCH-LOCAL-WRONG-LINK** | Local link sai case ID | Phát hiện sai lệch giữa liên kết thẻ ưu tiên và ID case thật từ API |
| **BRANCH-HP04-ERROR** | Lỗi tại bước HP-04 | Sửa điểm thiếu lý do bị chặn; lỗi được phân định chính xác cho HP-04, block HP-05/06 |
| **BRANCH-GATE-CLOSED** | Gate đóng chặn công bố | Scoreboard chưa đủ điều kiện hiển thị banner cảnh báo, khóa nút công bố, HP-05 = BLOCKED |
| **BRANCH-HP06-NO-FINALIZED** | HP-06 thiếu FINALIZED | GVCN chỉ thấy màn hình giải thích chờ chốt điểm, khóa xuất CSV; HP-06 không thể PASS sớm |
| **BRANCH-MOCK-UI-FLOW** | Mô phỏng luồng UI | Dữ liệu tự chấm đã nạp sẵn; kiểm tra các thao tác nộp, duyệt, công bố, đồng ý, chốt và bàn giao trên UI mock. Không thay thế E2E live. |

---

## 5. Hướng dẫn thực thi

### Điều kiện tiên quyết:
- Python 3.11+
- Đã cài đặt thư viện: `pip install playwright requests`
- Trình duyệt Google Chrome có sẵn trên hệ thống Windows
- Frontend local chạy tại `http://localhost:5173` và Backend local tại `http://localhost:8000`
- Tệp cấu hình bí mật `deploy/.env.pilot_accounts.local` chứa thông tin đăng nhập của các tài khoản pilot.

### Lệnh thực thi:
```powershell
python web/e2e/run_e2e_bpmn.py
```

### Kết quả đầu ra:
1. Thư mục `output/e2e_ui_bpmn/run_06/` chứa ảnh chụp màn hình của live suite và các nhánh mock.
2. Tệp máy đọc `output/e2e_ui_bpmn/run_06/results.json`.
3. Tệp báo cáo Markdown `docs/e2e_ui_bpmn_test_report.md` được tự động cập nhật khớp từng số liệu.
