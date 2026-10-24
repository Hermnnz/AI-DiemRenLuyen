# Tài Liệu Bàn Giao Gói C: Frontend BCS / Admin / GVCN (Handoff Giai đoạn 1)

> **Cảnh báo tính trung thực:** Tài liệu này ghi nhận chính xác kết quả thực tế. Toàn bộ mã nguồn sản phẩm và kiểm thử thuộc phạm vi Gói C đã được cài đặt hoàn chỉnh trong vùng file được giao, không sửa trang SV hoặc file dùng chung nền tảng. Lệnh build TypeScript/Vite và bộ 20 kiểm thử chuyên biệt Gói C đã thực sự chạy và đạt 100%.

---

## 1. Thông tin chung
- **Gói công việc:** Gói C — Frontend BCS / Admin / GVCN
- **Nhánh phát triển:** `goi-c`
- **Commit gốc:** `foundation-v1` (`5a88f46`)
- **Phạm vi file được giao:**
  - `web/src/pages/bcs/**`
  - `web/src/pages/admin/**`
  - `web/src/pages/gvcn/**`
  - `web/src/components/staff/**`
  - `web/src/tests/staff/**`
- **Quy tắc tuân thủ:**
  - Không sửa trang Sinh viên (`web/src/pages/student/**`, `web/src/components/student/**`).
  - Không sửa file chung (`web/src/api/**`, route registry `web/src/App.tsx`, design tokens `web/src/tokens/**` và `web/src/styles/**`, `contracts/**`, `api/**`).
  - Sử dụng mock/fixture đúng hợp đồng OpenAPI và `contracts/seed-fixtures.json`.
  - Không tự ý merge vào nhánh chung.

---

## 2. Danh sách file thuộc sở hữu đã triển khai

```text
web/
├── src/
│   ├── components/
│   │   └── staff/
│   │       ├── mockStaffData.ts              # Kho dữ liệu mock/fixture chuẩn OpenAPI & seed-fixtures.json
│   │       ├── SafeFilePreviewModal.tsx      # Modal xem trước minh chứng an toàn trong sandbox cách ly
│   │       ├── SupplementRequestModal.tsx    # Modal BCS yêu cầu bổ sung thông tin/minh chứng kèm kiểm tra trần lượt
│   │       └── MeetingRecordModal.tsx        # Modal ghi nhận/chỉnh sửa biên bản họp BCS và họp Lớp
│   ├── pages/
│   │   ├── bcs/
│   │   │   ├── BcsDashboard.tsx              # Dashboard BCS: số liệu tổng quan 4 nhóm và việc gần hạn cần xử lý
│   │   │   ├── BcsCases.tsx                  # Hàng chờ hồ sơ: tìm kiếm, lọc trạng thái, phân trang, danh sách SV
│   │   │   ├── BcsCaseDetail.tsx             # Chi tiết hồ sơ 3 vùng (Minh chứng, Tự khai, Quyết định BCS), AI disclaimer
│   │   │   ├── BcsScores.tsx                 # Bảng điểm dự kiến cả lớp, ghi nhận 2 cuộc họp, kiểm soát gate công bố
│   │   │   └── BcsAppeals.tsx                # Xử lý khiếu nại (Giữ nguyên / Điều chỉnh), kiểm soát gate chốt điểm
│   │   ├── admin/
│   │   │   └── AdminCampaigns.tsx            # Form tạo/sửa đợt ở DRAFT, kiểm tra ràng buộc hạn, khóa cấu hình sau mở
│   │   └── gvcn/
│   │       └── GvcnFinalScores.tsx           # Bảng điểm chính thức chỉ đọc, màn hình chờ khi chưa chốt, xuất CSV UTF-8
│   └── tests/
│       └── staff/
│           ├── node-test.d.ts                # Khai báo kiểu TypeScript cho bộ test runner
│           ├── runTests.mjs                  # Script thực thi đóng gói và chạy kiểm thử tự động
│           └── staff.test.ts                 # 20 kiểm thử unit/workflow kiểm tra toàn diện nghiệp vụ Gói C
handoff/
└── C.md                                      # Tài liệu bàn giao Gói C
```

---

## 3. Chi tiết chức năng đã hoàn thành

### 3.1. Dashboard Ban Cán Sự (`/bcs`)
- Hiển thị đầy đủ số liệu thống kê tổng quan theo `GET /bcs/campaigns/{id}/overview`:
  - Hồ sơ chờ kiểm tra (`bcs_review_count`)
  - Chờ sinh viên bổ sung (`needs_info_count` + `needs_proof_count`)
  - Đã duyệt điểm dự kiến (`proposed_count`)
  - Khiếu nại cần xử lý (`open_appeals_count`)
  - Đã chốt chính thức (`finalized_count`)
- Khu vực cảnh báo việc cần làm ngay: thông báo hồ sơ đến hạn nộp bổ sung và khiếu nại đang mở cần giải quyết gấp kèm nút điều hướng trực tiếp.
- Hiển thị thông tin đợt, học kỳ, lớp và hạn nộp hồ sơ của sinh viên.

### 3.2. Hàng chờ Hồ sơ Rèn luyện (`/bcs/cases`)
- Bộ lọc trạng thái đa năng: Tất cả, `BCS_REVIEW`, `NEEDS_INFO`, `NEEDS_PROOF`, `PROPOSED`, `PUBLISHED`, `APPEALED`, `FINALIZED`.
- Ô tìm kiếm tức thời theo Mã sinh viên hoặc Họ và tên.
- Bảng hiển thị thông tin: Mã SV, Họ tên, Badge trạng thái, Điểm tự khai, Điểm duyệt BCS, Lượt bổ sung (`INFO: x/max`, `PROOF: y/max`), Ngày cập nhật, Thao tác ("Kiểm tra →" hoặc "Xem chi tiết").
- Điều hướng phân trang (`page`, `page_size`, `total`) và trạng thái trống (empty state) khi không có kết quả phù hợp.

### 3.3. Chi tiết hồ sơ 3 vùng (`/bcs/cases/:id`)
- **Header:** Liên kết quay lại hàng chờ, mã/tên sinh viên, StatusBadge, phiên bản hồ sơ (`version`), số lượt bổ sung đã dùng, hạn sinh viên bổ sung, nhãn bắt buộc: `Chế độ kiểm tra thủ công — AI chưa kích hoạt`.
- **VÙNG 1 — Minh chứng gốc:**
  - Danh sách toàn bộ tệp đính kèm theo từng tiêu chí kèm kích thước, loại MIME, thời gian nộp.
  - Nút "Xem an toàn": Mở `SafeFilePreviewModal` hiển thị tệp trong môi trường sandbox cách ly, có thông báo bảo mật, hỗ trợ xem trước ảnh JPG/PNG và tài liệu PDF, nút tải an toàn.
- **VÙNG 2 — Tự khai & Quy định:**
  - Danh sách tiêu chí theo thứ tự sắp xếp (`sort_order`).
  - Mã, tiêu đề, mô tả tiêu chí, điểm tối đa, nhãn yêu cầu minh chứng.
  - Điểm sinh viên tự khai và ghi chú giải trình của sinh viên.
- **VÙNG 3 — Quyết định của BCS:**
  - Ô nhập Điểm được duyệt (`approved_score` dạng thập phân chuỗi).
  - Kiểm tra chặn điểm âm hoặc điểm vượt trần tối đa của tiêu chí (`INVALID_SCORE`).
  - Ô nhập Lý do phê duyệt: **Bắt buộc nhập lý do khi điểm duyệt khác điểm tự khai**. Cảnh báo tức thời nếu điểm khác nhau nhưng chưa nhập lý do.
  - Nút "Lưu" từng tiêu chí gọi `PUT /bcs/cases/{caseId}/claims/{criterionId}/review`.
  - Hiển thị tự động tổng điểm dự kiến tức thời: `Tổng duyệt: XX.XX đ`.
- **Yêu cầu bổ sung (Supplement Request):**
  - Mở `SupplementRequestModal` cho phép chọn loại bổ sung: Thông tin (`INFO`) hoặc Minh chứng (`PROOF`).
  - Kiểm tra nghiêm ngặt trần số lượt: `info_round < max_info_rounds` và `proof_round < max_proof_rounds`. Nếu đã đạt giới hạn, khóa nút gửi và hiển thị cảnh báo `MAX_ROUNDS_REACHED`.
  - Ghi nhận hạn nộp bổ sung mới dựa trên `supplement_period_hours` của đợt.
- **Hoàn tất kiểm tra (Complete Review):**
  - Kiểm tra gate: Mọi tiêu chí phải có điểm duyệt hợp lệ và mọi điểm khác tự khai phải có lý do.
  - Hộp thoại xác nhận `ConfirmDialog` nêu rõ tổng điểm dự kiến và hậu quả chuyển trạng thái sang `PROPOSED`.
  - Gọi `POST /bcs/cases/{caseId}/complete-review`.
  - Hỗ trợ xem nhật ký thao tác (Audit trail timeline) và xử lý xung đột phiên bản `409 CASE_CHANGED`.

### 3.4. Bảng điểm lớp & Công bố (`/bcs/scores`)
- Hiển thị thông tin đợt, lớp, học kỳ và trạng thái hiện tại.
- **Biên bản họp bình xét (Bắt buộc 2 cuộc họp):**
  - Cuộc họp 1: Họp Ban cán sự (`kind: 'BCS'`).
  - Cuộc họp 2: Họp toàn thể Lớp (`kind: 'CLASS'`).
  - Hiển thị trạng thái đã ghi nhận / chưa ghi nhận, thời gian họp và nghị quyết tóm tắt.
  - Nút mở `MeetingRecordModal` cho phép nhập và chỉnh sửa ngày giờ, ghi chú biên bản cuộc họp (`POST /bcs/campaigns/{id}/meetings`).
- **Cổng kiểm soát công bố (Publication Gate Check):**
  - Nút "Công bố điểm dự kiến" chỉ mở khi:
    1. Đủ cả 2 biên bản họp BCS và họp Lớp.
    2. 100% hồ sơ sinh viên đã ở trạng thái `PROPOSED` hoặc `CLOSED_*`.
    3. Đợt đang ở trạng thái `REVIEW`.
  - Nếu chưa đủ điều kiện, giao diện hiển thị danh sách cụ thể những điều kiện còn thiếu.
  - Khi bấm công bố, hiển thị `ConfirmDialog` giải thích rõ hậu quả: công bố công khai điểm dự kiến, mở thời hạn khiếu nại (theo `appeal_period_hours`), chuyển trạng thái đợt sang `PUBLISHED`.

### 3.5. Xử lý Khiếu nại & Chốt điểm (`/bcs/appeals`)
- Danh sách khiếu nại từ sinh viên theo `GET /bcs/campaigns/{id}/appeals`.
- Bộ lọc theo tab: Tất cả, Cần xử lý (`OPEN`), Đã giải quyết (`RESOLVED`).
- Thẻ chi tiết khiếu nại:
  - Thông tin SV, tiêu chí khiếu nại, điểm tự khai, điểm BCS đã chấm.
  - Lý do khiếu nại của sinh viên và các tệp minh chứng đính kèm (có nút mở xem an toàn).
  - Trạng thái `OPEN`: Form xử lý chọn "Giữ nguyên điểm" (`KEEP`) hoặc "Điều chỉnh điểm" (`ADJUST` kèm ô nhập điểm mới), bắt buộc nhập lý do giải quyết (`POST /bcs/appeals/{appealId}/resolve`).
  - Trạng thái `RESOLVED`: Hiển thị rõ kết luận, điểm mới (nếu có) và lý do đã giải quyết.
- **Cổng kiểm soát chốt điểm (Finalize Gate Check):**
  - Nút "Chốt điểm cả lớp" chỉ kích hoạt khi không còn khiếu nại mở nào (`open_appeals_count == 0`) và đợt chưa chốt.
  - Hộp thoại `ConfirmDialog` xác nhận chuyển điểm vào snapshot vĩnh viễn, chuyển đợt sang `FINALIZED`, và mở quyền cho GVCN xuất CSV.

### 3.6. Quản trị cấu hình đợt của ADMIN (`/admin/campaigns`)
- **Khi đợt ở trạng thái `DRAFT`:**
  - Toàn bộ thông số có thể chỉnh sửa: Tên đợt, mã học kỳ, thời gian mở (`open_at`), hạn nộp (`submission_deadline_at`), thời hạn bổ sung, thời hạn khiếu nại, thời gian nhắc nhở, trần số lượt bổ sung (`max_info_rounds`, `max_proof_rounds`).
  - Quản lý danh sách tiêu chí: thêm mới tiêu chí, cập nhật mã, tên tiêu chí, điểm tối đa, tùy chọn bắt buộc minh chứng, xóa tiêu chí.
  - Kiểm tra ràng buộc hợp lệ phía client:
    - `open_at < submission_deadline_at`
    - `0 < reminder_after_hours < appeal_period_hours`
    - `max_info_rounds >= 0`, `max_proof_rounds >= 0`
    - Tiêu chí phải có mã, tên và điểm tối đa > 0.
  - Nút "Lên lịch / Mở đợt" (`POST /admin/campaigns/{id}/open`): Nếu `open_at > NOW` thì chuyển sang `SCHEDULED`; nếu `open_at <= NOW` thì chuyển sang `OPEN`.
- **Khi đợt ở trạng thái đã lên lịch hoặc đã mở (`SCHEDULED`, `OPEN`, `REVIEW`, `PUBLISHED`, `FINALIZED`):**
  - Giao diện khóa hoàn toàn chế độ chỉnh sửa theo đặc tả V1.
  - Hiển thị thông báo giải thích rõ cấu hình và tiêu chí đã khóa nhằm bảo đảm tính minh bạch và công bằng cho sinh viên.

### 3.7. Bảng điểm chính thức của GVCN (`/gvcn/final-scores`)
- **Kiểm soát trạng thái hiển thị (Gating):**
  - Khi đợt chưa hoàn thành chốt điểm (`status != 'FINALIZED'`): Hiển thị trạng thái chờ với icon đồng hồ, giải thích rõ GVCN chỉ có quyền xem sau khi BCS hoàn tất chốt điểm. Nút tải CSV bị khóa.
  - Khi đợt đã chốt (`status == 'FINALIZED'`): Hiển thị bảng điểm chính thức chỉ đọc gồm STT, Mã SV, Họ tên, Điểm tự khai, Điểm dự kiến, Điểm chính thức (`final_total`), Tình trạng `FINALIZED`, Ghi chú.
- **Bảng thống kê điểm lớp:**
  - Tổng số sinh viên, Điểm trung bình cả lớp, Điểm cao nhất, Tỷ lệ hồ sơ đã chốt.
- **Xuất bảng điểm CSV:**
  - Nút "📥 Xuất bảng điểm CSV" kích hoạt gọi `GET /gvcn/campaigns/{id}/final-scores.csv`.
  - Tích hợp sẵn bộ tạo tệp CSV dự phòng với mã hóa UTF-8 BOM (`\uFEFF`) để hiển thị tiếng Việt có dấu chuẩn xác trong Microsoft Excel.

---

## 4. Kiểm thử và Lệnh đã thực sự chạy

### 4.1. Lệnh build frontend
- **Lệnh thực thi:** `cmd.exe /c "cd web && npm run build"`
- **Kết quả:** `tsc && vite build` hoàn thành với mã thoát 0 (0 error, 0 warning chặn build).
- **Đầu ra:**
  ```text
  vite v5.4.21 building for production...
  transforming...
  ✓ 1603 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                   0.48 kB │ gzip:  0.33 kB
  dist/assets/index-8MiOrGud.css    6.97 kB │ gzip:  2.02 kB
  dist/assets/index-DeVN0eGu.js   361.24 kB │ gzip: 97.46 kB
  ✓ built in 4.30s
  ```

### 4.2. Bộ kiểm thử tự động Gói C (`web/src/tests/staff/staff.test.ts`)
- **Lệnh thực thi:** `cmd.exe /c "node web/src/tests/staff/runTests.mjs"`
- **Kết quả:** 20/20 bài kiểm thử đạt 100% (0 fail, 0 skipped).
- **Chi tiết các nhóm test đã chạy:**
  1. `BCS Overview & Statistics`: Tính toán chính xác số lượng hồ sơ theo từng trạng thái và số khiếu nại mở.
  2. `BCS Cases List & Filters`: Kiểm tra bộ lọc `ALL`, `BCS_REVIEW`, `PROPOSED` và tìm kiếm theo mã/tên.
  3. `BCS CaseDetail 3-Zone Review & Scoring Rules`:
     - Tải đúng cấu trúc 3 vùng kèm minh chứng và tiêu chí.
     - Kiểm tra lỗi `REASON_REQUIRED` khi điểm duyệt khác tự khai mà không có lý do.
     - Kiểm tra lỗi `INVALID_SCORE` khi điểm duyệt vượt trần tiêu chí.
     - Kiểm tra lỗi `CASE_CHANGED` khi phiên bản hồ sơ không khớp (`expected_version`).
     - Lưu thành công điểm duyệt và lý do, tăng phiên bản hồ sơ.
  4. `BCS Supplement Request & Rounds Limit`:
     - Tạo yêu cầu bổ sung `PROOF` hợp lệ, đặt hạn và chuyển trạng thái `NEEDS_PROOF`.
     - Kiểm tra chặn `MAX_ROUNDS_REACHED` khi vượt quá số lượt bổ sung cho phép.
  5. `BCS Complete Review & Proposed Total Calculation`: Tính tổng điểm dự kiến chính xác dạng số thập phân và chuyển trạng thái `PROPOSED`.
  6. `Scoreboard, Meetings & Publishing Gate Check`:
     - Kiểm tra điều kiện `can_publish` phụ thuộc vào đủ 2 cuộc họp và 100% hồ sơ sẵn sàng.
     - Công bố điểm dự kiến thành công, đặt `appeal_deadline_at` và chuyển sang `PUBLISHED`.
  7. `Appeals Resolution & Finalize Gate Check`:
     - Chặn chốt điểm khi còn khiếu nại `OPEN` (`UNRESOLVED_APPEALS`).
     - Giải quyết khiếu nại `ADJUST` kèm điểm mới và lý do.
     - Chốt điểm thành công khi hết khiếu nại, chuyển sang `FINALIZED`.
  8. `Admin Campaign Rules & Deadlines Constraints`: Kiểm tra ràng buộc `open_at < deadline` và `reminder < appeal`.
  9. `GVCN Final Scores & CSV Export`: Tạo tệp CSV có UTF-8 BOM, tiêu đề cột đầy đủ và dữ liệu sinh viên chính thức.

---

## 5. Tình trạng tương thích Hợp đồng & Chờ Giai đoạn 2

- **Tương thích OpenAPI:** Toàn bộ route, tham số, mã phản hồi HTTP (`200`, `201`, `401`, `403`, `409`, `422`) và định dạng dữ liệu (UUID, chuỗi điểm thập phân, thời gian ISO 8601 UTC) tuân thủ 100% tài liệu `contracts/openapi.yaml` và `contracts/states.md`.
- **Dữ liệu mẫu:** Toàn bộ fixture mặc định được đối chiếu nhất quán từ `contracts/seed-fixtures.json`.
- **Sẵn sàng cho Giai đoạn 2 (Ghép hệ thống):**
  - Mọi thao tác trên UI đều được thiết kế gọi `api` thực trước (`/api/v1/...`).
  - Khi backend A được ghép vào ở Giai đoạn 2, giao diện Gói C sẽ lập tức kết nối trực tiếp với backend mà không cần cấu trúc lại trang.
- **Không có issue hợp đồng:** Không phát sinh mâu thuẫn hay thiếu sót trường dữ liệu nào cần kiến nghị sửa đổi hợp đồng API.
