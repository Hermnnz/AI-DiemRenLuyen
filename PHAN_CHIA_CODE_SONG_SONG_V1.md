# Chia việc để code song song — vỏ web V1

**Tài liệu gốc bắt buộc đọc:** [DAC_TA_CODE_WEB_VO_V1.md](DAC_TA_CODE_WEB_VO_V1.md).  
**Phạm vi:** frontend + backend cơ bản chạy được toàn luồng demo. Không xây OCR, LLM, RAG hoặc bốn agent thực ở đợt này.

## 1. Sơ đồ phụ thuộc

```text
Giai đoạn 0: một AI dựng nền và khóa hợp đồng API/dữ liệu
                         │
           ┌─────────────┼─────────────┬─────────────┐
           ▼             ▼             ▼             ▼
      A. Backend     B. UI sinh viên  C. UI BCS/    D. Kiểm thử
      nghiệp vụ      + mock API        Admin/GVCN    độc lập
                                      + mock API
           └─────────────┬─────────────┴─────────────┘
                         ▼
Giai đoạn 2: một lượt ghép, sửa sai khác hợp đồng, chạy thử đầu-cuối
                         ▼
Giai đoạn 3: hoàn thiện UI, kiểm thử chấp nhận, bàn giao vỏ V1
```

**Chỉ Giai đoạn 1 gồm A–D chạy song song.** Giai đoạn 0 phải hoàn thành trước để bốn gói dùng chung tên route, kiểu dữ liệu, trạng thái và dữ liệu demo. Giai đoạn 2 phải chờ cả bốn gói. Giai đoạn lắp AI thật là một kế hoạch khác, sau khi vỏ V1 đạt kiểm thử.

## 2. Quy tắc để tránh các AI sửa đè nhau

1. Mỗi gói làm trên **một nhánh/worktree riêng** từ cùng commit kết thúc Giai đoạn 0. Không dùng chung một checkout đang sửa.
2. Giai đoạn 0 tạo và khóa `contracts/openapi.yaml`, `contracts/states.md`, `contracts/seed-fixtures.json`, `web/src/api/types.ts`, `web/src/api/client.ts`, route registry và design tokens. A–D được đọc nhưng **không tự sửa** các file này.
3. Nếu thấy hợp đồng thiếu/sai, ghi vào `handoff/<goi>-contract-issues.md` theo mẫu: route/field hiện tại → vấn đề → thay đổi đề nghị → ảnh hưởng. Người ghép ở Giai đoạn 2 quyết định và sửa hợp đồng **một lần**.
4. Không sửa file ngoài vùng sở hữu ở bảng bên dưới. Không thêm thư viện nếu chưa cần cho gói; nếu thêm, nêu lý do trong handoff.
5. Mọi response mock ở frontend phải lấy từ `contracts/seed-fixtures.json` hoặc đúng schema OpenAPI. Không tự đặt status/field mới.
6. Không viết phần AI thật và không tạo dữ liệu “AI đã duyệt” giả. Các hồ sơ đủ cấu trúc đi `BCS_REVIEW` thủ công.

## 3. Giai đoạn 0 — nền chung, làm tuần tự

**Một người/AI duy nhất sở hữu toàn repo ở bước này.** Đầu vào: đặc tả V1. Đầu ra là một commit `foundation-v1` mà cả bốn gói có thể bắt đầu.

### Việc phải làm

- Tạo cấu trúc repo `web/`, `api/`, `contracts/`, `handoff/`, `storage/`, `compose.yaml`, `.env.example`, `README.md`.
- Tạo PostgreSQL local, FastAPI health check, React/Vite shell, trang login trống và layout cho 4 vai trò.
- Tạo **OpenAPI 3.x đầy đủ** cho toàn bộ endpoint ở Mục 7 đặc tả V1: request/response/error, enum trạng thái, mã HTTP. Chốt cách trả điểm dạng chuỗi thập phân, thời gian UTC, UUID.
- Tạo `contracts/states.md`: mọi trạng thái đợt/hồ sơ, bảng chuyển, actor, điều kiện và tác dụng phụ; khớp Mục 6 đặc tả.
- Tạo `contracts/seed-fixtures.json`: dữ liệu seed cho 1 lớp, 1 đợt, 3 tiêu chí demo, 3 SV, 1 BCS, 1 GVCN, 1 ADMIN; thêm các **response mẫu độc lập** cho những trạng thái cần hiển thị trên UI. Response mẫu không nhất thiết cùng tồn tại trong một đợt thật. Không coi fixture là dữ liệu thật.
- Tạo migration đầu tiên cho bảng ở Mục 5 và seed script. Chỉ tạo schema/seed; chưa viết nghiệp vụ.
- Tạo `web/src/api/types.ts` từ hợp đồng, `web/src/api/client.ts` (base URL, cookie/CSRF, lỗi chung), route registry với placeholder cho các trang.
- Tạo design tokens chung (màu, spacing, typography, trạng thái), component nền `AppLayout`, `StatusBadge`, `Deadline`, `ConfirmDialog`.

### Điều kiện xong

- Backend và frontend khởi động local; health check trả OK; trang login placeholder hiện được.
- Migration và seed chạy lại không tạo bản ghi trùng.
- OpenAPI/schema/TypeScript types nhất quán; tất cả route trong đặc tả đã có trong hợp đồng.
- Commit/tag nền chung và gửi mã commit cho bốn gói. Không bắt đầu A–D trước mốc này.

## 4. Giai đoạn 1 — bốn gói chạy song song

| Gói | Sở hữu file | Phải hoàn thành | Không được sửa |
|---|---|---|---|
| **A — Backend nghiệp vụ** | `api/app/routes/**`, `api/app/services/**`, `api/app/review/**`, `api/app/jobs/**`, `api/tests/**`; migration bổ sung nếu thật cần | Auth/CSRF/RBAC; API SV, BCS, ADMIN, GVCN; upload an toàn; state machine; tính điểm; deadline tick; thông báo; audit; API tests. `ManualReviewProvider` chỉ đẩy BCS. | `web/**`, `contracts/**`, migration nền cũ. |
| **B — Frontend sinh viên** | `web/src/pages/student/**`, `web/src/components/student/**`, `web/src/tests/student/**` | Dashboard, form tự chấm, tải tệp, nháp/nộp/bổ sung, kết quả, đồng ý, khiếu nại; loading/error/empty/confirm; responsive mobile. Gọi `api/client.ts`; chạy với mock đúng hợp đồng. | Trang BCS/Admin/GVCN, `web/src/api/**`, route registry, design tokens, `api/**`. |
| **C — Frontend BCS/Admin/GVCN** | `web/src/pages/bcs/**`, `web/src/pages/admin/**`, `web/src/pages/gvcn/**`, `web/src/components/staff/**`, `web/src/tests/staff/**` | Dashboard BCS, hàng chờ, chi tiết 3 vùng, bổ sung/duyệt điểm, bảng lớp/họp/công bố, khiếu nại/chốt; form ADMIN; bảng cuối GVCN. Dùng mock đúng hợp đồng, responsive tối thiểu. | Trang SV, `web/src/api/**`, route registry, design tokens, `api/**`. |
| **D — Kiểm thử chấp nhận** | `tests/e2e/**`, `tests/contract/**`, `tests/fixtures/**`, `handoff/D-*.md` | Viết test đen hộp cho 16 tiêu chí Mục 9; kiểm OpenAPI và fixtures; script khởi tạo/chạy kiểm thử. Có thể test với mock trước, đánh dấu test chờ backend. | Mã sản phẩm `api/**`, `web/src/**`, `contracts/**`. |

### Đầu ra từng gói

Mỗi gói tạo `handoff/<goi>.md` gồm: commit/nhánh, file đã sửa, chức năng xong, lệnh kiểm thử đã **thực sự chạy**, kết quả, chỗ còn chờ hợp đồng hoặc backend. Không ghi “pass” cho test chưa chạy. Mỗi gói giao code có thể review; không tự merge vào nhánh chung.

### Điều kiện xong riêng

- **A:** API đúng OpenAPI; test quyền, trạng thái, điểm, deadline, idempotency và file upload đạt. Không có lệnh gọi AI.
- **B:** toàn bộ route SV render được bằng fixture; không tự dùng dữ liệu trường khác; nút khóa theo status/deadline; build frontend đạt.
- **C:** toàn bộ route BCS/Admin/GVCN render bằng fixture; BCS thấy nguồn và lý do, GVCN chỉ xem bảng chốt; build frontend đạt.
- **D:** 16 test được viết, chạy được phần hợp đồng/fixture; các test đợi integration được ghi rõ, không khai đã đạt sớm.

## 5. Giai đoạn 2 — ghép và chạy đầu-cuối

**Một người/AI duy nhất ghép theo thứ tự:** nền → A → B → C → D. Sau mỗi gói, xử lý conflict ở file thuộc phạm vi gói; nếu phải sửa `contracts/**` thì cập nhật OpenAPI, TypeScript types, backend và mock cùng một commit.

1. Chạy migration/seed trên database mới, khởi động API/web.
2. Chuyển B và C từ mock sang backend thật bằng `api/client.ts`; chỉ cập nhật adapter chung ở bước ghép.
3. Chạy một đợt demo theo thứ tự: ADMIN lên lịch/mở → SV nộp → BCS duyệt → họp/công bố → SV đồng ý và khiếu nại → BCS xử lý/chốt → GVCN tải CSV.
4. Chạy deadline tick với thời gian giả lập cho mở đợt, nộp muộn, bổ sung, nhắc hạn và tự chấp nhận. Kiểm tra chạy lặp không nhân đôi dữ liệu.
5. Chạy bộ 16 test của D; sửa lỗi có bằng chứng, không đổi phạm vi nghiệp vụ để làm test xanh.

**Điều kiện xong:** không còn sai khác request/response giữa frontend và backend; toàn luồng demo chạy được; tất cả lỗi 401/403/409/422 được UI hiển thị rõ; 16 kiểm thử chấp nhận đạt hoặc có danh sách lỗi cụ thể chưa giải quyết.

## 6. Giai đoạn 3 — hoàn thiện và bàn giao

- Rà giao diện SV ở 360–430 px và BCS ở desktop; kiểm bàn phím, nhãn trường, loading/empty/error, thông báo quá hạn.
- Xác minh frontend không lộ điểm BCS trước PUBLISHED và không lộ tệp SV khác.
- README ghi lệnh chạy, migration, seed, demo accounts qua `DEMO_PASSWORD`, lệnh deadline tick, lệnh test, giới hạn dữ liệu minh họa.
- Chụp ảnh màn hình các luồng chính nếu cần thuyết trình; không thêm AI vào V1.
- Bàn giao một nhánh tích hợp cùng file `.env.example`; không đưa mật khẩu/tệp sinh viên thật vào repo.

## 7. Prompt giao việc có thể sao chép

**Prompt Giai đoạn 0:**

> Đọc `output/DAC_TA_CODE_WEB_VO_V1.md` và `output/PHAN_CHIA_CODE_SONG_SONG_V1.md`. Chỉ làm Giai đoạn 0 của tài liệu chia việc. Tạo repo nền, hợp đồng OpenAPI/states/fixtures, migration/seed, frontend/backend shell. Không triển khai nghiệp vụ hoặc AI. Chạy kiểm tra khởi động và ghi commit nền cùng lệnh đã chạy.

**Prompt gói A:**

> Bắt đầu từ commit `foundation-v1`. Đọc hai tài liệu trong `output/` và các file `contracts/`. Chỉ làm gói A Backend nghiệp vụ. Tuân OpenAPI và state machine đã khóa; không sửa `web/**` hoặc `contracts/**`. V1 dùng `ManualReviewProvider`, không gọi AI. Viết/chạy test liên quan. Ghi `handoff/A.md` với kết quả thực tế; không merge.

**Prompt gói B:**

> Bắt đầu từ commit `foundation-v1`. Đọc đặc tả V1, tài liệu chia việc, `contracts/` và `web/src/api/`. Chỉ làm gói B Frontend sinh viên trong vùng file được giao. Dùng fixture/mock đúng OpenAPI, không sửa API client/types/router/design tokens. Kiểm mobile, trạng thái, lỗi, xác nhận nộp. Chạy build/test, ghi `handoff/B.md`; không merge.

**Prompt gói C:**

> Bắt đầu từ commit `foundation-v1`. Đọc đặc tả V1, tài liệu chia việc, `contracts/` và `web/src/api/`. Chỉ làm gói C Frontend BCS/Admin/GVCN trong vùng file được giao. Dùng fixture/mock đúng OpenAPI; không sửa trang SV hoặc file chung. Chạy build/test, ghi `handoff/C.md`; không merge.

**Prompt gói D:**

> Bắt đầu từ commit `foundation-v1`. Đọc đặc tả V1, tài liệu chia việc và `contracts/`. Chỉ làm gói D kiểm thử trong `tests/**` và handoff của gói. Viết 16 kiểm thử chấp nhận theo Mục 9, đánh dấu test chưa thể chạy tới khi backend/UI ghép xong. Chạy những test hiện chạy được, ghi `handoff/D.md`; không merge.

**Prompt ghép Giai đoạn 2:**

> Đọc đặc tả V1, tài liệu chia việc và bốn file `handoff/A.md`–`D.md`. Ghép bốn nhánh theo thứ tự A, B, C, D vào commit nền. Chỉ sửa hợp đồng khi có lý do cụ thể và cập nhật đồng thời backend, frontend, fixture. Chạy migration/seed, demo đầu-cuối, deadline tick và 16 test. Báo kết quả thật và lỗi còn lại; không thêm AI.
