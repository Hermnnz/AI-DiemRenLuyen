# Tài Liệu Bàn Giao Gói D: Kiểm Thử Chấp Nhận & Kiểm Thử Hợp Đồng (Handoff Giai đoạn 1)

> **Cảnh báo tính trung thực:** Tài liệu này phản ánh chính xác kết quả thực tế. 16 kiểm thử chấp nhận Mục 9 đã được lập trình đầy đủ nhưng được đánh dấu **SKIPPED (chờ ghép Giai đoạn 2)** do backend ở mốc `foundation-v1` mới chỉ là các endpoint shell. Toàn bộ 46 kiểm thử hợp đồng đã chạy và đạt 100%.

---

## 1. Thông tin chung
- **Gói công việc:** Gói D — Kiểm thử chấp nhận độc lập
- **Nhánh phát triển:** `goi-d`
- **Commit kết quả:** `570f394`
- **Commit gốc:** `5a88f46` (tag `foundation-v1`)
- **Quy tắc tuân thủ:** Không sửa bất kỳ file mã nguồn sản phẩm nào thuộc `api/**`, `web/src/**`, `contracts/**`. Không tự ý merge vào nhánh chung.

---

## 2. Danh sách file thuộc sở hữu và đã tạo mới

```text
tests/
├── __init__.py
├── conftest.py                             # Cấu hình pytest, markers, fixtures dùng chung
├── run_tests.py                            # Script điều phối và báo cáo kiểm thử CLI
├── contract/                               # Kiểm thử hợp đồng (chạy và đạt 100%)
│   ├── __init__.py
│   ├── test_openapi_contract.py            # Kiểm thử hợp đồng OpenAPI 3.0.3 (29 routes, schema, error)
│   ├── test_fixtures_contract.py           # Kiểm thử dữ liệu mẫu contracts/seed-fixtures.json
│   └── test_states_contract.py             # Kiểm thử máy trạng thái Campaign & Case (states.md)
├── fixtures/                               # Công cụ hỗ trợ kiểm thử
│   ├── __init__.py
│   ├── client.py                           # AcceptanceTestClient hỗ trợ phiên, CSRF, giả lập 4 vai trò
│   └── loader.py                           # Loader đọc OpenAPI, seed fixtures, states markdown
└── e2e/                                    # 16 Kiểm thử chấp nhận theo Mục 9 đặc tả V1
    ├── __init__.py
    ├── test_01_student_isolation.py         # Mục 9.1: STUDENT chỉ thấy case mình; sửa ID bị 404/403
    ├── test_02_bcs_gvcn_rbac.py             # Mục 9.2: BCS lớp A không mở case lớp B; GVCN không sửa điểm
    ├── test_03_draft_persistence.py         # Mục 9.3: Lưu nháp và tải lại giữ nguyên điểm/tệp; tổng đúng
    ├── test_04_missing_evidence_info.py     # Mục 9.4: Thiếu minh chứng bắt buộc -> NEEDS_INFO, bổ sung đúng hạn -> BCS_REVIEW
    ├── test_05_info_round_limit_close.py    # Mục 9.5: Hết lượt/hạn bổ sung INFO đóng CLOSED_INCOMPLETE
    ├── test_06_bcs_proof_request.py         # Mục 9.6: BCS yêu cầu PROOF; quá hạn quay BCS kết luận, không tự trừ
    ├── test_07_bcs_scoring_validation.py    # Mục 9.7: Điểm vượt max/khác tự khai không lý do bị 422; tổng đúng
    ├── test_08_publication_gates.py         # Mục 9.8: Chưa đủ 2 cuộc họp hoặc còn case chờ BCS -> không công bố
    ├── test_09_score_visibility.py          # Mục 9.9: Trước công bố SV không thấy điểm; sau công bố thấy đúng điểm
    ├── test_10_mutual_exclusion_accept_appeal.py # Mục 9.10: Đồng ý không thể khiếu nại và ngược lại; concurrency
    ├── test_11_appeal_resolution_audit.py   # Mục 9.11: BCS giải quyết KEEP/ADJUST; audit trail truy được
    ├── test_12_deadline_tick_idempotent.py  # Mục 9.12: Tick chạy 2 lần không trùng thông báo, không tăng lượt
    ├── test_13_auto_accept_timeout.py       # Mục 9.13: Quá hạn phản hồi thành ACCEPTED_AUTO đúng 1 lần
    ├── test_14_finalize_and_gvcn_csv.py     # Mục 9.14: Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt
    ├── test_15_file_security_mime.py        # Mục 9.15: Tệp không xem trực tiếp storage; kiểm MIME PDF/JPG/PNG
    └── test_16_scheduled_campaign_open.py   # Mục 9.16: Đợt SCHEDULED chưa tạo case; tick ở open_at tạo đúng 1 case/SV

handoff/
├── D.md                                     # Tài liệu bàn giao này
└── D-contract-issues.md                     # Ghi nhận vấn đề hợp đồng chờ giải quyết ở Giai đoạn 2
```

---

## 3. Chức năng đã hoàn thành

1. **Bộ kiểm thử hợp đồng tự động (`tests/contract/**`):**
   - Xác thực cấu trúc YAML và siêu dữ liệu của `contracts/openapi.yaml` đạt chuẩn OpenAPI 3.0.3.
   - Kiểm tra đầy đủ toàn bộ 29 routes theo Mục 7 của đặc tả kèm HTTP methods.
   - Kiểm tra định dạng lỗi chuẩn hóa `{"error": {"code": "...", "message": "...", "fields": {}}}`.
   - Kiểm tra các định nghĩa Enum: `Role`, `CampaignStatus`, `CaseStatus`, `SupplementKind`, `MeetingKind`, `AppealStatus`, `AppealResolution`.
   - Kiểm tra định nghĩa tham số concurrency `expected_version` và header `Idempotency-Key`.
   - Kiểm tra tính toàn vẹn của dữ liệu seed trong `contracts/seed-fixtures.json` (6 tài khoản demo đúng phân quyền lớp, cấu hình đợt mẫu, 3 tiêu chí TC01/TC02/TC03).
   - Kiểm tra cấu trúc 7 mock responses cho UI.
   - Kiểm tra ma trận chuyển trạng thái hợp lệ và các trạng thái kết thúc (terminal states) theo `contracts/states.md`.

2. **Bộ 16 kiểm thử chấp nhận đen hộp (`tests/e2e/**`):**
   - Đã viết đầy đủ mã kiểm thử chi tiết cho toàn bộ 16 tiêu chí Mục 9.
   - Sử dụng `AcceptanceTestClient` mô phỏng đầy đủ chu trình: đăng nhập nhận cookie/CSRF, nộp hồ sơ, tải minh chứng, duyệt điểm, lập biên bản họp, công bố, đồng ý/khiếu nại, giải quyết khiếu nại, chốt đợt và xuất CSV.
   - Đánh dấu kiểm thử chờ backend bằng marker `@pytest.mark.acceptance` kết hợp `pytest.mark.skipif(not os.getenv("RUN_ACCEPTANCE_TESTS"))` kèm thông báo lý do rõ ràng.

3. **Công cụ điều phối kiểm thử (`tests/run_tests.py`):**
   - Hỗ trợ các chế độ chạy: `runnable` (mặc định), `contract`, `e2e`, `all`.
   - Tự động thiết lập `PYTHONPATH` và xuất báo cáo trạng thái chi tiết theo 16 tiêu chí.

---

## 4. Lệnh kiểm thử đã thực sự chạy và kết quả thực tế

### Lệnh 1: Chạy kiểm thử hợp đồng
```bash
python -m pytest tests/contract
```
**Kết quả thực tế:**
```text
tests/contract/test_fixtures_contract.py ......                          [ 13%]
tests/contract/test_openapi_contract.py .....                            [ 23%]
tests/contract/test_states_contract.py ................................. [ 95%]
..                                                                       [100%]
======================== 46 passed, 1 warning in 0.31s ========================
```
- **Số lượng:** 46/46 passed (100%).

### Lệnh 2: Chạy toàn bộ test suite hiện khả dụng
```bash
python tests/run_tests.py
```
**Kết quả thực tế:**
```text
tests\contract\test_fixtures_contract.py ......                          [  9%]
tests\contract\test_openapi_contract.py .....                            [ 17%]
tests\contract\test_states_contract.py ................................. [ 69%]
..                                                                       [ 73%]
tests\e2e\test_01_student_isolation.py s                                 [ 74%]
tests\e2e\test_02_bcs_gvcn_rbac.py s                                     [ 76%]
tests\e2e\test_03_draft_persistence.py s                                 [ 77%]
tests\e2e\test_04_missing_evidence_info.py s                             [ 79%]
tests\e2e\test_05_info_round_limit_close.py s                            [ 80%]
tests\e2e\test_06_bcs_proof_request.py s                                 [ 82%]
tests\e2e\test_07_bcs_scoring_validation.py s                            [ 84%]
tests\e2e\test_08_publication_gates.py s                                 [ 85%]
tests\e2e\test_09_score_visibility.py s                                  [ 87%]
tests\e2e\test_10_mutual_exclusion_accept_appeal.py ss                   [ 90%]
tests\e2e\test_11_appeal_resolution_audit.py s                           [ 92%]
tests\e2e\test_12_deadline_tick_idempotent.py s                          [ 93%]
tests\e2e\test_13_auto_accept_timeout.py s                               [ 95%]
tests\e2e\test_14_finalize_and_gvcn_csv.py s                             [ 96%]
tests\e2e\test_15_file_security_mime.py s                                [ 98%]
tests\e2e\test_16_scheduled_campaign_open.py s                           [100%]

================== 46 passed, 17 skipped, 1 warning in 0.37s ==================
```

---

## 5. Bảng trạng thái 16 tiêu chí chấp nhận Mục 9

| Mục | Nội dung tiêu chí | File kiểm thử | Trạng thái Giai đoạn 1 | Điều kiện để chạy ở Giai đoạn 2 |
|---|---|---|:---:|---|
| **9.1** | STUDENT chỉ thấy case của chính mình; sửa ID nhận 404/403 | `test_01_student_isolation.py` | `SKIPPED` | Ghép xong auth/session và quyền sinh viên của Gói A |
| **9.2** | BCS lớp A không mở được case lớp B; GVCN không gọi API sửa điểm | `test_02_bcs_gvcn_rbac.py` | `SKIPPED` | Ghép xong RBAC theo lớp và chặn sửa điểm với GVCN |
| **9.3** | Form lưu nháp rồi tải lại giữ nguyên điểm và tệp; tổng tự khai đúng | `test_03_draft_persistence.py` | `SKIPPED` | Ghép xong API claim/evidence draft và tính claimed_total |
| **9.4** | Nộp thiếu minh chứng bắt buộc -> NEEDS_INFO, bổ sung đúng hạn -> BCS_REVIEW | `test_04_missing_evidence_info.py` | `SKIPPED` | Ghép xong logic submit, phát hiện thiếu file và tạo supplement request |
| **9.5** | Hết lượt hoặc hết hạn bổ sung INFO đóng CLOSED_INCOMPLETE; không tạo lặp | `test_05_info_round_limit_close.py` | `SKIPPED` | Ghép xong kiểm tra max_info_rounds và timeout job |
| **9.6** | BCS yêu cầu PROOF, SV nộp lại; quá hạn PROOF quay BCS để kết luận, không tự trừ | `test_06_bcs_proof_request.py` | `SKIPPED` | Ghép xong API yêu cầu PROOF và xử lý quá hạn quay lại BCS |
| **9.7** | BCS nhập điểm vượt max hoặc khác tự khai không lý do bị 422; tổng cộng đúng | `test_07_bcs_scoring_validation.py` | `SKIPPED` | Ghép xong validation điểm duyệt và tính proposed_total |
| **9.8** | Chưa đủ 2 cuộc họp hoặc còn case chờ BCS thì không công bố; đủ công bố 1 lần | `test_08_publication_gates.py` | `SKIPPED` | Ghép xong gate công bố (meetings check, case states check) |
| **9.9** | Trước công bố SV không thấy điểm dự kiến; sau công bố thấy đúng điểm và hạn | `test_09_score_visibility.py` | `SKIPPED` | Ghép xong bộ lọc bảo mật điểm dự kiến trước PUBLISHED |
| **9.10** | SV đồng ý thì không thể khiếu nại; khiếu nại thì không thể đồng ý; concurrency | `test_10_mutual_exclusion_accept_appeal.py` | `SKIPPED` | Ghép xong state machine mutual exclusion và version check |
| **9.11** | BCS giải quyết khiếu nại KEEP và ADJUST; điểm cũ/mới, lý do, người xử lý truy được | `test_11_appeal_resolution_audit.py` | `SKIPPED` | Ghép xong API resolve appeal, tính lại tổng và lưu audit log |
| **9.12** | Deadline tick chạy 2 lần không gửi trùng thông báo, không tăng lượt hai lần | `test_12_deadline_tick_idempotent.py` | `SKIPPED` | Ghép xong lệnh `api.app.jobs.tick` và dedup_key thông báo |
| **9.13** | Quá hạn phản hồi SV chưa đồng ý/khiếu nại thành ACCEPTED_AUTO đúng 1 lần | `test_13_auto_accept_timeout.py` | `SKIPPED` | Ghép xong job quét timeout sau appeal_deadline_at |
| **9.14** | Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt | `test_14_finalize_and_gvcn_csv.py` | `SKIPPED` | Ghép xong gate finalize và endpoint xuất CSV điểm chính thức |
| **9.15** | Tệp không thể xem bằng URL storage trực tiếp; API kiểm quyền và MIME | `test_15_file_security_mime.py` | `SKIPPED` | Ghép xong validation MIME (PDF/JPG/PNG) và stream quyền riêng tư |
| **9.16** | Đợt SCHEDULED chưa tạo case; tick ở open_at tạo đúng 1 case mỗi SV, không tạo trùng | `test_16_scheduled_campaign_open.py` | `SKIPPED` | Ghép xong lệnh tick mở đợt và khởi tạo case DRAFT |

---

## 6. Hướng dẫn chạy kiểm thử khi ghép Giai đoạn 2

Khi người ghép hoàn thành việc gộp Gói A vào nhánh chung:
```bash
# 1. Chạy toàn bộ 16 kiểm thử chấp nhận Mục 9:
python tests/run_tests.py --mode e2e
# hoặc qua biến môi trường:
RUN_ACCEPTANCE_TESTS=1 python -m pytest tests/e2e -v

# 2. Chạy toàn bộ cả hợp đồng và kiểm thử chấp nhận:
python tests/run_tests.py --mode all
```

---

## 7. Đề xuất cho Giai đoạn 2
Chi tiết các lưu ý về hợp đồng API và fixtures được ghi tại: `handoff/D-contract-issues.md`.
Gói D đã sẵn sàng bàn giao; không thực hiện merge code vào nhánh chung.
