# Ghi nhận vấn đề hợp đồng từ Gói D (D-contract-issues.md)

Tài liệu này ghi nhận các điểm lưu ý về hợp đồng API và fixtures được phát hiện trong quá trình xây dựng bộ kiểm thử hợp đồng và kiểm thử chấp nhận (Gói D). Người ghép ở Giai đoạn 2 sẽ quyết định và cập nhật hợp đồng đồng thời một lần.

---

### 1. Route kiểm tra phân quyền truy cập hồ sơ sinh viên theo ID

- **Route/field hiện tại:** `GET /student/current` có trong OpenAPI; không có `GET /student/cases/{caseId}` trong `openapi.yaml` dành riêng cho vai trò `STUDENT`.
- **Vấn đề:** Tiêu chí 9.1 đặc tả yêu cầu: *"STUDENT chỉ thấy case của chính mình; sửa ID trên URL/API để đọc case khác nhận 404/403."* Hiện tại, sinh viên chủ yếu thao tác qua `GET /student/current` và các route mutation `PUT /student/cases/{caseId}/claims/{criterionId}`, `POST /student/cases/{caseId}/submit`.
- **Thay đổi đề nghị:**
  - Lựa chọn 1: Bổ sung route tường minh `GET /student/cases/{caseId}` vào `openapi.yaml` để hỗ trợ điều hướng trực tiếp bằng URL trên frontend, kiểm tra quyền sở hữu case và trả về 403/404 nếu không phải case của mình.
  - Lựa chọn 2: Duy trì `GET /student/current` làm route đọc duy nhất của sinh viên; kiểm soát sửa ID trên URL qua các route mutation (`PUT /student/cases/{caseId}/claims/...`, `POST /student/cases/{caseId}/submit`).
- **Ảnh hưởng:** Giúp thống nhất hành vi URL routing trên frontend (Gói B) và kiểm tra phân quyền chặt chẽ trên backend (Gói A).

---

### 2. Cấu trúc trường `claims` trong `StudentCurrentResponse` và mock response

- **Route/field hiện tại:** `contracts/openapi.yaml` (`StudentCurrentResponse`) và `contracts/seed-fixtures.json` (`student_current_draft`).
- **Vấn đề:** Trong `seed-fixtures.json`, mảng `claims` nằm ở cấp gốc của response (`mock_responses.student_current_draft.claims`), đồng thời trong `openapi.yaml` schema `StudentCurrentResponse` cũng định nghĩa `claims` ở cấp gốc. Tuy nhiên một số mô hình tài liệu mô tả `claims` nằm lồng trong `case.claims`.
- **Thay đổi đề nghị:** Giữ nhất quán cấu trúc cấp gốc: `{ "campaign": ..., "case": ..., "criteria": [...], "claims": [...], "supplement_requests": [...], "appeals": [...] }` trên cả backend và mock client frontend.
- **Ảnh hưởng:** Đảm bảo TypeScript client (`web/src/api/types.ts`) và backend route `GET /student/current` deserialize khớp 100%.

---

### 3. Chuỗi định danh học kỳ `campaign.term` giữa văn bản và fixture

- **Route/field hiện tại:** `contracts/seed-fixtures.json` -> `campaign.term = "HK1-2026-2027"`, trong khi ví dụ Mục 7 đặc tả ghi `"HK1-DEMO"`.
- **Vấn đề:** Không ảnh hưởng nghiệp vụ vì đều là kiểu `string`, nhưng cần thống nhất giá trị mặc định cho dữ liệu demo.
- **Thay đổi đề nghị:** Giữ nguyên `"HK1-2026-2027"` trong fixture hiện tại và coi đây là chuẩn seed.
- **Ảnh hưởng:** Không ảnh hưởng logic nghiệp vụ.
