# ĐẶC TẢ TRIỂN KHAI V1 — WEB CHẤM ĐIỂM RÈN LUYỆN

> **Dành cho AI lập trình:** Hãy xây frontend và backend theo tài liệu này. Đây là bản **vỏ chạy được từ đầu đến cuối bằng thao tác của người và luật đơn giản**. Không gọi LLM, OCR, RAG, API AI hoặc dựng agent framework ở V1. Không giả vờ đã có kết quả AI. Giữ các điểm mở rộng ghi ở Mục 11 để lắp bốn vai trò agent sau.

**Nguồn nghiệp vụ:** `Input/Nhom8_TOBE_NangCao_BPMN20_v6.bpmn`. Chương 3 quyết định nguyên tắc: AI sau này chỉ đọc/đối chiếu; tính điểm và thời hạn dùng luật; BCS phê duyệt.  
**Kết quả V1:** một đợt demo đi được từ mở đợt → SV tự chấm/nộp → BCS kiểm tra thủ công/tạo điểm dự kiến → họp/công bố → SV đồng ý hoặc khiếu nại → BCS giải quyết/chốt → GVCN xem bảng điểm.

## 1. Phạm vi cố định

### Phải có ở V1

- Đăng nhập local với 4 vai trò: `STUDENT`, `BCS`, `GVCN`, `ADMIN` (ADMIN chỉ cấu hình đợt/demo; BPMN không mô tả thêm quyền quyết định điểm cho ADMIN).
- Một lớp có nhiều sinh viên; một đợt thuộc một lớp; mỗi sinh viên có đúng một hồ sơ trong đợt.
- Cấu hình đợt, tiêu chí chấm, hạn và trần số lượt bổ sung.
- Form tự chấm, tải PDF/JPG/PNG, lưu nháp, nộp và bổ sung.
- Hàng chờ BCS, xem minh chứng, yêu cầu bổ sung, duyệt điểm **thủ công theo từng tiêu chí**, ghi lý do khi thay đổi điểm.
- Tổng điểm dự kiến do backend cộng từ điểm BCS duyệt, kiểm tra giới hạn điểm từng tiêu chí.
- Ghi nhận đã họp BCS và đã họp lớp; công bố điểm dự kiến sau khi hồ sơ đủ điều kiện.
- Sinh viên xem điểm, đồng ý hoặc khiếu nại; BCS giữ nguyên/điều chỉnh điểm, ghi lý do; chốt và cho GVCN xem/tải CSV.
- Thông báo **trong web**, hạn, giới hạn vòng lặp, nhật ký thao tác, phân quyền truy cập.
- Lệnh xử lý deadline chạy được thủ công và theo lịch local; có kiểm thử với thời gian giả lập.

### Chưa làm ở V1

- OCR, mô hình AI, RAG, tự chấm hợp lệ, điểm tin cậy, tự phê duyệt minh chứng, chat với agent.
- Email/SMS, SSO trường, thanh toán, báo cáo phân tích, nhiều trường/nhiều khoa.
- Diễn giải quy chế chấm điểm thật. Dữ liệu demo phải được gắn nhãn **“Dữ liệu minh họa — không dùng để ra quyết định thật”**.

**Quyết định thiết kế quan trọng:** khi chưa có AI, mọi hồ sơ **đủ cấu trúc** sau khi nộp đi vào `BCS_REVIEW`; hồ sơ thiếu đi `NEEDS_INFO`. Không tạo kết quả “AI hợp lệ” giả. Sau này adapter AI có thể tự tạo phát hiện và chỉ đẩy hồ sơ cần người xem vào hàng chờ.

## 2. Công nghệ và cấu trúc dự án

Tạo một repo mới tại thư mục dự án do người code chọn, **không sửa file BPMN**. Cấu trúc:

```text
web/                 React + TypeScript + Vite
  src/api/            HTTP client và kiểu dữ liệu API
  src/components/     Layout, StatusBadge, Deadline, FilePreview, ConfirmDialog
  src/pages/student/  Dashboard, Submission, Result, Appeal
  src/pages/bcs/      Dashboard, CaseQueue, CaseDetail, Scoreboard, Appeals
  src/pages/admin/    CampaignSetup
  src/pages/gvcn/     FinalScores
api/                 FastAPI + Python
  app/routes/         auth, student, bcs, admin, gvcn, files
  app/models/         ORM
  app/schemas/        request/response
  app/services/       workflow, scoring, deadlines, notifications, audit
  app/review/         giao diện ReviewProvider, ManualReviewProvider
  app/jobs/           lệnh tick xử lý hạn
  alembic/            migration
  tests/              kiểm thử API và luật
storage/             tệp local; gitignore
compose.yaml         PostgreSQL cho môi trường local
.env.example         các biến cấu hình, không chứa bí mật thật
README.md            hướng dẫn chạy và tài khoản demo
```

Chọn React/Vite cho UI, FastAPI cho API và PostgreSQL cho dữ liệu. Dùng SQLAlchemy ORM + Alembic migration; khóa phiên bản thư viện bằng lockfile. Tài liệu chính thức: [Vite](https://vite.dev/guide/), [React](https://react.dev/learn), [FastAPI](https://fastapi.tiangolo.com/tutorial/), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/index.html), [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html). Lưu tệp bằng tên UUID trong `storage/`, metadata ở database; mọi lần đọc tệp phải qua API kiểm tra quyền.

## 3. Vai trò và quyền

| Hành động | STUDENT | BCS cùng lớp | GVCN cùng lớp | ADMIN |
|---|:---:|:---:|:---:|:---:|
| Xem/sửa hồ sơ của mình trước hạn | ✓ | — | — | — |
| Xem minh chứng và duyệt hồ sơ SV trong lớp | — | ✓ | — | — |
| Yêu cầu bổ sung, điều chỉnh, công bố, chốt | — | ✓ | — | — |
| Đồng ý hoặc gửi khiếu nại điểm của mình | ✓ | — | — | — |
| Xem/tải bảng điểm đã chốt | — | ✓ | ✓ | — |
| Tạo đợt, cấu hình hạn và tiêu chí trước khi mở | — | — | — | ✓ |

Phân quyền kiểm ở **backend cho mọi endpoint và tệp**, không dựa vào việc ẩn nút trên UI. Một BCS/GVCN của lớp A không được xem lớp B. ADMIN chỉ quản trị cấu hình và tài khoản demo; không được âm thầm sửa điểm.

Đăng nhập local: `POST /api/v1/auth/login` với username/password; mật khẩu lưu hash; phiên lưu bằng cookie `HttpOnly`, `SameSite=Lax`. Web và API chạy cùng origin qua proxy local. Login và `GET /auth/me` trả `csrf_token` cho frontend giữ trong bộ nhớ; mọi request thay đổi dữ liệu gửi header `X-CSRF-Token`, backend kiểm token và Origin. Có `POST /auth/logout`; phiên hết hạn trả 401. Không hardcode mật khẩu demo trong mã nguồn: seed script đọc `DEMO_PASSWORD` từ môi trường.

## 4. Màn hình và hành vi chi tiết

### Quy chuẩn giao diện

- Nền sáng, chữ dễ đọc; nội dung chính rộng tối đa khoảng 1200 px. BCS dùng sidebar trái khoảng 240 px; SV dùng thanh điều hướng ngắn và giao diện một cột trên điện thoại.
- Màu trạng thái đi kèm chữ: xanh = hoàn tất, vàng = cần xử lý, đỏ = quá hạn/lỗi, xám = chưa bắt đầu. Không truyền đạt trạng thái chỉ bằng màu.
- Mỗi trang có tiêu đề, trạng thái hiện tại, hạn liên quan và **một hành động chính**. Có loading, empty, error, success rõ ràng.
- Định dạng ngày giờ `dd/MM/yyyy HH:mm`, hiển thị “giờ Việt Nam”; lưu database ở UTC. Thời gian máy chủ quyết định quyền thao tác.
- Hành động nộp, công bố, điều chỉnh, chốt có hộp xác nhận nêu hậu quả. Nút đang gửi phải khóa để tránh bấm hai lần.

### Routes và nội dung

| Route | Vai trò | Nội dung và thao tác |
|---|---|---|
| `/login` | tất cả | Username, password, lỗi xác thực rõ; đăng nhập xong chuyển theo vai trò. |
| `/student` | SV | Thẻ đợt hiện tại: tên, hạn nộp, trạng thái hồ sơ, việc tiếp theo; thông báo chưa đọc. |
| `/student/submission` | SV | Danh sách tiêu chí theo thứ tự; mỗi dòng: mô tả, điểm tối đa, ô điểm tự khai, ghi chú, tệp đã tải, nút tải tệp. Tổng tự khai tự cập nhật. Nút `Lưu nháp`; nút `Nộp hồ sơ` mở xác nhận. Sau nộp chỉ cho sửa khi ở `NEEDS_INFO`/`NEEDS_PROOF`. |
| `/student/result` | SV | Sau công bố: bảng tiêu chí gồm tự khai, điểm dự kiến, lý do BCS; tổng điểm, hạn phản hồi; nút `Đồng ý` và `Khiếu nại`. Trước công bố chỉ hiện trạng thái, không rò điểm dự kiến. |
| `/student/appeal` | SV | Chọn một hoặc nhiều tiêu chí, nhập lý do từng tiêu chí, nộp; sau nộp xem tiến độ và kết quả. Không cho sửa khi đã gửi. |
| `/bcs` | BCS | Số hồ sơ chưa nộp, chờ kiểm tra, chờ bổ sung, đã có điểm dự kiến, khiếu nại; danh sách việc gần hạn. |
| `/bcs/cases` | BCS | Bảng SV/mã hồ sơ/trạng thái/hạn/số lượt bổ sung; tìm kiếm và lọc trạng thái. Click mở chi tiết. |
| `/bcs/cases/:id` | BCS | **Ba vùng:** tệp gốc có preview/tải an toàn; điểm SV khai + tiêu chí; quyết định BCS. Mỗi tiêu chí có ô `Điểm được duyệt` và `Lý do`; lý do bắt buộc nếu khác điểm tự khai. Nút `Yêu cầu bổ sung thông tin`, `Yêu cầu bổ sung minh chứng`, `Hoàn tất kiểm tra`. Header hiển thị lịch sử và phiên bản hồ sơ. Có nhãn `Chế độ kiểm tra thủ công — AI chưa kích hoạt`. |
| `/bcs/scores` | BCS | Bảng điểm dự kiến của lớp; bộ lọc, tổng, tình trạng từng SV. Ghi nhận họp BCS/họp lớp bằng ngày giờ và ghi chú; nút `Công bố điểm dự kiến` chỉ mở khi đủ điều kiện từ backend. |
| `/bcs/appeals` | BCS | Danh sách khiếu nại; chi tiết điểm trước, lý do SV, tệp, nút `Giữ nguyên` hoặc `Điều chỉnh`; bắt buộc lý do; sau khi mọi khiếu nại xong có nút `Chốt điểm`. |
| `/admin/campaigns` | ADMIN | Tạo/sửa đợt trước khi lên lịch: lớp, học kỳ, thời hạn, trần lượt bổ sung, tiêu chí và điểm tối đa; nút `Lên lịch/mở đợt`. Nếu chưa đến `open_at`, hiển thị `Đã lên lịch`; đến giờ mới mở. Sau khi lên lịch, khóa tiêu chí và hạn cơ bản ở V1. |
| `/gvcn/final-scores` | GVCN | Chỉ đọc bảng điểm chốt, người chốt, thời điểm; nút tải CSV. Chưa chốt thì hiển thị trạng thái chờ. |

**Phác thảo trang BCS xem hồ sơ (desktop):**

```text
Hồ sơ SV001 · Chờ BCS kiểm tra · Hạn bổ sung 28/10 17:00
┌──────────────────┬─────────────────────┬────────────────────────┐
│ Minh chứng gốc   │ Tự khai & quy định  │ Quyết định của BCS     │
│ [xem PDF/ảnh]    │ TC01: 8/10          │ Điểm duyệt [ 8 ]      │
│ [danh sách tệp]  │ Mô tả tiêu chí      │ Lý do [________]      │
│                  │                     │ [Yêu cầu bổ sung]     │
└──────────────────┴─────────────────────┴────────────────────────┘
                                    [Lưu] [Hoàn tất kiểm tra]
```

Trên màn hình hẹp, ba vùng xếp dọc theo thứ tự minh chứng → tiêu chí → quyết định. Không dùng modal để xem tài liệu dài; cần mở song song với ô quyết định.

## 5. Mô hình dữ liệu (migration V1)

Dùng UUID cho khóa chính; mọi bảng có `created_at`, `updated_at` khi phù hợp. Enum lưu giá trị viết hoa; số điểm dùng `NUMERIC(5,2)`, không dùng float.

| Bảng | Cột bắt buộc và ràng buộc |
|---|---|
| `users` | `id`, `username UNIQUE`, `password_hash`, `full_name`, `role`, `is_active`. |
| `classes` | `id`, `code UNIQUE`, `name`. |
| `class_members` | `id`, `class_id`, `user_id`, `member_role` (`STUDENT/BCS/GVCN`), `UNIQUE(class_id,user_id,member_role)`. |
| `campaigns` | `id`, `class_id`, `title`, `term`, `status`, `open_at`, `submission_deadline_at`, `supplement_period_hours`, `appeal_period_hours`, `reminder_after_hours`, `max_info_rounds`, `max_proof_rounds`, `opened_at`, `published_at`, `finalized_at`, `created_by`. Ràng buộc `open_at < submission_deadline_at`, `0 < reminder_after_hours < appeal_period_hours`, các trần lượt ≥ 0. V1 demo thực hiện tự chấp nhận sau hạn như BPMN; phải xác nhận chính sách trước khi dùng thật. |
| `criteria` | `id`, `campaign_id`, `code`, `title`, `description`, `max_score`, `requires_evidence`, `sort_order`, `UNIQUE(campaign_id,code)`; bất biến sau khi đợt mở. Dữ liệu demo dùng nhãn `TC01/TC02/TC03`, không giả làm quy chế thật. |
| `cases` | `id`, `campaign_id`, `student_id`, `status`, `info_round DEFAULT 0`, `proof_round DEFAULT 0`, `claimed_total`, `proposed_total`, `final_total`, `submitted_at`, `published_at`, `appeal_deadline_at`, `acceptance_source`, `version DEFAULT 1`, `UNIQUE(campaign_id,student_id)`. Tạo một case cho mỗi SV khi mở đợt. |
| `claims` | `id`, `case_id`, `criterion_id`, `self_score NULL` khi nháp, `student_note`, `approved_score NULL`, `bcs_reason`, `reviewed_by`, `reviewed_at`, `UNIQUE(case_id,criterion_id)`. `0 ≤ score ≤ max_score` kiểm bằng service vì cần đọc `criteria`. |
| `evidence_files` | `id`, `claim_id`, `storage_key UNIQUE`, `original_name`, `mime_type`, `size_bytes`, `sha256`, `uploaded_by`, `uploaded_at`, `version_no`, `is_current`. Chỉ nhận PDF/JPG/PNG; tối đa 10 MB mỗi tệp ở demo; giới hạn cấu hình được. |
| `supplement_requests` | `id`, `case_id`, `kind` (`INFO/PROOF`), `criterion_id NULL`, `reason`, `round_no`, `requested_by NULL` (hệ thống nếu INFO), `requested_at`, `deadline_at`, `fulfilled_at`; mỗi yêu cầu có một hạn riêng. |
| `meetings` | `id`, `campaign_id`, `kind` (`BCS/CLASS`), `held_at`, `note`, `recorded_by`, `UNIQUE(campaign_id,kind)`. |
| `appeals` | `id`, `case_id`, `criterion_id`, `student_reason`, `status` (`OPEN/RESOLVED`), `resolution` (`KEEP/ADJUST`) NULL trước khi xử lý, `new_score NULL`, `bcs_reason`, `submitted_at`, `resolved_at`, `resolved_by`, `UNIQUE(case_id,criterion_id)` ở V1. |
| `score_snapshots` | `id`, `case_id`, `kind` (`PUBLISHED/FINAL`), `per_criterion_json`, `total`, `created_at`, `created_by`, `UNIQUE(case_id,kind)`. Bản đã công bố bất biến dù sau đó BCS điều chỉnh khiếu nại. |
| `notifications` | `id`, `user_id`, `case_id NULL`, `type`, `title`, `body`, `dedup_key UNIQUE`, `read_at`, `created_at`. |
| `audit_events` | `id`, `actor_user_id NULL` cho timer, `campaign_id`, `case_id NULL`, `action`, `before_json`, `after_json`, `request_id`, `created_at`; chỉ thêm, không sửa/xóa qua API. |
| `sessions` | `id`, `user_id`, `csrf_hash`, `expires_at`, `created_at`; logout xóa phiên. |

Không cần bảng `agent_runs` ở V1. Thêm bằng migration sau khi có AI. `DIn_StudentList` của BPMN = thành viên STUDENT của lớp; `DIn_ScoredList` = các case có điểm dự kiến, lấy bằng truy vấn chứ không lưu bản sao.

## 6. Trạng thái và quy tắc chuyển

### Trạng thái đợt

`DRAFT → SCHEDULED → OPEN → REVIEW → PUBLISHED → FINALIZED`. Lệnh `POST /admin/campaigns/{id}/open` chuyển DRAFT sang SCHEDULED nếu `open_at` còn ở tương lai; nếu đã đến giờ thì chuyển thẳng OPEN. Deadline tick chuyển SCHEDULED → OPEN đúng giờ và tạo một case DRAFT cho mỗi sinh viên trong lớp. `REVIEW` bắt đầu khi hết hạn nộp hoặc khi mọi SV đã nộp/đóng. `FINALIZED` không cho sửa qua UI.

### Trạng thái hồ sơ

| Từ → đến | Ai/khi nào | Điều kiện bắt buộc và tác dụng |
|---|---|---|
| `DRAFT → SUBMITTED` | SV nộp | Đợt `OPEN`, trước `submission_deadline_at`; mọi tiêu chí có `self_score` hợp lệ. Ghi `submitted_at`. |
| `SUBMITTED → NEEDS_INFO` | hệ thống | Tiêu chí `requires_evidence=true` mà thiếu tệp hoặc thiếu thông tin bắt buộc; tạo yêu cầu INFO, tăng `info_round`, gửi thông báo. Nếu đã hết lượt thì `CLOSED_INCOMPLETE`. |
| `SUBMITTED → BCS_REVIEW` | hệ thống | Hồ sơ đủ cấu trúc. **ReviewProvider V1 luôn trả về cần BCS xem.** |
| `NEEDS_INFO → BCS_REVIEW` | SV bổ sung/nộp lại | Trước hạn yêu cầu; đủ thông tin. Nếu còn thiếu và còn lượt, tạo yêu cầu mới; hết lượt/hết hạn thì `CLOSED_INCOMPLETE`. |
| `BCS_REVIEW → NEEDS_PROOF` | BCS yêu cầu | Ghi lý do/tiêu chí, `proof_round < max_proof_rounds`; tăng lượt, đặt hạn, thông báo SV. |
| `BCS_REVIEW → NEEDS_INFO` | BCS yêu cầu | Khi BCS phát hiện thông tin hồ sơ còn thiếu; ghi rõ mục cần bổ sung, kiểm `info_round < max_info_rounds`, tăng lượt và đặt hạn. |
| `NEEDS_PROOF → BCS_REVIEW` | SV bổ sung hoặc hết hạn | Tệp mới có trước hạn thì quay BCS; hết hạn cũng quay BCS để kết luận trên hồ sơ hiện có, không tự kết luận “không hợp lệ”. |
| `BCS_REVIEW → PROPOSED` | BCS hoàn tất | Mọi tiêu chí có `approved_score` hợp lệ; khác `self_score` phải có lý do. Backend tính `proposed_total = SUM(approved_score)`, ghi vết. |
| `DRAFT → CLOSED_NO_SUBMIT` | deadline tick | Qua `submission_deadline_at` mà chưa nộp; thông báo SV và BCS. |
| `PROPOSED → PUBLISHED` | BCS công bố cả lớp | Tất cả case trong đợt đã `PROPOSED/CLOSED_*`; có bản ghi họp BCS và họp lớp. Tạo `score_snapshots(kind=PUBLISHED)` bất biến; đặt `appeal_deadline_at = published_at + appeal_period_hours`. |
| `PUBLISHED → ACCEPTED` | SV đồng ý | Chưa hết hạn, chưa gửi khiếu nại; `acceptance_source=EXPLICIT`. |
| `PUBLISHED → APPEALED` | SV khiếu nại | Chưa hết hạn; tạo một hoặc nhiều appeal theo tiêu chí, không cho đồng ý cùng lúc. |
| `PUBLISHED → ACCEPTED_AUTO` | deadline tick | Quá hạn mà chưa có phản hồi; `acceptance_source=TIMEOUT`, thông báo SV. Đây là hành vi của BPMN v6 và chỉ dùng với dữ liệu demo cho đến khi chính sách được xác nhận. |
| `APPEALED → RESOLVED` | BCS | Mọi appeal của case đã có kết luận và lý do; điểm hiện hành cập nhật theo quyết định, snapshot điểm đã công bố giữ nguyên. Thông báo SV. |
| `ACCEPTED / ACCEPTED_AUTO / RESOLVED → FINALIZED` | BCS chốt cả lớp | Không còn case đang chờ; tính `final_total`, tạo `score_snapshots(kind=FINAL)`; case đóng không nộp/không hoàn tất giữ nguyên trạng thái đóng. |

`PUBLISHED` chỉ áp dụng cho case `PROPOSED`; case `CLOSED_*` không có điểm dự kiến. Mọi chuyển trạng thái đi qua một service backend duy nhất, không cho route tự gán trạng thái. Cập nhật `case.version` trong giao dịch; request với phiên bản cũ trả `409 CASE_CHANGED`.

### Deadline tick

Viết lệnh `python -m app.jobs.tick --now <ISO8601>`; nếu bỏ `--now` thì dùng thời gian hệ thống UTC. Lệnh an toàn khi chạy lặp lại: mở đợt SCHEDULED khi đến `open_at` và tạo case, xử lý quá hạn nộp, chuyển đợt `OPEN → REVIEW` khi không còn case DRAFT, quá hạn INFO/PROOF, gửi nhắc một lần khi `published_at + reminder_after_hours` mà chưa phản hồi, auto-accept khi đủ điều kiện. Dùng `notifications.dedup_key` và giao dịch để chống gửi trùng. Có thể lập lịch lệnh mỗi phút ở local; **API vẫn kiểm hạn khi nhận thao tác**, không phụ thuộc hoàn toàn vào tick.

## 7. Hợp đồng API cụ thể

Prefix `/api/v1`; JSON UTF-8, thời gian ISO 8601 UTC, UUID dạng chuỗi. Trả lỗi chung:

```json
{"error":{"code":"CASE_CHANGED","message":"Hồ sơ đã thay đổi, vui lòng tải lại.","fields":{}}}
```

Mã HTTP: `401` chưa đăng nhập, `403` sai quyền/lớp, `404` không tìm thấy hoặc không được phép biết, `409` sai trạng thái/phiên bản, `422` dữ liệu không hợp lệ. Những thao tác nộp/công bố/giải quyết/chốt nhận header `Idempotency-Key` và không thực hiện hai lần với cùng khóa.

| API | Request chính | Response/hành vi |
|---|---|---|
| `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | username/password hoặc cookie phiên | Login và me trả `{user:{id,full_name,role,class_ids},csrf_token}`; login đặt cookie. |
| `GET /student/current` | — | Đợt, cấu hình thời hạn, case, criteria, tự khai, evidence và thông báo chưa đọc của SV hiện tại. **Trước PUBLISHED, backend không trả `approved_score`, `proposed_total` hoặc lý do duyệt BCS**. |
| `PUT /student/cases/{caseId}/claims/{criterionId}` | `{self_score,student_note,expected_version}` | Lưu nháp hoặc bản bổ sung nếu trạng thái cho phép; trả case version mới. |
| `POST /student/cases/{caseId}/evidence` | multipart `criterion_id`, `file` | Kiểm quyền, MIME/kích thước, lưu tệp; trả metadata, không trả đường dẫn lưu nội bộ. |
| `GET /files/{fileId}` | cookie phiên | Stream tệp nếu là chủ hồ sơ hoặc BCS phụ trách lớp; GVCN chỉ nhận bảng điểm, không đọc minh chứng ở V1. |
| `POST /student/cases/{caseId}/submit` | `{expected_version}` | Từ DRAFT hoặc nộp lại trong NEEDS_INFO/NEEDS_PROOF; trả `{case_id,status,version,missing_items[]}`. |
| `GET /bcs/campaigns/{id}/overview` | — | Số case từng trạng thái, hạn, số khiếu nại mở. |
| `GET /bcs/campaigns/{id}/cases?status=&q=&page=` | — | Danh sách có phân trang, chỉ lớp BCS phụ trách. |
| `GET /bcs/cases/{caseId}` | — | Claims, evidence, supplement requests, điểm, lịch sử thao tác. |
| `POST /bcs/cases/{caseId}/supplement-requests` | `{kind,criterion_id?,reason,expected_version}` | Tạo yêu cầu INFO/PROOF trong số lượt cho phép, đặt hạn và thông báo. |
| `PUT /bcs/cases/{caseId}/claims/{criterionId}/review` | `{approved_score,reason,expected_version}` | Lưu điểm duyệt; `reason` bắt buộc nếu khác điểm tự khai. |
| `POST /bcs/cases/{caseId}/complete-review` | `{expected_version}` | Kiểm mọi tiêu chí, tính tổng và chuyển PROPOSED. |
| `POST /bcs/campaigns/{id}/meetings` | `{kind,held_at,note}` | Ghi hoặc cập nhật một cuộc họp BCS/CLASS, lưu audit. |
| `POST /bcs/campaigns/{id}/publish` | `{expected_campaign_status}` | Kiểm gate toàn lớp, công bố từng điểm dự kiến, tạo thông báo. |
| `GET /bcs/campaigns/{id}/scoreboard` | — | Danh sách tự khai, dự kiến, cuối và trạng thái. |
| `POST /student/cases/{caseId}/accept` | `{expected_version}` | Đồng ý trong hạn, trả trạng thái ACCEPTED. |
| `POST /student/cases/{caseId}/appeals` | `{items:[{criterion_id,reason}],expected_version}` | Tạo khiếu nại, trả trạng thái APPEALED. |
| `GET /bcs/campaigns/{id}/appeals` | — | Danh sách khiếu nại và trạng thái. |
| `POST /bcs/appeals/{appealId}/resolve` | `{resolution,new_score?,reason}` | KEEP/ADJUST; `new_score` chỉ với ADJUST và trong trần tiêu chí. Ghi điểm cũ/mới vào audit. |
| `POST /bcs/campaigns/{id}/finalize` | — | Kiểm tất cả case xong, chốt điểm, tạo snapshot CSV. |
| `GET /gvcn/campaigns/{id}/final-scores.csv` | — | Chỉ sau FINALIZED và đúng lớp. |
| `GET /notifications`, `POST /notifications/{id}/read` | — | Thông báo trong web của user hiện tại. |
| `POST /admin/campaigns`, `PUT /admin/campaigns/{id}`, `POST /admin/campaigns/{id}/open` | cấu hình và criteria | Chỉ DRAFT cho sửa cấu hình; lệnh open đặt SCHEDULED hoặc OPEN theo `open_at`, tạo case khi thật sự OPEN. |

**Mẫu request để thống nhất frontend/backend:**

`POST /admin/campaigns`:

```json
{
  "class_id":"uuid", "title":"Đợt demo học kỳ 1", "term":"HK1-DEMO",
  "open_at":"2026-10-25T01:00:00Z", "submission_deadline_at":"2026-10-30T10:00:00Z",
  "supplement_period_hours":48, "appeal_period_hours":72, "reminder_after_hours":48,
  "max_info_rounds":2, "max_proof_rounds":2,
  "criteria":[
    {"code":"TC01","title":"Tiêu chí minh họa 1","description":"Chỉ dùng cho demo","max_score":"10.00","requires_evidence":true,"sort_order":1}
  ]
}
```

`PUT /bcs/cases/{caseId}/claims/{criterionId}/review`:

```json
{"approved_score":"7.00","reason":"BCS xác nhận theo minh chứng đã nộp","expected_version":4}
```

`POST /student/cases/{caseId}/appeals`:

```json
{"items":[{"criterion_id":"uuid","reason":"Đề nghị xem lại minh chứng ở tiêu chí này"}],"expected_version":8}
```

`POST /bcs/appeals/{appealId}/resolve`:

```json
{"resolution":"ADJUST","new_score":"8.00","reason":"BCS chấp nhận minh chứng bổ sung"}
```

Các trường `expected_version` là số nguyên; nếu frontend gửi phiên bản cũ, trả 409 cùng bản hiện tại để người dùng tải lại. Điểm ở JSON dùng chuỗi thập phân để giữ chính xác.

**Ví dụ `GET /bcs/cases/{id}` rút gọn:**

```json
{
  "id":"uuid", "version":4, "status":"BCS_REVIEW",
  "student":{"id":"uuid","code":"SV001","full_name":"Sinh viên demo"},
  "deadlines":{"submission_at":"2026-10-30T10:00:00Z","supplement_at":null},
  "rounds":{"info":0,"info_max":2,"proof":0,"proof_max":2},
  "claims":[{
    "criterion":{"id":"uuid","code":"TC01","title":"Tiêu chí minh họa 1","max_score":"10.00"},
    "self_score":"8.00","approved_score":null,"bcs_reason":null,
    "evidence":[{"id":"uuid","original_name":"minh-chung.pdf","mime_type":"application/pdf"}]
  }],
  "review_mode":"MANUAL",
  "history":[{"action":"CASE_SUBMITTED","at":"2026-10-24T09:00:00Z","actor":"SV001"}]
}
```

## 8. Dữ liệu demo và quy tắc tính điểm V1

Seed một lớp `LOP-DEMO`, ba tiêu chí mang nhãn rõ `TC01/TC02/TC03` với điểm tối đa tùy chọn (ví dụ 10/10/10), 3 sinh viên, 1 BCS, 1 GVCN, 1 ADMIN, một đợt đang ở DRAFT. Đây **không phải quy chế chấm điểm rèn luyện thực tế**. Seed script idempotent; nhận mật khẩu demo từ môi trường.

- Sinh viên nhập điểm tự khai từng tiêu chí: `0 ≤ self_score ≤ max_score`.
- BCS xem minh chứng và nhập `approved_score` từng tiêu chí; nếu khác điểm tự khai thì nhập lý do.
- Backend tính `claimed_total = SUM(self_score)`, `proposed_total = SUM(approved_score)`. Khi khiếu nại được chấp thuận, cập nhật điểm tiêu chí trong bản điểm phiên bản mới, tính lại tổng; lưu bản cũ trong audit/snapshot.
- Chưa có AI/rule engine nghiệp vụ thực; **không tự kết luận minh chứng hợp lệ**. Tổng điểm chỉ là phép cộng chắc chắn.
- Đợt mở không cho sửa `criteria.max_score`, `requires_evidence`, danh sách sinh viên. Nếu cần thay, tạo đợt demo mới.

## 9. Kiểm thử chấp nhận bắt buộc

1. STUDENT chỉ thấy case của chính mình; sửa ID trên URL/API để đọc case khác nhận 404/403.
2. BCS lớp A không mở được case lớp B; GVCN không gọi API sửa điểm.
3. Form lưu nháp rồi tải lại giữ nguyên điểm và tệp; tổng tự khai đúng.
4. Nộp thiếu minh chứng bắt buộc tạo NEEDS_INFO và thông báo đúng mục; bổ sung đúng hạn quay lại BCS_REVIEW.
5. Hết lượt hoặc hết hạn bổ sung INFO đóng CLOSED_INCOMPLETE; không tạo vòng lặp tiếp.
6. BCS yêu cầu PROOF, SV nộp lại; quá hạn PROOF quay BCS để kết luận, không tự trừ điểm.
7. BCS nhập điểm vượt max hoặc khác tự khai mà không có lý do bị 422; tổng dự kiến cộng đúng.
8. Chưa đủ hai cuộc họp hoặc còn case chờ BCS thì không công bố; đủ điều kiện thì công bố một lần.
9. Trước công bố SV không thấy điểm dự kiến; sau công bố thấy đúng điểm và hạn phản hồi.
10. SV đồng ý thì không thể khiếu nại; khiếu nại thì không thể đồng ý; hai request đồng thời chỉ một thành công.
11. BCS giải quyết khiếu nại KEEP và ADJUST; điểm cũ/mới, lý do, người xử lý đều truy được.
12. Deadline tick chạy hai lần không gửi trùng thông báo và không tăng lượt hai lần; không nhắc SV đã phản hồi.
13. Quá hạn phản hồi mà SV chưa đồng ý/khiếu nại thì thành ACCEPTED_AUTO đúng một lần; SV đã phản hồi không bị tự chấp nhận.
14. Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt.
15. Tệp không thể xem bằng URL storage trực tiếp; API kiểm quyền và MIME, chặn loại tệp ngoài PDF/JPG/PNG.
16. Đợt SCHEDULED chưa tạo case/chưa cho nộp; tick ở `open_at` tạo đúng một case mỗi SV, chạy lặp lại không tạo trùng.

Chạy kiểm thử API tự động cho chuyển trạng thái, phân quyền, deadline và tính điểm; frontend kiểm thử tối thiểu các thao tác nộp, BCS duyệt, khiếu nại. Sau đó chạy thử thủ công một đợt với ba tài khoản demo.

## 10. Thứ tự code và tiêu chí hoàn thành

1. **Khởi tạo repo:** `compose.yaml`, backend FastAPI, frontend React, env example, README; trang login và health check chạy local.
2. **Migration + seed + quyền:** dữ liệu ở Mục 5, đăng nhập/phiên/CSRF, phân quyền lớp; đạt test 1–2.
3. **Luồng SV:** form, file upload, nháp, nộp, bổ sung; đạt test 3–5 và 15.
4. **Luồng BCS:** hàng chờ, xem tệp, yêu cầu bổ sung, duyệt điểm, hoàn tất kiểm tra; đạt test 6–7.
5. **Công bố/phản hồi:** họp, bảng điểm, công bố, đồng ý/khiếu nại; đạt test 8–10.
6. **Kết thúc:** giải quyết khiếu nại, deadline tick, chốt, GVCN CSV, audit; đạt test 11–14 và 16.
7. **Rà UI:** desktop BCS và mobile SV; đầy đủ loading/empty/error/success, xác nhận thao tác và điều hướng bàn phím.

**Định nghĩa “vỏ V1 xong”:** chạy từ `README.md` trên máy mới; migration/seed thành công; ba tài khoản SV/BCS/GVCN hoàn thành một đợt demo từ đầu đến cuối; 16 kiểm thử chấp nhận trên đạt; không có lệnh gọi AI hoặc kết quả AI giả. Không cần triển khai lên Internet ở V1.

## 11. Điểm mở rộng cho bốn agent ở phiên bản sau

Định nghĩa interface `ReviewProvider.review(case_id) -> ReviewResult` trong `api/app/review/`. V1 dùng `ManualReviewProvider` trả `mode=MANUAL`, `needs_human_review=true`, **không tạo findings**. Sau này thêm `AIReviewProvider` mà không đổi API giao diện SV/BCS.

- **Agent điều phối:** thay/bao quanh workflow service hiện tại; vẫn tuân trạng thái, timer, số lượt và quyền đã định nghĩa.
- **Agent đọc dữ liệu:** đọc tệp từ API nội bộ, trả dữ liệu trích xuất và vị trí nguồn; lưu `agent_runs`/`extractions` bằng migration mới.
- **Agent minh bạch:** đọc quy chế đúng phiên bản, trả findings có điều khoản và minh chứng; thêm trạng thái `valid/issue/uncertain`; `uncertain` đi BCS.
- **Agent ra quyết định:** thay chỗ BCS nhập điểm bằng **đề xuất điểm theo luật được phiên bản hóa**, nhưng BCS vẫn có màn duyệt; không thay các giao dịch chốt điểm.

Không tạo bốn tiến trình AI riêng hoặc màn hình chat ở V1. Khi làm phần AI, giữ nguyên luồng người dùng và thay nguồn dữ liệu ở các điểm mở rộng này.
