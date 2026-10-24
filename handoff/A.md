# Báo cáo bàn giao Gói A — Backend Nghiệp vụ (V1)

## 1. Thông tin chung
- **Gói thực hiện:** Gói A — Backend nghiệp vụ
- **Nhánh thực hiện:** `goi-a`
- **Commit xuất phát:** `foundation-v1` (`5a88f4654e8674c5d0ef103b591aafca7e7e3762`)
- **Commit hoàn thành:** `6e5ee26` (`feat(package-a): implement business backend, auth, workflow, deadline tick, and tests`)
- **Nguyên tắc tuân thủ:**
  - Tuyệt đối không chỉnh sửa thư mục `web/**` và `contracts/**`.
  - Không sửa đổi migration nền cũ `001_initial_schema.py`.
  - Toàn bộ endpoint, kiểu dữ liệu, mã lỗi và state machine tuân thủ chính xác `contracts/openapi.yaml` và `contracts/states.md`.
  - Sử dụng `ManualReviewProvider`, không gọi bất kỳ LLM, OCR, RAG hay API AI nào.
  - Không tự merge vào nhánh chung (`master`).

---

## 2. Danh sách file đã sửa và tạo mới

### Các file tạo mới:
- `api/app/schemas/entities.py`: Định nghĩa đầy đủ toàn bộ Pydantic models cho Request/Response/Entity theo chuẩn OpenAPI V1.
- `api/app/services/auth_service.py`: Xử lý đăng nhập, bcrypt, phiên HttpOnly cookie, CSRF token validation và RBAC dependencies.
- `api/app/services/workflow_service.py`: Triển khai state machine locked cho Campaign và Case theo `contracts/states.md`.
- `api/app/services/scoring_service.py`: Kiểm tra giới hạn điểm, tính toán tổng điểm bằng `Decimal` chính xác 2 chữ số thập phân.
- `api/app/services/deadline_service.py`: Xử lý hạn thời gian, mở đợt, đóng nộp hồ sơ, timeout bổ sung, nhắc hạn và auto-accept idempotent.
- `api/app/services/file_service.py`: Tải lên, kiểm tra định dạng MIME (PDF/JPG/PNG), giới hạn kích thước (10MB), băm SHA256 và lưu trữ file theo UUID.
- `api/app/services/notification_service.py`: Quản lý thông báo trong web với cơ chế chống gửi trùng (`dedup_key`).
- `api/app/services/audit_service.py`: Ghi nhận nhật ký kiểm toán thao tác hệ thống không thể sửa/xóa.
- `api/tests/conftest.py`: Fixtures kiểm thử độc lập với SQLite in-memory, seed dữ liệu mẫu và helper đăng nhập.
- `api/tests/test_auth_rbac.py`: Bộ test xác thực, phân quyền 4 vai trò, CSRF token và cô lập sinh viên / lớp học.
- `api/tests/test_student_workflow.py`: Bộ test luồng sinh viên: lưu nháp, nộp, upload file an toàn, kiểm tra cấu trúc thiếu minh chứng.
- `api/tests/test_bcs_workflow.py`: Bộ test luồng ban cán sự: hàng chờ, yêu cầu bổ sung minh chứng, chấm duyệt điểm và hoàn tất kiểm tra.
- `api/tests/test_publish_and_feedback.py`: Bộ test cổng công bố (biên bản họp, điều kiện hồ sơ), bảo mật che giấu điểm trước công bố, loại trừ lẫn nhau giữa đồng ý và khiếu nại.
- `api/tests/test_appeals_and_finalization.py`: Bộ test xử lý khiếu nại (KEEP/ADJUST), chốt điểm toàn lớp và xuất CSV cho GVCN.
- `api/tests/test_deadline_tick.py`: Bộ test lệnh xử lý hạn với thời gian giả lập và kiểm tra tính idempotent khi chạy lặp lại.
- `handoff/A.md`: Tài liệu bàn giao này.

### Các file đã cập nhật:
- `api/app/routes/auth.py`: Hoàn thiện API `/auth/login`, `/auth/me`, `/auth/logout` với cookie phiên và CSRF token.
- `api/app/routes/student.py`: Hoàn thiện `/student/current`, cập nhật tiêu chí, tải tệp minh chứng, nộp hồ sơ, đồng ý và khiếu nại.
- `api/app/routes/bcs.py`: Hoàn thiện overview, danh sách hồ sơ có lọc/phân trang, chi tiết hồ sơ 3 vùng, yêu cầu bổ sung, chấm điểm, ghi nhận họp, công bố điểm, danh sách khiếu nại, giải quyết khiếu nại và chốt điểm.
- `api/app/routes/admin.py`: Hoàn thiện tạo đợt, cập nhật cấu hình đợt DRAFT, mở/lên lịch đợt đánh giá.
- `api/app/routes/gvcn.py`: Hoàn thiện xuất tải bảng điểm CSV có BOM UTF-8 sau khi đợt đã chốt (FINALIZED).
- `api/app/routes/files.py`: Hoàn thiện tải/xem tệp minh chứng an toàn với kiểm tra phân quyền sở hữu.
- `api/app/routes/notifications.py`: Hoàn thiện lấy danh sách thông báo và đánh dấu đã đọc.
- `api/app/jobs/tick.py`: Hoàn thiện CLI deadline tick `python -m api.app.jobs.tick [--now ISO8601]`.
- `api/app/schemas/common.py`: Bổ sung `AppError` exception class và các helper format datetime ISO UTC và điểm số thập phân.
- `api/app/schemas/__init__.py`: Export đầy đủ các schema mới.
- `api/scripts/seed.py`: Chuẩn hóa thứ tự nạp sys.path để chạy được cả dạng script trực tiếp lẫn qua module.

---

## 3. Các chức năng nghiệp vụ đã hoàn thành

1. **Xác thực, Phiên & CSRF:**
   - Đăng nhập qua `POST /api/v1/auth/login` kiểm tra mật khẩu băm bcrypt, cấp cookie phiên `HttpOnly; SameSite=Lax` và trả về `csrf_token`.
   - Mọi request thay đổi dữ liệu (`POST`, `PUT`, `DELETE`, `PATCH`) bắt buộc gửi kèm header `X-CSRF-Token` khớp với phiên làm việc.
   - Đăng xuất qua `POST /api/v1/auth/logout` xóa bản ghi phiên trong database và xóa cookie trên client.

2. **Phân quyền truy cập (RBAC) nghiêm ngặt:**
   - Sinh viên chỉ được truy cập và thao tác trên hồ sơ của chính mình; cố tình sửa ID trên URL/API sẽ nhận lỗi `403 FORBIDDEN` hoặc `404 NOT_FOUND`.
   - Ban cán sự (BCS) của Lớp A bị chặn hoàn toàn, không thể xem hoặc chấm hồ sơ của Lớp B (`403 FORBIDDEN`).
   - GVCN chỉ có quyền xem và xuất bảng điểm CSV khi đợt đã chốt (`FINALIZED`); bị chặn không thể gọi API chấm điểm hay xem tệp minh chứng trực tiếp.
   - ADMIN chỉ quản trị cấu hình đợt khi đang ở `DRAFT`; không thể can thiệp sửa đổi điểm của sinh viên.

3. **Luồng nghiệp vụ Sinh viên (Student Workflow):**
   - Xem tổng quan đợt hiện tại, tiêu chí, điểm tự khai và minh chứng qua `GET /student/current`.
   - **Bảo mật điểm dự kiến:** Khi hồ sơ chưa đến trạng thái `PUBLISHED`, API tuyệt đối trả về `null` cho các trường `proposed_total`, `approved_score` và `bcs_reason` của BCS để ngăn rò rỉ điểm trước khi công bố chính thức.
   - Lưu nháp điểm tự khai (`PUT /student/cases/{id}/claims/{criterionId}`) kiểm tra `0 <= self_score <= max_score` và tự động cộng tổng tự khai `claimed_total`.
   - Tải lên minh chứng an toàn (`POST /student/cases/{id}/evidence`) kiểm tra định dạng MIME (chỉ nhận PDF, JPG, PNG), giới hạn tối đa 10MB, băm SHA256 và lưu file vào `storage/` với tên UUID.
   - Nộp hồ sơ (`POST /student/cases/{id}/submit`):
     - Kiểm tra tính đầy đủ cấu trúc: nếu tiêu chí yêu cầu minh chứng (`requires_evidence=True`) mà chưa có file thì chuyển sang `NEEDS_INFO`, tăng `info_round`, đặt hạn bổ sung và gửi thông báo.
     - Nếu đã hết số lượt bổ sung cho phép (`info_round >= max_info_rounds`) thì chuyển thẳng sang `CLOSED_INCOMPLETE`.
     - Nếu hồ sơ đủ cấu trúc thông tin: chuyển qua `ManualReviewProvider`, đẩy hồ sơ vào trạng thái `BCS_REVIEW`.

4. **Luồng nghiệp vụ Ban cán sự (BCS Workflow):**
   - Dashboard thống kê tổng quan (`GET /bcs/campaigns/{id}/overview`).
   - Danh sách hồ sơ có phân trang và tìm kiếm theo tên/mã SV (`GET /bcs/campaigns/{id}/cases`).
   - Chi tiết hồ sơ 3 vùng (`GET /bcs/cases/{id}`): hiển thị minh chứng gốc, điểm tự khai, quyết định duyệt của BCS và lịch sử thao tác từ audit log.
   - Yêu cầu bổ sung thông tin hoặc minh chứng (`POST /bcs/cases/{id}/supplement-requests`) kiểm tra trần số lượt bổ sung (`max_info_rounds`, `max_proof_rounds`), đặt hạn và gửi thông báo.
   - Chấm duyệt điểm từng tiêu chí (`PUT /bcs/cases/{id}/claims/{criterionId}/review`): kiểm tra giới hạn điểm trần; bắt buộc phải nhập lý do nếu điểm duyệt khác điểm tự khai.
   - Hoàn tất kiểm tra (`POST /bcs/cases/{id}/complete-review`): kiểm tra toàn bộ tiêu chí đã được duyệt điểm, tính tổng `proposed_total` và chuyển sang `PROPOSED`.

5. **Cuộc họp & Công bố kết quả:**
   - Ghi nhận biên bản cuộc họp BCS và cuộc họp Lớp (`POST /bcs/campaigns/{id}/meetings`).
   - Công bố điểm dự kiến (`POST /bcs/campaigns/{id}/publish`):
     - Kiểm tra điều kiện tiên quyết: bắt buộc phải có đủ cả 2 cuộc họp (`BCS` và `CLASS`).
     - Toàn bộ hồ sơ trong đợt phải ở trạng thái `PROPOSED` hoặc `CLOSED_*`.
     - Tạo bản ghi `score_snapshots(kind=PUBLISHED)` bất biến cho từng sinh viên.
     - Chuyển trạng thái đợt và hồ sơ sang `PUBLISHED`, thiết lập hạn phản hồi (`appeal_deadline_at`) và gửi thông báo công bố đến tất cả sinh viên.

6. **Phản hồi, Khiếu nại & Chốt điểm:**
   - Sinh viên đồng ý điểm dự kiến (`POST /student/cases/{id}/accept`) ghi nhận `acceptance_source = EXPLICIT`.
   - Sinh viên khiếu nại (`POST /student/cases/{id}/appeals`) chọn một hoặc nhiều tiêu chí kèm lý do chi tiết, chuyển trạng thái sang `APPEALED`.
   - Hai hành động Đồng ý và Khiếu nại loại trừ lẫn nhau (đã đồng ý thì không thể khiếu nại và ngược lại).
   - BCS giải quyết khiếu nại (`POST /bcs/appeals/{id}/resolve`): chọn `KEEP` hoặc `ADJUST` kèm điểm mới và lý do; tự động cập nhật lại `approved_score`, tính lại `proposed_total` và ghi nhận lịch sử kiểm toán. Khi mọi khiếu nại của hồ sơ được giải quyết, hồ sơ chuyển sang `RESOLVED`.
   - BCS chốt điểm toàn lớp (`POST /bcs/campaigns/{id}/finalize`): kiểm tra toàn bộ hồ sơ đã ở trạng thái kết thúc (`ACCEPTED`, `ACCEPTED_AUTO`, `RESOLVED`, `CLOSED_*`), tạo snapshot điểm chính thức `score_snapshots(kind=FINAL)`.

7. **Báo cáo GVCN:**
   - GVCN tải file CSV bảng điểm chính thức (`GET /gvcn/campaigns/{id}/final-scores.csv`). Chỉ cho phép tải khi đợt đã `FINALIZED` và đúng lớp phụ trách. File CSV được chèn UTF-8 BOM (`\ufeff`) để hiển thị tiếng Việt hoàn hảo trên Excel.

8. **Deadline Tick CLI & Tính Idempotent:**
   - Lệnh `python -m api.app.jobs.tick [--now ISO8601]` hỗ trợ chạy tự động và kiểm thử thời gian giả lập.
   - Tự động mở đợt `SCHEDULED -> OPEN` khi đến `open_at` và khởi tạo hồ sơ cho sinh viên.
   - Tự động đóng thời gian nộp `OPEN -> REVIEW`, chuyển các hồ sơ chưa nộp sang `CLOSED_NO_SUBMIT`.
   - Tự động đóng hồ sơ quá hạn bổ sung INFO sang `CLOSED_INCOMPLETE`.
   - Tự động chuyển hồ sơ quá hạn bổ sung PROOF về lại hàng chờ `BCS_REVIEW` để BCS kết luận trên minh chứng hiện có.
   - Tự động gửi thông báo nhắc hạn sau `reminder_after_hours`.
   - Tự động chấp thuận `ACCEPTED_AUTO` (`acceptance_source = TIMEOUT`) cho các sinh viên chưa phản hồi khi hết hạn khiếu nại.
   - Kiểm tra lặp lại nhiều lần tại cùng mốc thời gian không gây sai lệch dữ liệu, không tạo bản ghi trùng và không gửi trùng thông báo (nhờ `dedup_key`).

---

## 4. Kết quả kiểm thử thực tế

Toàn bộ test suite được viết và thực thi bằng `pytest` trong môi trường backend local.

### Lệnh chạy kiểm thử:
```bash
python -m pytest api/tests
```

### Kết quả chi tiết:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0
rootdir: D:\Hoc Tap\NAM 4\Học kì 1\QLQTKD\AI_DRL_Project
plugins: anyio-4.13.0
collected 24 items

api\tests\test_appeals_and_finalization.py ..                            [  8%]
api\tests\test_auth_rbac.py .......                                      [ 37%]
api\tests\test_bcs_workflow.py ..                                        [ 45%]
api\tests\test_deadline_tick.py ...                                      [ 58%]
api\tests\test_health.py ...                                             [ 70%]
api\tests\test_publish_and_feedback.py ...                               [ 83%]
api\tests\test_student_workflow.py ....                                  [100%]

====================== 24 passed in 27.24s ======================
```

### Bảng đối chiếu 16 tiêu chí kiểm thử chấp nhận (Mục 9 đặc tả V1):

| STT | Tiêu chí chấp nhận theo đặc tả V1 | Test file & Hàm test tương ứng | Kết quả |
|:---:|---|---|:---:|
| 1 | STUDENT chỉ thấy case của chính mình; sửa ID trên URL/API nhận 404/403 | `test_auth_rbac.py::test_acceptance_criteria_1_student_isolation` | **PASSED** |
| 2 | BCS lớp A không mở được case lớp B; GVCN không gọi API sửa điểm | `test_auth_rbac.py::test_acceptance_criteria_2_bcs_cross_class_and_gvcn_rbac` | **PASSED** |
| 3 | Form lưu nháp rồi tải lại giữ nguyên điểm và tệp; tổng tự khai đúng | `test_student_workflow.py::test_acceptance_criteria_3_save_draft_and_total` | **PASSED** |
| 4 | Nộp thiếu minh chứng bắt buộc tạo NEEDS_INFO và thông báo đúng mục; bổ sung đúng hạn quay lại BCS_REVIEW | `test_student_workflow.py::test_acceptance_criteria_4_submit_missing_evidence_creates_needs_info` | **PASSED** |
| 5 | Hết lượt hoặc hết hạn bổ sung INFO đóng CLOSED_INCOMPLETE; không tạo vòng lặp tiếp | `test_student_workflow.py::test_acceptance_criteria_5_exceeding_info_rounds_closes_incomplete` | **PASSED** |
| 6 | BCS yêu cầu PROOF, SV nộp lại; quá hạn PROOF quay BCS để kết luận, không tự trừ điểm | `test_bcs_workflow.py::test_acceptance_criteria_6_bcs_request_proof_and_timeout` | **PASSED** |
| 7 | BCS nhập điểm vượt max hoặc khác tự khai mà không có lý do bị 422; tổng dự kiến cộng đúng | `test_bcs_workflow.py::test_acceptance_criteria_7_bcs_review_score_validation_and_reasons` | **PASSED** |
| 8 | Chưa đủ hai cuộc họp hoặc còn case chờ BCS thì không công bố; đủ điều kiện thì công bố một lần | `test_publish_and_feedback.py::test_acceptance_criteria_8_meetings_and_publish_gate` | **PASSED** |
| 9 | Trước công bố SV không thấy điểm dự kiến; sau công bố thấy đúng điểm và hạn phản hồi | `test_publish_and_feedback.py::test_acceptance_criteria_9_score_masking_before_and_after_publish` | **PASSED** |
| 10 | SV đồng ý thì không thể khiếu nại; khiếu nại thì không thể đồng ý | `test_publish_and_feedback.py::test_acceptance_criteria_10_accept_appeal_mutual_exclusion` | **PASSED** |
| 11 | BCS giải quyết khiếu nại KEEP và ADJUST; điểm cũ/mới, lý do, người xử lý đều truy được | `test_appeals_and_finalization.py::test_acceptance_criteria_11_appeals_resolution_keep_and_adjust` | **PASSED** |
| 12 | Deadline tick chạy hai lần không gửi trùng thông báo và không tăng lượt hai lần | `test_deadline_tick.py::test_acceptance_criteria_12_and_13_tick_idempotency_and_auto_accept` | **PASSED** |
| 13 | Quá hạn phản hồi mà SV chưa đồng ý/khiếu nại thì thành ACCEPTED_AUTO đúng một lần; SV đã phản hồi không bị tự chấp nhận | `test_deadline_tick.py::test_acceptance_criteria_12_and_13_tick_idempotency_and_auto_accept` | **PASSED** |
| 14 | Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt | `test_appeals_and_finalization.py::test_acceptance_criteria_14_finalize_gate_and_gvcn_csv` | **PASSED** |
| 15 | Tệp không thể xem bằng URL storage trực tiếp; API kiểm quyền và MIME, chặn loại tệp ngoài PDF/JPG/PNG | `test_student_workflow.py::test_acceptance_criteria_15_file_upload_security` | **PASSED** |
| 16 | Đợt SCHEDULED chưa tạo case/chưa cho nộp; tick ở open_at tạo đúng một case mỗi SV, chạy lặp lại không tạo trùng | `test_deadline_tick.py::test_acceptance_criteria_16_scheduled_campaign_and_tick_open` | **PASSED** |

---

## 5. Lưu ý cho người ghép ở Giai đoạn 2
1. **Khởi tạo dữ liệu mẫu (Seed Data):**
   - Lệnh seed idempotent: `python api/scripts/seed.py` hoặc `python -m api.scripts.seed`.
   - Đọc mật khẩu demo từ biến môi trường `DEMO_PASSWORD` (mặc định: `Demo@123456`).
2. **Khởi động Backend:**
   - `uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload`
3. **Chạy kiểm tra hạn (Deadline Tick):**
   - Theo thời gian thực tế: `python -m api.app.jobs.tick`
   - Theo thời gian giả lập: `python -m api.app.jobs.tick --now 2026-10-30T10:00:00Z`
4. **Hợp đồng OpenAPI:**
   - Không phát sinh thay đổi hợp đồng API nào ngoài các chuẩn đã khóa tại Giai đoạn 0. Mọi request/response đều khớp 100% với `contracts/openapi.yaml`.
