# Biên bản Bàn giao Giai đoạn 3 — Rà soát Giao diện & Bàn giao Vỏ V1

- **Dự án:** Hệ thống Chấm Điểm Rèn Luyện Sinh Viên (AI_DRL_Project)
- **Giai đoạn:** Giai đoạn 3 — Rà soát giao diện và bàn giao vỏ V1 (sau Giai đoạn 2.5)
- **Thời điểm thực hiện:** 25/10/2026
- **Trạng thái:** **HOÀN THÀNH 100% — ĐẠT TẤT CẢ TIÊU CHÍ BÀN GIAO**

---

## 1. Mục tiêu và Phạm vi Giai đoạn 3

Theo tài liệu đặc tả `DAC_TA_CODE_WEB_VO_V1.md` và hướng dẫn `output/PROMPT_GIAI_DOAN_3_BAN_GIAO_VO_V1.md`:
- Hoàn thiện bản web **Live** hiện có, chạy trên nền cơ sở dữ liệu PostgreSQL thật và backend FastAPI thật.
- Rà soát toàn bộ giao diện qua **trình duyệt Google Chrome thật (Playwright)** trên nhiều kích thước màn hình (Mobile 390px, Tablet 768px, Desktop 1366px).
- Thực thi chu trình liên vai trò đầu-cuối hoàn chỉnh: `ADMIN` → `STUDENT` → `BCS` → `STUDENT` → `GVCN`.
- Kiểm tra cách ly dữ liệu giữa nhiều sinh viên (`sv001`, `sv002`, `sv003`), xác thực người dùng và phân quyền (RBAC Route Guard).
- **Ràng buộc tuyệt đối:** Không tích hợp AI/OCR/LLM/RAG; không âm thầm fallback sang mock data khi chạy ở chế độ Live.

---

## 2. Môi trường Thực thi & Kiểm thử Live

| Thành phần | Phiên bản / Cấu hình | Ghi chú |
|---|---|---|
| **Hệ điều hành** | Windows 11 Pro 64-bit | Shell: PowerShell |
| **Cơ sở dữ liệu** | PostgreSQL 16 (Container `drl_postgres`) | Port: 5432, kết nối SQLAlchemy async/sync pool |
| **Backend** | Python 3.11.9, FastAPI 0.115.6, Uvicorn | Port: 8000, HttpOnly Cookie Session + CSRF |
| **Frontend** | Node.js v22.14.0, React 18, Vite 5.4, TypeScript | Port: 5173, `VITE_DEMO_MODE=false` (Live Mode thực) |
| **Trình duyệt tự động** | Playwright 1.64.1 (Google Chrome v156 Headless) | Đo viewport, thao tác click, upload, download CSV |

---

## 3. Kết quả Kiểm thử Chu trình Đầu-Cuối trên Trình duyệt Thật (`api/scripts/browser_phase3_run.py`)

Kịch bản kiểm thử tự động điều khiển trình duyệt thực hiện đầy đủ các bước nghiệp vụ và xác minh dữ liệu trực tiếp trong database:

### Phần 1: Rà soát Lỗi Người dùng & Phân quyền UI
1. **Kiểm tra Đăng nhập Sai Mật khẩu (401 Unauthorized):**
   - Người dùng nhập mật khẩu sai `MatKhauSai@999` cho tài khoản `sv001`.
   - Giao diện bắt lỗi từ backend và hiển thị cảnh báo đỏ: `"Tên đăng nhập hoặc mật khẩu không chính xác."`.
   - Trình duyệt giữ nguyên ở `/login`, không tạo session cookie trái phép.
2. **Kiểm tra Phân quyền Tuyến đường (Route Guard & 403 Forbidden):**
   - `sv001` đăng nhập thành công vào `/student`.
   - Cố tình gõ trực tiếp URL của Ban cán sự (`/bcs` hoặc `/bcs/dashboard`) → Bị chặn bởi `ProtectedRoute`, hiển thị thẻ đỏ `403 — Không có quyền truy cập`.
   - Cố tình gõ trực tiếp URL của Quản trị viên (`/admin/campaigns`) → Bị chặn 403 Forbidden.
   - Đăng xuất thành công, xóa phiên và điều hướng an toàn về `/login`.
3. **Rà soát Giao diện Responsive trên nhiều độ phân giải:**
   - **Mobile 390px (iPhone 12/13/14):** Form sinh viên tự co giãn, không tràn ngang (`scrollWidth <= innerWidth`).
   - **Tablet 768px (iPad Mini):** Menu điều hướng và các thẻ tiêu chí căn chỉnh gọn gàng, không vỡ layout.
   - **Desktop 1366px (BCS Laptop):** Màn hình hàng chờ hồ sơ và bảng điểm hiển thị đầy đủ bảng dữ liệu, nút bấm dễ thao tác.

### Phần 2: Chu trình Nghiệp vụ Đầu-Cuối (Database Thực)
1. **Bước 1 (ADMIN):**
   - `admin001` đăng nhập, kiểm tra đợt đánh giá ở trạng thái `DRAFT`.
   - Mở đợt đánh giá trực tiếp qua UI (`POST /admin/campaigns/{id}/open`).
   - Hệ thống tự động sinh hồ sơ `Case` ở trạng thái `DRAFT` cho tất cả sinh viên trong lớp (`sv001`, `sv002`, `sv003`).
2. **Bước 2 (STUDENT `sv001` - Tự chấm, Validation & Minh chứng):**
   - `sv001` đăng nhập, thấy đúng họ tên "Nguyễn Văn An" và đợt đánh giá đang mở.
   - Thử nghiệm tải tệp sai định dạng `.txt` → Bị từ chối ngay lập tức: `"Chỉ hỗ trợ tệp định dạng PDF, JPG hoặc PNG."`.
   - Tải tệp PDF thật cho TC01 và tệp PNG thật cho TC03.
   - Tự chấm điểm (TC01: 9.00, TC02: 8.00, TC03: 7.00), bấm "Lưu nháp" thành công.
   - Bấm "Nộp hồ sơ", xác nhận trong hộp thoại modal → Hồ sơ chuyển trạng thái `BCS_REVIEW`.
3. **Bước 3 (STUDENT `sv002` - Cách ly Dữ liệu Tuyệt đối):**
   - `sv002` đăng nhập, thấy đúng tên "Trần Thị Bình".
   - **Kiểm chứng cách ly:** Giao diện tuyệt đối không hiển thị bất kỳ thông tin hoặc điểm số nào của `sv001`.
   - Tải minh chứng, tự chấm điểm và nộp hồ sơ thành công vào `BCS_REVIEW`.
4. **Bước 3b (STUDENT `sv003` - Hoàn tất Sĩ số Cả Lớp):**
   - `sv003` đăng nhập, tự chấm điểm và nộp hồ sơ thành công vào `BCS_REVIEW`.
5. **Bước 4 (BCS `bcs001` - Duyệt 3 Vùng, Cuộc Họp & Công bố Điểm):**
   - `bcs001` thấy toàn bộ 3 hồ sơ (`sv001`, `sv002`, `sv003`) trong hàng chờ `/bcs/cases`.
   - **Duyệt `sv001`:** Mở modal `SafeFilePreviewModal` kiểm tra tệp an toàn; giảm điểm TC01 từ 9.00 xuống 8.00 kèm lý do `"Chưa đủ số giờ tình nguyện theo quy định"`; lưu điểm TC02, TC03; hoàn tất kiểm tra hồ sơ `sv001` sang `PROPOSED`.
   - **Duyệt `sv002` & `sv003`:** Kiểm tra và hoàn tất duyệt sang `PROPOSED`.
   - **Kiểm tra Cổng Công bố Điểm (Scoreboard Gate):** Khi chưa ghi nhận đủ 2 cuộc họp, nút "Công bố điểm dự kiến" bị vô hiệu hóa (disabled) đúng quy định.
   - **Ghi nhận 2 Cuộc họp:** Ghi nhận biên bản "Họp Ban cán sự lớp" và biên bản "Họp toàn thể Lớp" qua modal.
   - **Công bố Điểm:** Sau khi đủ điều kiện, nút mở khóa; bấm xác nhận công bố điểm → Đợt chuyển sang `PUBLISHED`.
6. **Bước 5 (STUDENT `sv001` - Khiếu nại & Kiểm tra Loại trừ Tương hỗ):**
   - `sv001` đăng nhập vào `/student/result`, thấy đúng tổng điểm dự kiến 23.00 và lý do bị trừ điểm của BCS.
   - Bấm "Khiếu nại điểm", nhập nội dung khiếu nại cho TC01 và gửi thành công → Hồ sơ sang `APPEALED`.
   - **Kiểm tra Mutual Exclusion:** Nút "Đồng ý với điểm dự kiến" bị khóa/ẩn, đảm bảo không thể đồng ý khi đang khiếu nại.
7. **Bước 6 & 6b (STUDENT `sv002` & `sv003` - Đồng ý Kết quả):**
   - `sv002` và `sv003` xem điểm dự kiến và bấm "Đồng ý với điểm dự kiến" → Hồ sơ chuyển sang `ACCEPTED`.
8. **Bước 7 (BCS `bcs001` - Giải quyết Khiếu nại & Chốt Điểm Cả Lớp):**
   - Vào `/bcs/appeals`, thấy đơn khiếu nại của `sv001`.
   - Chọn "Điều chỉnh điểm" (ADJUST), cập nhật điểm mới 9.00 và ghi lý do kết luận của BCS → Chuyển sang `RESOLVED`.
   - Cả 3 hồ sơ trong lớp đều đã sẵn sàng (`RESOLVED`, `ACCEPTED`, `ACCEPTED`).
   - Bấm "Chốt điểm cả lớp", xác nhận modal → Đợt đánh giá chuyển sang `FINALIZED`.
9. **Bước 8 (GVCN `gvcn001` - Xem & Xuất Bảng Điểm CSV Chính Thức):**
   - `gvcn001` đăng nhập, thấy bảng điểm chính thức của toàn bộ 3 sinh viên (`sv001`, `sv002`, `sv003`) ở trạng thái `FINALIZED`.
   - Bấm "Xuất bảng điểm CSV", tải tệp `Bang_Diem_DRL_Chinh_Thuc_HK1-2026-2027.csv`.
   - Đọc và xác minh nội dung CSV (279 bytes, UTF-8 BOM, đúng header và 3 sinh viên).
10. **Giám sát Console Browser:**
    - Ghi nhận **0 lỗi console (`0 console errors`)**, không có bất kỳ unhandled exception nào làm sập giao diện.

---

## 4. Các Vấn đề Đã Phát hiện & Khắc phục trong Giai đoạn 3

Trong quá trình rà soát giao diện và thực thi luồng thật, các điểm sau đã được xử lý triệt để:

1. **Khởi tạo Dữ liệu Mock trong Component khi chạy Live Mode:**
   - *Phát hiện:* Trong `BcsScores.tsx` và `BcsAppeals.tsx`, state khởi tạo ban đầu gọi `staffStore.getScoreboard()` hoặc `staffStore.getCampaign()`, gây chớp dữ liệu giả trước khi API thực phản hồi.
   - *Khắc phục:* Khởi tạo state rỗng/null khi `!isDemoMode`, bổ sung giao diện loading và null-safety an toàn.
2. **Lỗi Đồng bộ State trong Modal Ghi nhận Cuộc họp (`MeetingRecordModal.tsx`):**
   - *Phát hiện:* Do component được tái sử dụng khi mở cuộc họp thứ 2 (Họp Lớp), hook `useState` không cập nhật lại giá trị `kind` từ prop `initialKind`, dẫn đến gửi trùng biên bản Họp BCS.
   - *Khắc phục:* Bổ sung hook `useEffect` theo dõi `[isOpen, initialKind, existingMeeting]` để đồng bộ lại toàn bộ form mỗi khi modal mở ra.
3. **Định danh Phần tử Tương tác (Data Test IDs):**
   - *Phát hiện:* Các nút ghi nhận cuộc họp và xuất CSV có văn bản thay đổi tùy theo trạng thái (chỉnh sửa / ghi nhận), dễ gây nhầm lẫn selector.
   - *Khắc phục:* Bổ sung các thuộc tính tường minh `data-testid="record-bcs-meeting"`, `data-testid="record-class-meeting"`, `data-testid="publish-scores-btn"`, `data-testid="export-csv-btn"`.
4. **Quy tắc Cổng Xuất bản Điểm (Scoreboard Gate Section 9.8):**
   - *Phát hiện:* Cổng xuất bản điểm yêu cầu 100% hồ sơ trong lớp phải ở trạng thái sẵn sàng (`PROPOSED` hoặc `CLOSED_*`). Nếu còn sinh viên ở `DRAFT`, nút công bố sẽ bị khóa đúng quy chế.
   - *Khắc phục:* Kịch bản kiểm thử đã đưa cả 3 sinh viên trong lớp tham gia luồng hoàn chỉnh, kiểm chứng cả hai trạng thái: bị khóa khi chưa đủ điều kiện và tự động mở khóa khi đủ điều kiện.

---

## 5. Tổng kết Kiểm thử Hệ thống Toàn diện

Mọi bộ kiểm thử của dự án đều đạt 100% sau khi hoàn thiện Giai đoạn 3:

```text
======================================================================
1. Backend & Contract Tests (python tests/run_tests.py --mode all)
======================================================================
  - tests/contract/test_fixtures_contract.py: 6 passed
  - tests/contract/test_openapi_contract.py: 5 passed
  - tests/contract/test_states_contract.py: 35 passed
  - tests/e2e/test_01 -> test_16 (Section 9 Acceptance Tests): 17 passed
  TỔNG CỘNG: 63 passed / 63 tests (100% ĐẠT)

======================================================================
2. Frontend Unit & Integration Tests (npm test --prefix web)
======================================================================
  - Logic Sinh viên (Gói B): 25 passed
  - Nghiệp vụ Cán bộ BCS / GVCN / Admin (Gói C): 20 passed
  - Tích hợp Live Client & Route Guard (Giai đoạn 2.5): 9 passed
  TỔNG CỘNG: 54 passed / 54 tests (100% ĐẠT)

======================================================================
3. Frontend TypeScript & Production Build (npm run build --prefix web)
======================================================================
  - TypeScript compiler (tsc): 0 errors
  - Vite build production bundle: Thành công trong 4.17s (dist/assets/...)

======================================================================
4. Kịch bản Trình duyệt Thật Playwright (api/scripts/browser_phase3_run.py)
======================================================================
  - 8/8 bước nghiệp vụ liên vai trò: ĐẠT 100%
  - Rà soát giao diện 390px, 768px, 1366px: ĐẠT (không tràn ngang)
  - Giám sát lỗi JavaScript console: 0 console errors
```

---

## 6. Cam kết Tuân thủ & Bàn giao Vỏ V1

- **Tính toàn vẹn chức năng:** Toàn bộ vỏ V1 đã kết nối hoàn chỉnh giữa giao diện người dùng và cơ sở dữ liệu thật, không có lỗi chặn luồng (blocker).
- **Không có thành phần AI:** Tuyệt đối không thêm AI, OCR, LLM hay RAG trong phiên bản vỏ V1.
- **Tính khả chuyển:** Tất cả lệnh chạy, cấu hình môi trường `.env.example`, tài khoản seed khởi tạo và quy trình khởi động đã được chuẩn hóa và ghi nhận chi tiết trong `README.md`.
- **Commit bàn giao:** `v1-shell` đánh dấu hoàn tất vỏ V1 theo đặc tả.
