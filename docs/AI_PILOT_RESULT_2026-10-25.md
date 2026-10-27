# Kết quả thử luồng AI cục bộ — 25/10/2026

## Phạm vi

Kịch bản dùng một ảnh chứng nhận **giả lập**, ghi rõ “GIẢ LẬP — KHÔNG HỢP LỆ ĐỂ CHẤM ĐIỂM”, cho tiêu chí 7b. Sinh viên thử tự chấm 1 điểm, tải ảnh và nộp; Ban cán sự thử tạo lượt phân tích. Cơ sở dữ liệu SQLite trong bộ nhớ và thư mục ảnh tạm được xóa sau lượt chạy. Không dùng hồ sơ thật, Supabase hoặc môi trường production. Script chạy lại: `python api/scripts/verify_ai_pilot.py --live`; kiểm tra phần ứng dụng không gọi model: `python api/scripts/verify_ai_pilot.py --stub-models`.

## Kết quả quan sát

| Ranh giới | Kết quả |
|---|---|
| Sinh viên → API → hồ sơ | Tự chấm, upload PNG, nộp thành công; hồ sơ chuyển `BCS_REVIEW`. |
| Ban cán sự → hàng chờ | Tạo run `QUEUED` thành công. |
| Gemini 3.6 `AI_Read` | Lượt thật đầu tiên hoàn tất, `readable=true`, trích 7 loại dữ kiện gồm hoạt động, ngày, đơn vị cấp, người nhận và mã. Chưa đối chiếu từng giá trị với nhãn chuẩn. |
| Gemini 3.8 `AI_Transparency` | Yêu cầu ảnh hết thời gian chờ 120 giây; worker ghi `MODEL_TIMEOUT` và xếp lại `QUEUED`. Một yêu cầu văn bản rất nhỏ tới 3.8 cũng hết thời gian chờ sau 45 giây. GET metadata của cả hai model trả HTTP 200. |
| Chẩn đoán đổi model đối chiếu sang 3.6 chỉ trong tiến trình thử | Bước đọc nhận lỗi tạm thời `503`, worker ghi `MODEL_TEMPORARILY_UNAVAILABLE` và xếp lại hàng chờ. Cấu hình chính vẫn là 3.8. |
| Luồng ứng dụng với đầu ra AI giả lập | Hai bước AI `COMPLETED`; ảnh được `FLAGGED`; điểm gợi ý là `null`; hồ sơ vẫn `BCS_REVIEW`; `approved_score` vẫn `null`. |

## Kết luận và việc còn lại

- API, hàng chờ, kết quả lưu trong run, tầng luật và quyền chốt điểm của Ban cán sự đi đúng luồng trên dữ liệu thử cô lập.
- **Chưa xác nhận chất lượng `AI_Transparency` bằng model 3.8 thật.** Mã model và dạng REST đã đối chiếu với tài liệu Google; phản hồi sinh nội dung hiện không ổn định trong lượt thử này. Không bật cờ AI production.
- Khi dịch vụ phản hồi ổn định, chạy lại script với `--live`, sau đó dùng bộ minh chứng **đã ẩn danh** có kết luận mong đợi của Ban cán sự để đo ca hợp lệ, không hợp lệ và mơ hồ. Ảnh giả lập chỉ kiểm tra luồng kỹ thuật, không đại diện chất lượng với tài liệu thật.

## Điều tra bổ sung về timeout 3.8

- Yêu cầu 3.8 chỉ có chữ “Reply with OK”, suy luận `low`, vẫn timeout sau 30 giây bằng `httpx` và sau 20 giây bằng `urllib`; streaming cũng timeout sau 25 giây. Do đó không quy lỗi cho ảnh, JSON schema, suy luận `medium` hoặc riêng thư viện HTTP của dự án.
- POST sai dữ liệu tới cả 3.8 và 3.6 trả HTTP `400 INVALID_ARGUMENT` trong khoảng 0,1–0,2 giây: DNS/TLS/đường POST tới API thông. Cùng khóa và máy đó, yêu cầu văn bản hợp lệ tới 3.6 trả HTTP 200 trong 1,8 giây. Không thấy proxy từ biến môi trường.
- Google quy định vượt RPM/TPM/RPD và giới hạn chi tiêu trả `429`; lượt thử 3.8 không nhận `429`. [Tài liệu giới hạn](https://ai.google.dev/gemini-api/docs/rate-limits), [mã lỗi API](https://ai.google.dev/gemini-api/docs/api-errors).
- Một [ca gần như trùng trên diễn đàn Google](https://discuss.ai.google.dev/t/gemini-3-8-flash-generatecontent-reaches-client-deadline-before-response-headers/188354) được nhân viên Google xác nhận: cấu hình 3.8 hợp lệ, nhưng nhu cầu cao tạm thời có thể làm phản hồi vượt quá deadline của client. [Ca khác](https://discuss.ai.google.dev/t/gemini-3-8-flash-api-returns-503-but-ai-studio-works/187076) ghi nhận AI Studio vẫn chạy trong khi API 3.8 lỗi với cùng tài khoản/mạng.
- **Kết luận có xác suất cao cho lượt thử ban đầu:** nút thắt nằm ở dịch vụ suy luận/routing của API 3.8 tại thời điểm thử, không phải RPM của dự án. Chưa thể chứng minh sự cố toàn cầu hoặc loại trừ hoàn toàn khác biệt dự án/API key đang xem trong AI Studio. Lượt thử dùng retry có giới hạn, không tự chuyển model.

## Thử cấu hình mới: đọc 3.5 Flash-Lite, đối chiếu 3.6 Flash

Theo yêu cầu sau đó, cấu hình cục bộ được đổi sang `gemini-3.5-flash-lite` cho `AI_Read` và `gemini-3.6-flash` cho `AI_Transparency`. Hai lượt chạy cô lập với cùng ảnh giả lập đều cho kết quả `AI_READ=COMPLETED`: model Lite trích đúng loại giấy, đơn vị giả lập, tên người nhận, hoạt động, ngày 15/10/2026 và mã DEMO-001. Cả hai lượt `AI_TRANSPARENCY` nhận HTTP 503, được worker ghi `MODEL_TEMPORARILY_UNAVAILABLE` và xếp lại hàng chờ; chưa có nhận xét minh chứng thật từ 3.6. Điểm BCS không đổi. Điều này xác nhận ánh xạ model và OCR mẫu hoạt động, nhưng **chưa xác nhận tầng đối chiếu live**. Các cờ AI production vẫn tắt.

## Chẩn đoán tiếp lỗi 503 của tầng đối chiếu

- Thử riêng Gemini 3.6 với năm biến thể: văn bản ngắn `medium`, schema JSON, prompt/quy tắc đầy đủ nhưng không có ảnh, payload đầy đủ có ảnh ở mức `medium`, và cùng payload ở mức `low`. Cả năm trả HTTP 200; payload đầy đủ gồm ảnh giả lập, schema và quy tắc hoàn tất trong khoảng 8,6 giây. Vì vậy không thấy lỗi cố định ở cấu trúc request, ảnh, schema hay mức suy luận.
- Một lượt chạy toàn bộ ứng dụng ngay sau đó vẫn nhận 503 ở `AI_Transparency`; lượt kế tiếp với cùng model và ảnh hoàn tất trong 15,6 giây. Model trả `FLAGGED`, sáu trích dẫn, không đưa điểm dự thảo, để Ban cán sự chốt. Một lượt xác nhận sau sửa cũng hoàn tất (`NEEDS_HUMAN`, hai bước `COMPLETED`, không có `error_code`).
- Kết luận theo bằng chứng hiện có: 503 xảy ra gián đoạn trên endpoint Gemini 3.6, không phải request đối chiếu luôn sai. Chưa ghi được nội dung body của phản hồi 503 nên không thể chỉ rõ hơn dịch vụ con nào gây lỗi. [Google mô tả 503 là dịch vụ tạm quá tải hoặc không sẵn sàng và khuyến nghị retry có backoff](https://ai.google.dev/gemini-api/docs/troubleshooting).
- Provider đối chiếu giờ thử lại tối đa hai lần sau HTTP 500/502/503/504, với khoảng chờ tăng dần và jitter. Nếu vẫn lỗi, worker giữ cơ chế xếp hàng lại tối đa ba lượt và không sửa điểm BCS. Kiểm tra liên quan: 10 bài passed. Cờ AI production vẫn tắt; ảnh giả lập chưa đủ để đánh giá chất lượng trên hồ sơ thật.
