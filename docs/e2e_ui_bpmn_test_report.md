# BÁO CÁO KIỂM THỬ HỆ THỐNG ĐIỂM RÈN LUYỆN QUA GIAO DIỆN (E2E & BPMN AUDIT) — LƯỢT CHẠY 07 (TỰ ĐỘNG XUẤT TỪ RESULTS.JSON)

**Thời gian thực hiện:** 28/10/2026 00:14:47  
**Vai trò kiểm thử:** Senior QA Automation Engineer  
**Tệp quy trình đối chiếu:** `Nhom8_TOBE_NangCao_BPMN20_v6.bpmn`  
**Kịch bản kiểm thử tự động:** `web/e2e/run_e2e_bpmn.py`  
**Tệp kết quả máy đọc (Machine-readable):** `output/e2e_ui_bpmn/run_07/results.json`  
**Thư mục lưu trữ bằng chứng kiểm thử:** `output/e2e_ui_bpmn/run_07/`  

---

## 1. Môi trường & Phiên bản kiểm thử

Kiểm thử được tiến hành độc lập và xác minh chéo trên cả hai môi trường hiện có để đánh giá tính toàn vẹn và mức độ sẵn sàng triển khai:

1. **Môi trường Production (Vercel):**
   - **Frontend URL:** `https://ai-diemrenluyen-web.vercel.app`
   - **Backend URL:** `https://ai-diemrenluyen-api.vercel.app`
   - **Hiện trạng quan sát thực tế:**
     - Backend API trả về **23 tiêu chí** cho đợt đang hoạt động.
     - Backend hiện có hồ sơ đang ở trạng thái `BCS_REVIEW`: ID case thật là `cf874699-de38-45b4-9a80-778c76a4093b`.
     - **Frontend đồng bộ:** Bundle frontend trên Vercel đã triển khai bản mới. Thẻ ưu tiên trên Dashboard Ban cán sự (`BcsDashboard`) **liên kết động chính xác tới `/bcs/cases/cf874699-de38-45b4-9a80-778c76a4093b`**, khớp 100% với case ID thật `cf874699-de38-45b4-9a80-778c76a4093b` từ Backend API.

2. **Môi trường Local (Phát triển cục bộ):**
   - **Frontend URL:** `http://localhost:5173` (Vite dev server)
   - **Backend URL:** `http://localhost:8000` (FastAPI local)
   - **Hiện trạng quan sát thực tế:**
     - Backend local có **3 tiêu chí**, 0 hồ sơ `BCS_REVIEW`; case API đầu tiên: `None`.
     - Link ưu tiên quan sát trên frontend local: `None`.

> [!NOTE]
> **KẾT LUẬN KIỂM TOÁN MÔI TRƯỜNG (`ENV-01`):**
> Môi trường được xác minh thành công: **VERCEL**. Backend và Frontend đồng bộ với >= 22 tiêu chí và case ID động. Trạng thái từng bước Happy Path nằm trong bảng Main Suite bên dưới.

3. **Tài khoản kiểm thử:**
   - `sv001`, `sv002`, `sv003` (Sinh viên)
   - `bcs001` (Ban cán sự lớp - Lớp trưởng)
   - `gvcn001` (Giáo viên chủ nhiệm)
   - `admin001` (Quản trị hệ thống)
   *(Mật khẩu được nạp an toàn từ biến môi trường và tệp bí mật cục bộ `deploy/.env.pilot_accounts.local`, tuyệt đối không in ra báo cáo, console hay git).*

4. **Cấu hình Minh chứng Pilot (`HP-01`):**
   - Tệp mẫu cấu hình không chứa dữ liệu cá nhân: `deploy/evidence_manifest.example.json`.
   - Tệp cục bộ thực thi: `deploy/.env.e2e_evidence.local.json` (được `.gitignore` bảo vệ, không đưa lên Git).
   - Khi chưa cung cấp tệp này với minh chứng thật được duyệt, `HP-01` ghi nhận `BLOCKED` đúng nguyên tắc bảo toàn dữ liệu.

---

## 2. Bảng đối chiếu quy trình BPMN (Traceability Matrix - Main Suite)

| Test ID | BPMN Task / Gateway | Vai trò | Thao tác UI thực tế | Trạng thái hồ sơ mong đợi | Kết quả | Bằng chứng |
|:---|:---|:---|:---|:---|:---|:---|
| **ENV-01** | `System_Audit` | ALL | Kiểm tra phiên bản & số tiêu chí trên Vercel vs Local | Tồn tại môi trường chứa cả 22 tiêu chí và Dashboard BCS động | **PASS** | `output/e2e_ui_bpmn/run_07/ENV-01_env_verified.png` |
| **SMK-01** | `ST_Login` | ALL | Đăng nhập qua UI 4 vai trò & kiểm tra Route Guard | Đăng nhập thành công đúng vai trò, route trái quyền bị chặn 403, Admin hiển thị dữ liệu thật (0 skeleton) | **PASS** | `output/e2e_ui_bpmn/run_07/SMK-01_login_rbac.png` |
| **EX-01** | `SC_CheckCompleteness` | STUDENT | Không chọn điểm, bấm Nộp hồ sơ | UI chặn gửi, hiển thị thông báo lỗi, hồ sơ giữ DRAFT | **PASS** | `output/e2e_ui_bpmn/run_07/EX-01_validation.png` |
| **EX-04** | `SC_CheckCompleteness` | STUDENT | Nhập điểm tự chấm 99 (vượt quá trần 10.00) | UI lập tức báo lỗi đỏ, chặn điểm vượt trần | **PASS** | `output/e2e_ui_bpmn/run_07/EX-04_max_score_error.png` |
| **EX-05-A** | `SC_CheckEvidenceRules` | STUDENT | Tải tệp .txt vào mục minh chứng | Client validation từ chối, hiển thị thông báo định dạng | **PASS** | `output/e2e_ui_bpmn/run_07/EX-05-A_invalid_file_type.png` |
| **EX-05-B** | `SC_CheckEvidenceRules` | STUDENT | Tải tệp 11MB (>10MB) vào mục minh chứng | Client validation từ chối, hiển thị giới hạn 10MB | **PASS** | `output/e2e_ui_bpmn/run_07/EX-05-B_file_too_large.png` |
| **EX-10** | `SC_ReviewDraft` | BCS | Network Interception: Overview 200 (đầy đủ schema), Priority Case 500 | Dashboard không trắng, hiển thị cảnh báo lỗi một phần + CTA hàng chờ, không có NaN | **PASS** | `output/e2e_ui_bpmn/run_07/EX-10_partial_error_state.png` |
| **UX-01** | `UX_Audit` | ALL | Kiểm toán 4 màn hình mobile (390×844) với phép đo bounding_box thật | scrollWidth <= 390px trên mọi màn hình, tap targets >= 44px, không tràn ngang | **PASS** | `output/e2e_ui_bpmn/run_07/UX-01_mobile_responsive.png` |
| **HP-01** | `ST_Self & ST_Submit` | STUDENT | Thực thi Happy Path tại bước HP-01 | Hoàn tất nghiệp vụ bước | **BLOCKED** | `output/e2e_ui_bpmn/run_07/HP-01_blocked.png` |
| **HP-02** | `SC_ReviewDraft` | BCS | Thực thi Happy Path tại bước HP-02 | Hoàn tất nghiệp vụ bước | **BLOCKED** | Dừng do lỗi phát sinh tại bước phía trước (HP-01) |
| **HP-03** | `SC_BCSFlags` | BCS | Thực thi Happy Path tại bước HP-03 | Hoàn tất nghiệp vụ bước | **BLOCKED** | Dừng do lỗi phát sinh tại bước phía trước (HP-01) |
| **HP-04** | `SC_MergeReview` | BCS | Thực thi Happy Path tại bước HP-04 | Hoàn tất nghiệp vụ bước | **BLOCKED** | Dừng do lỗi phát sinh tại bước phía trước (HP-01) |
| **HP-05** | `SC_PublishDraft` | BCS | Thực thi Happy Path tại bước HP-05 | Hoàn tất nghiệp vụ bước | **BLOCKED** | Dừng do lỗi phát sinh tại bước phía trước (HP-01) |
| **HP-06** | `SC_Finalize & SC_SendFinal` | BCS/GVCN | Thực thi Happy Path tại bước HP-06 | Hoàn tất nghiệp vụ bước | **BLOCKED** | Dừng do lỗi phát sinh tại bước phía trước (HP-01) |
| **EX-02** | `SC_MissingNotice` | STUDENT | Nộp hồ sơ thiếu thông tin bắt buộc | Chuyển NEEDS_INFO có hạn bổ sung | **NOT RUN** | Chưa thể thực hiện do HP-01 bị chặn (thiếu manifest minh chứng pilot). |
| **EX-03** | `SC_RequestProof` | BCS/SV | Quy trình yêu cầu và bổ sung minh chứng | Chuyển NEEDS_PROOF -> nộp lại -> BCS_REVIEW | **NOT RUN** | Chưa thể thực hiện do HP-01 bị chặn (thiếu manifest minh chứng pilot). |
| **EX-06** | `Gateway_Concurrency` | STUDENT/BCS | Kiểm tra chống gửi kép (Double-click) | Chặn request thứ 2, chỉ tăng 1 version | **NOT RUN** | Chưa thể thực hiện do HP-01 bị chặn (thiếu manifest minh chứng pilot). |
| **EX-07** | `SC_Edit` | BCS | BCS sửa điểm nhưng để trống lý do | UI/API chặn và báo lỗi yêu cầu lý do | **NOT RUN** | Chưa thể thực hiện do HP-01 bị chặn (thiếu manifest minh chứng pilot). |
| **EX-08** | `SC_HandleAppeal` | STUDENT/BCS | Quy trình khiếu nại điểm | Chuyển APPEALED, BCS xử lý | **BLOCKED** | Chưa có hồ sơ nào ở trạng thái PUBLISHED để thực hiện khiếu nại (HP-05 chưa hoàn tất). |

---

## 3. Tổng kết số liệu kiểm thử (Mathematical Verification)

- **Tổng số ca kiểm thử thực tế trong bảng:** 19
- **Số ca ĐẠT (PASS):** 8 (42.1%)
- **Số ca KHÔNG ĐẠT (FAIL):** 0 (0.0%)
- **Số ca BỊ CHẶN (BLOCKED):** 7 (36.8%)
- **Số ca CHƯA CHẠY (NOT RUN):** 4 (21.1%)

> [!NOTE]
> **Xác nhận tính nhất quán toán học (Được kiểm tra tự động):**  
> $\text{PASS (8)} + \text{FAIL (0)} + \text{BLOCKED (7)} + \text{NOT RUN (4)} = 19 \equiv \text{Tổng số ca kiểm thử trong bảng (19)}$.

---

## 4. Bằng chứng kiểm thử chi tiết & Phép đo định lượng

### A. Kiểm toán Responsive trên Mobile 390×844 (`UX-01`):
Phép đo định lượng được thực thi tự động qua Playwright Script bằng thuộc tính DOM thật sau khi dữ liệu đã tải xong hoàn toàn, **loại bỏ hoàn toàn giá trị giả định mặc định (fallback default)**:
1. **Màn hình Đăng nhập (`UX-01_mobile_login.png`):**
   - `scrollWidth = 390px`, `innerWidth = 390px` $\rightarrow$ `overflow = False`.
   - Bounding box nút Đăng nhập: `height = 44px` (yêu cầu $\ge 44\text{px}$).
2. **Biểu mẫu Sinh viên (`UX-01_mobile_student_form.png`):**
   - Đợi nạp xong toàn bộ các thẻ tiêu chí.
   - `scrollWidth = 390px`, `innerWidth = 390px` $\rightarrow$ `overflow = False`.
   - Bounding box nút Nộp hồ sơ: `height = 44px` (yêu cầu $\ge 44\text{px}$).
3. **Bảng điều khiển BCS (`UX-01_mobile_bcs_dashboard.png`):**
   - Đợi dữ liệu đợt nạp xong, thoát khỏi skeleton loading.
   - `scrollWidth = 390px`, `innerWidth = 390px` $\rightarrow$ `overflow = False`.
   - Thẻ thống kê tự co giãn 1 cột trên mobile, thanh điều hướng sidebar chuyển thành tab ngang.
4. **Hàng chờ hồ sơ BCS (`UX-01_mobile_bcs_cases.png`):**
   - Đã chuyển đổi từ bảng table 8 cột sang giao diện thẻ danh sách theo dòng (`.bcs-cases-cards-mobile`).
   - `scrollWidth = 390px`, `innerWidth = 390px` $\rightarrow$ `overflow = False`.
   - Bounding box nút thao tác "Xem chi tiết": `height = 44px` (yêu cầu $\ge 44\text{px}$). Nếu không tìm thấy phần tử, giá trị gán là `0.0px` và lập tức đánh trượt kiểm thử.

### B. Kiểm soát trạng thái lỗi một phần Dashboard BCS (`EX-10`):
- **Phòng chống lỗi NaN:** Mock overview cung cấp đủ các bộ đếm; Playwright kiểm tra giao diện không hiển thị `NaN` hoặc `undefined`.
- **Xác minh qua Script:** Playwright thực hiện kiểm tra `assert not re.search(r'\bNaN\b', body_text)` và xác nhận **100% không có chữ NaN hoặc undefined** trên giao diện.
- **Bằng chứng:** `output/e2e_ui_bpmn/run_07/EX-10_partial_error_state.png` hiển thị rõ hộp cảnh báo hổ phách và nút CTA "Mở hàng chờ →".

### C. Đăng nhập và Phân quyền RBAC (`SMK-01`):
Đã chụp riêng biệt từng vai trò sau khi trang nạp dữ liệu xong (đảm bảo skeleton loader biến mất 100% trước khi chụp):
- `SMK-01_student.png`: Giao diện Sinh viên `sv001`.
- `SMK-01_bcs.png`: Giao diện Ban cán sự `bcs001`.
- `SMK-01_gvcn.png`: Giao diện Giáo viên `gvcn001`.
- `SMK-01_admin.png`: Giao diện Quản trị viên `admin001` (**đã đợi `.ui-loading-panel, .ui-skeleton` biến mất hoàn toàn**, hiển thị toàn bộ form và bảng đợt đánh giá).
- `SMK-01_route_guard_403.png`: Màn hình chặn truy cập 403 Forbidden khi BCS cố tình vào trang Admin.

---

## 5. Kết quả kiểm chứng Mock/Fixture cho các nhánh nghiệp vụ BPMN

Bộ Mock/Fixture kiểm tra phản ứng UI với dữ liệu giả lập. PASS ở đây không thay thế kết quả Happy Path trên backend thật và không được cộng vào Main Suite:

| Mã nhánh | Nhánh nghiệp vụ kiểm chứng | Kết quả | Trạng thái ghi nhận | Bằng chứng hình ảnh |
|:---|:---|:---|:---|:---|
| **BRANCH-MISSING-PROOF** | Thiếu minh chứng bắt buộc khi tự chấm | **PASS** | UI phát hiện thiếu minh chứng tiêu chí 7b, cảnh báo rõ ràng trước khi nộp | `output/e2e_ui_bpmn/run_07/BRANCH_01_missing_evidence.png` |
| **BRANCH-LOCAL-WRONG-LINK** | Đối chiếu case ID trên Dashboard với API | **PASS** | Link UI khớp case API 11111111-1111-4111-8111-111111111111; phép kiểm ENV-01 từ chối một link khác | `output/e2e_ui_bpmn/run_07/BRANCH_02_local_wrong_link.png` |
| **BRANCH-HP04-ERROR** | UI chặn BCS hoàn tất khi thiếu lý do điều chỉnh | **PASS** | UI chặn hoàn tất kiểm tra khi điều chỉnh điểm thiếu lý do | `output/e2e_ui_bpmn/run_07/BRANCH_03_hp04_error.png` |
| **BRANCH-GATE-CLOSED** | Gate đóng chặn công bố bảng điểm | **PASS** | Banner hổ phách liệt kê rõ các điều kiện chưa đạt, nút công bố bị khóa cứng | `output/e2e_ui_bpmn/run_07/BRANCH_04_gate_closed.png` |
| **BRANCH-HP06-NO-FINALIZED** | HP-06 từ chối PASS khi đợt chưa chốt sổ FINALIZED | **PASS** | GVCN chỉ thấy màn hình giải thích chờ chốt điểm, bảng điểm rỗng, nút xuất CSV bị khóa | `output/e2e_ui_bpmn/run_07/BRANCH_05_hp06_no_finalized.png` |
| **BRANCH-MOCK-UI-FLOW** | Luồng UI mô phỏng từ nộp hồ sơ đến GVCN nhận bàn giao | **PASS** | Dữ liệu tự chấm đã có sẵn; UI nộp -> BCS duyệt -> công bố -> sinh viên đồng ý -> BCS chốt và gửi -> GVCN nhận | `output/e2e_ui_bpmn/run_07/BRANCH_06_mock_ui_flow.png` |
| **BRANCH-QUEUE-MULTI-STUDENT** | Hàng chờ nhiều SV: Thẻ ưu tiên là sv001, mở đúng sv003 qua UI hàng chờ | **PASS** | Dashboard hiển thị ưu tiên sv001; script vào hàng chờ /bcs/cases, tìm sv003 và click mở đúng /bcs/cases/33333333-3333-4333-8333-333333333333 | `output/e2e_ui_bpmn/run_07/BRANCH_07_queue_multi_student.png` |

### Chi tiết các nhánh kiểm chứng:
1. **BRANCH-MISSING-PROOF — Thiếu minh chứng bắt buộc khi tự chấm:**
   - **Hành vi quan sát:** UI phát hiện thiếu minh chứng tiêu chí 7b, cảnh báo rõ ràng trước khi nộp
   - **Kết luận QA:** Xác minh thành công: Client ngăn ngừa hoặc cảnh báo khi sinh viên chấm điểm nhưng thiếu minh chứng.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_01_missing_evidence.png`

2. **BRANCH-LOCAL-WRONG-LINK — Đối chiếu case ID trên Dashboard với API:**
   - **Hành vi quan sát:** Link UI khớp case API 11111111-1111-4111-8111-111111111111; phép kiểm ENV-01 từ chối một link khác
   - **Kết luận QA:** Xác minh thành công: Script đối chiếu href (/bcs/cases/11111111-1111-4111-8111-111111111111) với case ID thật của API.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_02_local_wrong_link.png`

3. **BRANCH-HP04-ERROR — UI chặn BCS hoàn tất khi thiếu lý do điều chỉnh:**
   - **Hành vi quan sát:** UI chặn hoàn tất kiểm tra khi điều chỉnh điểm thiếu lý do
   - **Kết luận QA:** Fixture kiểm tra validation UI; phân loại FAIL/BLOCKED của bộ điều phối chỉ được xác minh khi chạy luồng E2E thực.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_03_hp04_error.png`

4. **BRANCH-GATE-CLOSED — Gate đóng chặn công bố bảng điểm:**
   - **Hành vi quan sát:** Banner hổ phách liệt kê rõ các điều kiện chưa đạt, nút công bố bị khóa cứng
   - **Kết luận QA:** Fixture kiểm tra Gate UI; main suite ghi HP-05 BLOCKED khi gặp Gate đóng.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_04_gate_closed.png`

5. **BRANCH-HP06-NO-FINALIZED — HP-06 từ chối PASS khi đợt chưa chốt sổ FINALIZED:**
   - **Hành vi quan sát:** GVCN chỉ thấy màn hình giải thích chờ chốt điểm, bảng điểm rỗng, nút xuất CSV bị khóa
   - **Kết luận QA:** Fixture kiểm tra GVCN bị chặn trước FINALIZED; main suite còn phải thực hiện chốt và bàn giao.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_05_hp06_no_finalized.png`

6. **BRANCH-MOCK-UI-FLOW — Luồng UI mô phỏng từ nộp hồ sơ đến GVCN nhận bàn giao:**
   - **Hành vi quan sát:** Dữ liệu tự chấm đã có sẵn; UI nộp -> BCS duyệt -> công bố -> sinh viên đồng ý -> BCS chốt và gửi -> GVCN nhận
   - **Kết luận QA:** Fixture mô phỏng nghiệp vụ qua UI; không thay thế kết quả Happy Path trên backend thật.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_06_mock_ui_flow.png`

7. **BRANCH-QUEUE-MULTI-STUDENT — Hàng chờ nhiều SV: Thẻ ưu tiên là sv001, mở đúng sv003 qua UI hàng chờ:**
   - **Hành vi quan sát:** Dashboard hiển thị ưu tiên sv001; script vào hàng chờ /bcs/cases, tìm sv003 và click mở đúng /bcs/cases/33333333-3333-4333-8333-333333333333
   - **Kết luận QA:** Xác minh thành công: Script không điều hướng thẳng URL mà tìm và click qua UI hàng chờ.
   - **Ảnh minh chứng:** `output/e2e_ui_bpmn/run_07/BRANCH_07_queue_multi_student.png`

---

## 6. Giới hạn của lần kiểm thử & Khuyến nghị Pilot

1. **Minh chứng pilot (`HP-01`):** Nếu chưa có manifest minh chứng thật tại `deploy/.env.e2e_evidence.local.json`, `HP-01` và các bước kế tiếp ghi nhận `BLOCKED` đúng nguyên tắc bảo toàn dữ liệu. Người phụ trách cần sao chép từ `deploy/evidence_manifest.example.json` và bổ sung tệp minh chứng thực tế.
2. **Điều kiện Gate công bố (`HP-05`):** Nếu lớp còn hồ sơ chưa ở trạng thái `PROPOSED` hoặc chưa đủ 2 cuộc họp và biên bản rà soát, Gate Check hiển thị cảnh báo và khóa nút công bố (`HP-05 = BLOCKED`). Không được tự ý duyệt thay hồ sơ của sinh viên khác để ép thông luồng.
3. **Điều hướng hồ sơ (`HP-02` / `HP-03`):** Thẻ ưu tiên Dashboard hiển thị hồ sơ đầu tiên của hàng chờ API. Để xử lý sinh viên chỉ định (`sv003`), Ban cán sự truy cập qua giao diện hàng chờ `/bcs/cases` để tìm và mở hồ sơ tương ứng.
4. **Nghiệm thu toàn bộ luồng:** Chỉ xác nhận quy trình PASS khi toàn bộ các bước được kiểm chứng thực tế trên cùng môi trường Production.
