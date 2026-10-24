# Hợp đồng trạng thái hệ thống chấm điểm rèn luyện (V1)

Tài liệu này chuẩn hóa toàn bộ vòng đời, trạng thái, điều kiện chuyển và tác dụng phụ của đợt đánh giá (Campaign) và hồ sơ rèn luyện (Case). Đây là tài liệu nguồn khóa ở Giai đoạn 0.

---

## 1. Trạng thái đợt đánh giá (Campaign Status)

```text
DRAFT ────(Lên lịch/mở)────► SCHEDULED ────(Đến giờ open_at)────► OPEN
  │                                                                 │
  └──────────────────────────(Mở ngay nếu đã đến giờ)───────────────┘
                                                                    │
                                                              (Hết hạn nộp)
                                                                    ▼
FINALIZED ◄──(BCS chốt cả lớp)─── PUBLISHED ◄──(BCS công bố)─── REVIEW
```

| Trạng thái | Ý nghĩa | Hành động khả dụng | Ai thực hiện |
|---|---|---|---|
| `DRAFT` | Đợt mới tạo, đang soạn thảo cấu hình | Sửa cấu hình, tiêu chí, thời hạn; Lên lịch hoặc Mở đợt | ADMIN |
| `SCHEDULED` | Đã lên lịch, thời gian `open_at` còn ở tương lai | Xem trạng thái; chờ đến giờ mở | Hệ thống / Timer tick |
| `OPEN` | Đang mở cho sinh viên tự chấm và nộp minh chứng | Sinh viên nộp hồ sơ, sửa nháp, bổ sung | Sinh viên |
| `REVIEW` | Hết hạn nộp; toàn bộ hồ sơ đang được BCS kiểm tra/xử lý | BCS xem xét, yêu cầu bổ sung, chấm điểm, ghi nhận họp | BCS |
| `PUBLISHED` | Điểm dự kiến đã được công bố toàn lớp | Sinh viên xem điểm, bấm Đồng ý hoặc Khiếu nại; BCS xử lý khiếu nại | Sinh viên & BCS |
| `FINALIZED` | Toàn bộ khiếu nại đã xử lý, điểm đã được chốt chính thức | GVCN và BCS xem/tải bảng điểm chốt CSV. Không cho sửa đổi | GVCN, BCS |

---

## 2. Bảng chuyển trạng thái đợt đánh giá

| Từ | Đến | Tác nhân / Sự kiện | Điều kiện tiên quyết | Tác dụng phụ |
|---|---|---|---|---|
| `DRAFT` | `SCHEDULED` | ADMIN gọi `POST /admin/campaigns/{id}/open` | `open_at > NOW()` | Khóa sửa đổi tiêu chí và thời hạn cơ bản. |
| `DRAFT` | `OPEN` | ADMIN gọi `POST /admin/campaigns/{id}/open` | `open_at <= NOW()` | Khóa sửa tiêu chí; tự động khởi tạo hồ sơ `DRAFT` cho mọi sinh viên trong lớp; ghi `opened_at = NOW()`. |
| `SCHEDULED` | `OPEN` | Deadline tick / Timer | `open_at <= NOW()` | Khởi tạo hồ sơ `DRAFT` cho mọi sinh viên trong lớp; ghi `opened_at = NOW()`. |
| `OPEN` | `REVIEW` | Deadline tick / Timer | `submission_deadline_at <= NOW()` hoặc mọi SV đã nộp/đóng | Chuyển trạng thái đợt sang `REVIEW`. Các hồ sơ còn ở `DRAFT` chuyển thành `CLOSED_NO_SUBMIT`. |
| `REVIEW` | `PUBLISHED` | BCS gọi `POST /bcs/campaigns/{id}/publish` | Tất cả case trong đợt đã `PROPOSED` hoặc `CLOSED_*`; Đã có bản ghi họp BCS và họp Lớp | Tạo `score_snapshots(kind=PUBLISHED)` bất biến; đặt `appeal_deadline_at = published_at + appeal_period_hours`; gửi thông báo công bố đến tất cả sinh viên. |
| `PUBLISHED` | `FINALIZED` | BCS gọi `POST /bcs/campaigns/{id}/finalize` | Không còn case nào ở trạng thái `APPEALED` hoặc `PUBLISHED` chưa chốt; tất cả đã `ACCEPTED`, `ACCEPTED_AUTO`, `RESOLVED`, hoặc `CLOSED_*` | Tính `final_total` cho từng sinh viên; tạo `score_snapshots(kind=FINAL)`; ghi `finalized_at = NOW()`; cho phép GVCN xuất CSV. |

---

## 3. Trạng thái hồ sơ rèn luyện (Case Status)

```text
               ┌───────────────────────┐
               │         DRAFT         │
               └──────────┬────────────┘
                          │ (SV nộp trước hạn)
                          ▼
                  ┌───────────────┐  (quá hạn nộp)
                  │   SUBMITTED   ├───────────────► [CLOSED_NO_SUBMIT]
                  └───────┬───────┘
          (thiếu tệp)     │     (đủ cấu trúc)
         ┌────────────────┴───────────────┐
         ▼                                ▼
┌─────────────────┐             ┌─────────────────┐
│   NEEDS_INFO    │             │   BCS_REVIEW    │◄─────────────────┐
└────────┬────────┘             └────────┬────────┘                  │
         │ (hết hạn/lượt)                │ (BCS yêu cầu)             │ (SV nộp lại/
         ├────────► [CLOSED_INCOMPLETE]  ├────────► ┌─────────────┐  │  quá hạn)
         │ (SV bổ sung)                  │          │ NEEDS_PROOF ├──┘
         └───────────────────────────────┘          └─────────────┘
                                         │ (BCS duyệt xong)
                                         ▼
                                ┌─────────────────┐
                                │    PROPOSED     │
                                └────────┬────────┘
                                         │ (BCS công bố cả lớp)
                                         ▼
                                ┌─────────────────┐
                                │    PUBLISHED    │
                                └────┬───┬───┬────┘
                   (SV đồng ý)       │   │   │ (hết hạn phản hồi)
          ┌──────────────────────────┘   │   └──────────────────────┐
          ▼                              ▼                          ▼
   ┌──────────────┐             ┌─────────────────┐        ┌──────────────────┐
   │   ACCEPTED   │             │    APPEALED     │        │  ACCEPTED_AUTO   │
   └──────┬───────┘             └────────┬────────┘        └────────┬─────────┘
          │                              │ (BCS xử lý xong)         │
          │                              ▼                          │
          │                     ┌─────────────────┐                 │
          │                     │    RESOLVED     │                 │
          │                     └────────┬────────┘                 │
          │                              │                          │
          └──────────────────────────────┼──────────────────────────┘
                                         │ (BCS chốt cả lớp)
                                         ▼
                                ┌─────────────────┐
                                │    FINALIZED    │
                                └─────────────────┘
```

---

## 4. Bảng chuyển trạng thái hồ sơ rèn luyện

| Từ | Đến | Tác nhân | Điều kiện tiên quyết | Tác dụng phụ |
|---|---|---|---|---|
| `(Chưa có)` | `DRAFT` | Hệ thống | Khi đợt chuyển sang `OPEN` | Tạo 1 bản ghi `cases` với `version=1`, `info_round=0`, `proof_round=0` cho mỗi SV. |
| `DRAFT` | `SUBMITTED` | Sinh viên | Đợt `OPEN`, trước `submission_deadline_at`, mọi tiêu chí có `self_score` hợp lệ | Ghi `submitted_at = NOW()`, tăng `version`. |
| `SUBMITTED` | `NEEDS_INFO` | Hệ thống | Tiêu chí `requires_evidence=true` thiếu tệp, hoặc thiếu trường bắt buộc; `info_round < max_info_rounds` | Tăng `info_round`, tạo `supplement_requests(kind=INFO)`, đặt hạn `deadline_at = NOW() + supplement_period_hours`, gửi thông báo cho SV. |
| `SUBMITTED` | `CLOSED_INCOMPLETE` | Hệ thống | Thiếu tệp/thông tin bắt buộc nhưng `info_round >= max_info_rounds` | Đóng hồ sơ, không cho nộp lại, gửi thông báo cho SV và BCS. |
| `SUBMITTED` | `BCS_REVIEW` | Hệ thống | Hồ sơ đủ cấu trúc thông tin (V1 dùng `ManualReviewProvider` đẩy toàn bộ về BCS) | Ghi nhận hồ sơ vào hàng chờ xử lý của BCS. |
| `NEEDS_INFO` | `BCS_REVIEW` | Sinh viên | SV cập nhật tệp/thông tin trước hạn bổ sung; thông tin hợp lệ | Thu hồi yêu cầu bổ sung (`fulfilled_at = NOW()`), chuyển vào hàng chờ BCS. |
| `NEEDS_INFO` | `CLOSED_INCOMPLETE` | Deadline tick | Quá `deadline_at` của yêu cầu INFO mà SV chưa bổ sung | Đóng hồ sơ không hoàn tất, gửi thông báo SV và BCS. |
| `DRAFT` | `CLOSED_NO_SUBMIT` | Deadline tick | Quá `submission_deadline_at` của đợt mà SV chưa nộp | Khóa hồ sơ, không tính điểm dự kiến, gửi thông báo SV và BCS. |
| `BCS_REVIEW` | `NEEDS_PROOF` | BCS | BCS yêu cầu bổ sung minh chứng; `proof_round < max_proof_rounds` | Ghi lý do/tiêu chí, tăng `proof_round`, tạo `supplement_requests(kind=PROOF)`, đặt `deadline_at`, thông báo SV. |
| `BCS_REVIEW` | `NEEDS_INFO` | BCS | BCS phát hiện thiếu thông tin; `info_round < max_info_rounds` | Ghi lý do/tiêu chí, tăng `info_round`, tạo `supplement_requests(kind=INFO)`, đặt `deadline_at`, thông báo SV. |
| `NEEDS_PROOF` | `BCS_REVIEW` | Sinh viên / Deadline tick | SV nộp tệp mới trước hạn HOẶC quá hạn nộp bổ sung | Quay lại hàng chờ BCS. Nếu quá hạn, BCS kết luận dựa trên minh chứng hiện có (không tự ý trừ điểm ngoài quy định). |
| `BCS_REVIEW` | `PROPOSED` | BCS | Mọi tiêu chí có `approved_score` hợp lệ; tiêu chí có điểm duyệt khác tự khai bắt buộc có `reason` | Tính `proposed_total = SUM(approved_score)`, lưu audit log, chuyển trạng thái hồ sơ thành `PROPOSED`. |
| `PROPOSED` | `PUBLISHED` | BCS (cả lớp) | Đợt đánh giá được công bố sau khi thỏa mãn điều kiện họp | Tạo `score_snapshots(kind=PUBLISHED)` bất biến; gắn `published_at`, `appeal_deadline_at`. |
| `PUBLISHED` | `ACCEPTED` | Sinh viên | Trước `appeal_deadline_at`, chưa gửi khiếu nại | Đặt `acceptance_source = 'EXPLICIT'`, ghi nhận SV đồng ý với điểm dự kiến. |
| `PUBLISHED` | `APPEALED` | Sinh viên | Trước `appeal_deadline_at`, chọn ít nhất 1 tiêu chí và nhập lý do | Tạo các bản ghi `appeals` tương ứng, chuyển case sang `APPEALED`, thông báo cho BCS. |
| `PUBLISHED` | `ACCEPTED_AUTO` | Deadline tick | Quá `appeal_deadline_at` mà SV chưa đồng ý hoặc khiếu nại | Đặt `acceptance_source = 'TIMEOUT'`, thông báo cho SV và BCS. |
| `APPEALED` | `RESOLVED` | BCS | Mọi `appeals` của case đã được giải quyết (`KEEP` hoặc `ADJUST` kèm lý do) | Cập nhật điểm tiêu chí mới nếu `ADJUST`, tính lại `proposed_total`, lưu audit log, thông báo cho SV. |
| `ACCEPTED` / `ACCEPTED_AUTO` / `RESOLVED` | `FINALIZED` | BCS (cả lớp) | Đợt chuyển sang `FINALIZED` | Tính `final_total`, tạo `score_snapshots(kind=FINAL)`. |

---

## 5. Quy tắc Idempotency và Concurrency

1. Mọi request thay đổi dữ liệu hồ sơ (`PUT /claims`, `POST /submit`, `PUT /review`, `POST /appeals`) gửi kèm `expected_version`.
2. Nếu `case.version != expected_version`, backend trả mã lỗi `409 CASE_CHANGED` cùng dữ liệu hồ sơ mới nhất.
3. Các hành động chốt/công bố/nộp hồ sơ nhận header `Idempotency-Key` để tránh thực hiện lặp lại khi bấm đúp hoặc lỗi mạng.
4. Lệnh Deadline tick (`python -m app.jobs.tick`) là idempotent: chạy nhiều lần tại cùng một mốc thời gian không nhân đôi thông báo (nhờ `dedup_key`), không chuyển sai trạng thái, và không lặp lượt bổ sung.
