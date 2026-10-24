# Báo cáo Bàn giao Gói B — Frontend Sinh viên (Student Portal)

- **Nhánh làm việc:** `goi-b`
- **Commit hash hoàn thành:** `ddc6811`
- **Cam kết gốc:** `5a88f46` (tag: `foundation-v1`)
- **Ngày hoàn thành:** 24/10/2026
- **Người thực hiện:** AI Pair Programmer (Gói B)
- **Tình trạng merge:** Chưa merge vào nhánh chung (tuân thủ quy tắc song song).

---

## 1. Danh sách file thuộc phạm vi quản lý & đã thực hiện

Chỉ thao tác trong đúng vùng file được giao theo tài liệu `PHAN_CHIA_CODE_SONG_SONG_V1.md`:

### 1.1. Trang màn hình Sinh viên (`web/src/pages/student/**`)
- `web/src/pages/student/StudentDashboard.tsx`: Bảng tin sinh viên, hiển thị trạng thái hồ sơ, đợt đánh giá, hạn chót, tổng điểm tự khai, thông báo chưa đọc, khối "Việc tiếp theo cần làm" theo ngữ cảnh trạng thái hồ sơ.
- `web/src/pages/student/StudentSubmission.tsx`: Biểu mẫu tự đánh giá, điền điểm tự khai từng tiêu chí (tự động cộng tổng điểm real-time), đính kèm minh chứng, lưu nháp, nộp hồ sơ kèm hộp thoại xác nhận `ConfirmDialog`. Khóa form khi ở trạng thái chỉ đọc hoặc quá hạn.
- `web/src/pages/student/StudentResult.tsx`: Kết quả đánh giá dự kiến. Tuân thủ tuyệt đối quy tắc bảo mật: trước `PUBLISHED` ẩn toàn bộ điểm BCS duyệt và lý do; sau `PUBLISHED` hiển thị bảng so sánh chi tiết, cảnh báo điểm khác biệt, nút "Đồng ý" (kèm `ConfirmDialog`) và nút "Khiếu nại".
- `web/src/pages/student/StudentAppeal.tsx`: Màn hình khiếu nại điểm đánh giá. Cho phép chọn nhiều tiêu chí, nhập lý do bắt buộc cho từng tiêu chí, gửi khiếu nại (chỉ 1 lần duy nhất) và theo dõi tiến độ xử lý/kết luận từ Ban cán sự.

### 1.2. Thành phần dùng riêng Sinh viên (`web/src/components/student/**`)
- `web/src/components/student/studentMockData.ts`: Dữ liệu mock & fixtures chuẩn hóa theo đúng hợp đồng `contracts/openapi.yaml` và `contracts/seed-fixtures.json`, hỗ trợ 10 kịch bản trạng thái (`DRAFT`, `NEEDS_INFO`, `NEEDS_PROOF`, `BCS_REVIEW`, `PUBLISHED`, `ACCEPTED`, `APPEALED`, `RESOLVED`, `FINALIZED`, `CLOSED_NO_SUBMIT`).
- `web/src/components/student/studentService.ts`: Tầng dịch vụ dữ liệu SV. Gọi `api` từ `web/src/api/client.ts` khi ở chế độ `Live API`, và fallback/mô phỏng tương tác trên `Mock Fixtures`. Quản lý `expected_version`, xử lý concurrency `409 CASE_CHANGED`, validate tệp upload, nộp hồ sơ, đồng ý và khiếu nại.
- `web/src/components/student/StudentScenarioBar.tsx`: Thanh công cụ điều khiển kịch bản demo (thu gọn được), cho phép reviewer chuyển đổi tức thì giữa các trạng thái hồ sơ và giữa chế độ Live API / Mock để kiểm tra toàn diện UI/UX.
- `web/src/components/student/CriterionCard.tsx`: Card tiêu chí tự chấm, hỗ trợ kiểm tra ràng buộc `0 <= score <= max_score`, hiển thị cảnh báo khi tiêu chí có yêu cầu bổ sung (`supplement_request`), quản lý tệp minh chứng và chế độ chỉ đọc.
- `web/src/components/student/EvidenceViewer.tsx`: Component hiển thị thông tin tệp minh chứng (icon, tên, định dạng, dung lượng KB, thời gian upload giờ VN, liên kết xem an toàn `/files/{id}`, nút xóa khi còn quyền sửa).
- `web/src/components/student/studentStyles.css`: Tối ưu hóa giao diện responsive đặc thù cho sinh viên từ màn hình di động hẹp (360px – 430px) đến máy tính bảng và desktop (1200px). Đảm bảo target chạm cảm ứng >= 44px, nút full-width trên mobile, sticky action bar.

### 1.3. Kiểm thử đơn vị & tích hợp (`web/src/tests/student/**`)
- `web/src/tests/student/studentLogic.test.ts`: 25 test kiểm thử tính toán điểm, xác thực form, khóa trạng thái, phân quyền, bảo mật thông tin điểm dự kiến, concurrency, upload file và quy trình nộp/đồng ý/khiếu nại.

### 1.4. Tài liệu bàn giao (`handoff/**`)
- `handoff/B.md`: Tài liệu này.

---

## 2. Chi tiết các chức năng đã hoàn thành

| STT | Chức năng | Mô tả chi tiết | Trạng thái |
|---|---|---|:---:|
| 1 | **Dashboard Sinh viên** | Thẻ đợt, hạn nộp, trạng thái hồ sơ, thông báo chưa đọc, nút điều hướng ngữ cảnh theo trạng thái hiện tại. | **ĐẠT** |
| 2 | **Form Tự đánh giá** | Hiển thị tiêu chí theo `sort_order`, `requires_evidence`. Tự động cộng tổng điểm tự khai `claimed_total = SUM(self_score)`. | **ĐẠT** |
| 3 | **Đính kèm minh chứng** | Kiểm tra định dạng phía client (chỉ nhận PDF, JPG, PNG) và dung lượng (tối đa 10 MB). Hiển thị danh sách tệp đính kèm. | **ĐẠT** |
| 4 | **Lưu nháp hồ sơ** | Gọi `PUT /student/cases/{caseId}/claims/{criterionId}` kèm `expected_version`, cập nhật version và hiển thị thông báo thành công. | **ĐẠT** |
| 5 | **Nộp hồ sơ & Xác nhận** | Kiểm tra điền điểm toàn bộ tiêu chí; cảnh báo nếu thiếu minh chứng bắt buộc; mở `ConfirmDialog` nêu hậu quả nộp; chuyển trạng thái sang `BCS_REVIEW` (hoặc `NEEDS_INFO` nếu thiếu minh chứng). | **ĐẠT** |
| 6 | **Bổ sung thông tin / minh chứng** | Khi ở `NEEDS_INFO` hoặc `NEEDS_PROOF`, hiển thị lý do bổ sung và hạn bổ sung cụ thể ngay trên tiêu chí bị gắn cờ; cho phép SV sửa/tải lại tệp và nộp bổ sung. | **ĐẠT** |
| 7 | **Bảo mật điểm trước công bố** | Trước `PUBLISHED`: ẩn 100% `approved_score`, `proposed_total` và `bcs_reason`, hiển thị thông báo chờ họp bình xét. | **ĐẠT** |
| 8 | **Xem kết quả sau công bố** | Sau `PUBLISHED`: bảng so sánh 4 cột (Tiêu chí, Tự khai, BCS duyệt, Lý do BCS); làm nổi bật các tiêu chí bị điều chỉnh điểm khác tự khai. | **ĐẠT** |
| 9 | **Đồng ý với điểm dự kiến** | Nút `Đồng ý với điểm dự kiến` mở `ConfirmDialog`, gọi `POST /student/cases/{caseId}/accept` với `expected_version`, chuyển sang `ACCEPTED`. | **ĐẠT** |
| 10 | **Khiếu nại điểm đánh giá** | Chọn 1 hoặc nhiều tiêu chí, bắt buộc nhập lý do chi tiết; `ConfirmDialog` xác nhận gửi 1 lần duy nhất; gọi `POST /student/cases/{caseId}/appeals`; hiển thị tiến độ và kết quả giải quyết (`KEEP`/`ADJUST`). | **ĐẠT** |
| 11 | **Loại trừ tương hỗ (Accept vs Appeal)** | Đã đồng ý thì không thể khiếu nại; đã khiếu nại thì không thể đồng ý; các nút tương ứng tự động khóa/ẩn. | **ĐẠT** |
| 12 | **Khóa nút theo deadline & status** | Quá hạn nộp hoặc hồ sơ không thuộc `DRAFT`/`NEEDS_*` thì khóa toàn bộ form; quá hạn khiếu nại thì khóa nút phản hồi. | **ĐẠT** |
| 13 | **Xử lý xung đột phiên bản (409)** | Gửi kèm `expected_version`, bắt lỗi `409 CASE_CHANGED` và thông báo người dùng tải lại dữ liệu. | **ĐẠT** |
| 14 | **Thông báo trong hệ thống** | Lấy danh sách thông báo, hiển thị huy hiệu chưa đọc, hỗ trợ đánh dấu đã đọc (`POST /notifications/{id}/read`). | **ĐẠT** |
| 15 | **Mobile Responsive (360px – 430px)** | Giao diện 1 cột trên điện thoại, nút bấm kích thước tối thiểu 44px, sticky action bar, bảng kết quả scroll ngang mượt mà. | **ĐẠT** |

---

## 3. Lệnh kiểm thử đã thực sự chạy & Kết quả thực tế

### 3.1. Kiểm tra biên dịch TypeScript & Đóng gói Frontend (Production Build)
- **Lệnh chạy:**
  ```powershell
  cd web; npm.cmd run build
  ```
- **Kết quả thực tế:**
  ```text
  > web-cham-diem-ren-luyen@1.0.0 build
  > tsc && vite build

  vite v5.4.21 building for production...
  transforming...
  ✓ 1603 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                   0.48 kB │ gzip:  0.33 kB
  dist/assets/index-8MiOrGud.css    6.97 kB │ gzip:  2.02 kB
  dist/assets/index-DeVN0eGu.js   361.24 kB │ gzip: 97.46 kB
  ✓ built in 4.13s
  ```
- **Đánh giá:** Mã nguồn sạch, không lỗi cú pháp, không lỗi kiểu TypeScript (`tsc` đạt 0 lỗi), build hoàn tất thành công.

---

### 3.2. Chạy bộ kiểm thử tự động Frontend Sinh viên (`web/src/tests/student/`)
- **Lệnh chạy:**
  ```powershell
  npx.cmd tsx --test web/src/tests/student/studentLogic.test.ts
  ```
- **Kết quả thực tế:**
  ```text
  ▶ Gói B - Logic Frontend Sinh viên
    ▶ Tính toán tổng điểm tự khai (claimed_total)
      ✔ Cộng chính xác các điểm dạng chuỗi thập phân mà không bị lỗi số thực (float glitch) (0.8018ms)
      ✔ Xử lý an toàn khi tiêu chí có self_score là null hoặc rỗng (0.2947ms)
      ✔ Tổng điểm tối đa của 3 tiêu chí demo đúng 30.00 điểm (0.2483ms)
    ✔ Tính toán tổng điểm tự khai (claimed_total) (2.6285ms)
    ▶ Xác thực ô nhập điểm tự chấm và lý do khiếu nại
      ✔ Chấp nhận các giá trị điểm hợp lệ (0.2389ms)
      ✔ Từ chối điểm âm hoặc điểm vượt quá trần tiêu chí (0.1553ms)
      ✔ Xác thực tệp minh chứng: chỉ chấp nhận PDF/JPG/PNG và <= 10MB (0.1943ms)
    ✔ Xác thực ô nhập điểm tự chấm và lý do khiếu nại (0.8386ms)
    ▶ Quy tắc khóa trạng thái (Editable vs Read-only)
      ✔ Chỉ cho phép sửa ở DRAFT, NEEDS_INFO, NEEDS_PROOF (0.1989ms)
      ✔ Khóa toàn bộ form ở các trạng thái đang kiểm tra hoặc đã xong (0.2033ms)
      ✔ Khóa form khi đã quá thời hạn nộp (0.3349ms)
    ✔ Quy tắc khóa trạng thái (Editable vs Read-only) (1.0142ms)
    ▶ Bảo vệ tính toàn vẹn: Không rò rỉ điểm BCS trước PUBLISHED
      ✔ MOCK_STUDENT_DRAFT không có proposed_total và không có approved_score (0.433ms)
      ✔ MOCK_STUDENT_NEEDS_INFO không có proposed_total (0.2045ms)
      ✔ MOCK_STUDENT_PUBLISHED có điểm dự kiến hợp lệ và lý do BCS (0.1458ms)
    ✔ Bảo vệ tính toàn vẹn: Không rò rỉ điểm BCS trước PUBLISHED (1.1126ms)
    ▶ Loại trừ tương hỗ (Mutual Exclusion) giữa Đồng ý và Khiếu nại
      ✔ Khi hồ sơ ở ACCEPTED, không được phép khiếu nại (0.1544ms)
      ✔ Khi hồ sơ ở APPEALED, không được phép đồng ý (0.0984ms)
      ✔ Hồ sơ RESOLVED phản ánh đúng điểm mới và kết luận BCS (0.1473ms)
      ✔ Hồ sơ FINALIZED có final_total (0.1181ms)
      ✔ Hồ sơ CLOSED_NO_SUBMIT giữ đúng trạng thái đóng (0.0698ms)
    ✔ Loại trừ tương hỗ (Mutual Exclusion) giữa Đồng ý và Khiếu nại (0.7914ms)
    ▶ Xử lý xung đột phiên bản (Concurrency expected_version)
      ✔ Ném lỗi 409 CASE_CHANGED nếu expected_version không khớp (0.4686ms)
      ✔ Cập nhật thành công và tăng version khi expected_version đúng (0.2163ms)
    ✔ Xử lý xung đột phiên bản (Concurrency expected_version) (0.7803ms)
    ▶ Quy trình nộp hồ sơ, tải minh chứng, đồng ý và khiếu nại
      ✔ Tải tệp minh chứng: từ chối tệp không đúng định dạng (0.3353ms)
      ✔ Tải tệp minh chứng: thành công khi tệp hợp lệ (PDF/JPG/PNG <= 10MB) (1.2664ms)
      ✔ Nộp hồ sơ khi thiếu minh chứng bắt buộc -> chuyển NEEDS_INFO (0.4204ms)
      ✔ Chấp nhận điểm dự kiến -> chuyển ACCEPTED với acceptance_source=EXPLICIT (0.2365ms)
      ✔ Gửi khiếu nại -> chuyển APPEALED và tạo bản ghi appeals (0.3022ms)
    ✔ Quy trình nộp hồ sơ, tải minh chứng, đồng ý và khiếu nại (2.7645ms)
    ▶ Khớp cấu trúc hợp đồng OpenAPI
      ✔ Tất cả mock scenarios đều đầy đủ thuộc tính theo OpenAPI schema (0.249ms)
    ✔ Khớp cấu trúc hợp đồng OpenAPI (0.3491ms)
  ✔ Gói B - Logic Frontend Sinh viên (11.4508ms)
  ℹ tests 25
  ℹ suites 9
  ℹ pass 25
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 242.0197
  ```
- **Đánh giá:** Toàn bộ 25/25 test ca kiểm thử đạt 100% không có lỗi.

---

## 4. Ghi chú cho Giai đoạn 2 (Tích hợp đầu-cuối)

1. **Khả năng chuyển đổi Mock sang Live API:**
   - Dịch vụ `studentService.ts` đã xây dựng sẵn 2 chế độ (`live` và `mock`). Khi chạy Giai đoạn 2, chỉ cần chuyển toggle hoặc cấu hình `studentService.setMode('live')`, toàn bộ các lệnh gọi API (`GET /student/current`, `PUT /claims`, `POST /evidence`, `POST /submit`, `POST /accept`, `POST /appeals`, `GET /notifications`) sẽ gọi trực tiếp `api` từ `web/src/api/client.ts`.
2. **Lưu ý nhỏ về `api/client.ts`:**
   - Trong `api/client.ts`, dòng 8 sử dụng `import.meta.env.VITE_API_BASE_URL`. Ở môi trường trình duyệt Vite, biểu thức này hoạt động bình thường. `studentService.ts` đã dùng cơ chế nạp động an toàn để không gây xung đột khi test runner chạy độc lập ngoài trình duyệt. Ở Giai đoạn 2 khi ghép nối, có thể giữ nguyên hoặc hỗ trợ thêm `process.env` nếu có kiểm thử backend chạy bằng Node.
3. **Quy tắc bảo mật điểm:**
   - Backend cần đảm bảo endpoint `GET /student/current` trước trạng thái `PUBLISHED` không trả về `approved_score` hoặc `proposed_total`. Frontend sinh viên đã thiết kế để không bao giờ hiển thị điểm duyệt trước thời điểm công bố.
