# Kế hoạch đối soát BPMN và UX/UI

Ngày khảo sát: 26/10/2026. Đây là kiểm toán tĩnh theo mã nguồn; chưa chạy trình duyệt, chưa sửa code, chưa gọi Gemini.

## 1. Nguồn chuẩn và phạm vi

**BPMN chuẩn do người dùng chỉ định:** C:/Users/ADMIN/Downloads/Nhom8_TOBE_NangCao_BPMN20-1.bpmn (SHA-256: 64FE72E8035FD7F27E3D7EE7057B38379C7453D5431AADEE4F1784D12B1BE655). Không dùng bản Nhom8_TOBE_NangCao_BPMN20.bpmn hay bản v6 trong dự án làm chuẩn. Bản v6 ở gốc dự án và Input chỉ dùng để nhận diện lệch phiên bản: bản mới thêm SC_CheckEvidenceRules và bốn gateway nhập nhánh; bỏ SC_HumanAIReview và SC_MergeValid. Nguồn BPMN chuẩn đang nằm ngoài repository; khi triển khai nên lưu bản đã duyệt cùng mã hash trong kho tài liệu dự án.

Sơ đồ chuẩn có 108 phần tử cần theo dõi: 16 user task, 2 manual task, 10 service task, 9 send task, 10 subprocess, 12 exclusive gateway (XOR), 4 event-based gateway, 12 start event, 11 intermediate catch event, 2 boundary event và 20 end event. Có 95 sequence flow và 15 message flow. **Không có inclusive gateway (OR) hoặc parallel gateway (AND)**; multi-instance của hai subprocess xử lý từng sinh viên không đồng nghĩa có AND gateway trên UI.

Ứng dụng hiện là React Router/Vite + FastAPI điều khiển trạng thái; chưa thấy BPMN engine thực thi trực tiếp file XML. Vì vậy “Khớp” nghĩa là hành động/trạng thái tương đương có trong UI và API, không khẳng định engine chạy BPMN. “Thiếu” bao gồm trường hợp đã có một phần nhưng thiếu hành động, nhánh, thông báo hoặc ràng buộc để người dùng hoàn tất đúng luồng. “Thừa” là chức năng hỗ trợ nằm ngoài các node của sơ đồ, không mặc định là cần xóa. Đối với timer/service/send/end event, UI cần cho thấy trạng thái hoặc thông báo đúng; không cần tạo nút để chạy sự kiện tự động.

### Tài nguyên trọng tâm

| Nhóm | File/đường dẫn | Vai trò khảo sát |
|---|---|---|
| BPMN | C:/Users/ADMIN/Downloads/Nhom8_TOBE_NangCao_BPMN20-1.bpmn | Nguồn chuẩn duy nhất của ma trận |
| Sơ đồ tham chiếu | Nhom8_TOBE_NangCao_BPMN20_v6.bpmn; ../Input/Nhom8_TOBE_NangCao_BPMN20_v6.bpmn; ../Input/Nhom8_Asis (1).drawio | Bản To-Be cũ và As-Is để hiểu lịch sử; không ghi đè bản chuẩn mới |
| Quy trình và trạng thái | contracts/states.md; docs/AI_AGENT_V1_PLAN.md; DAC_TA_CODE_WEB_VO_V1.md | Hợp đồng trạng thái V1 và phạm vi pilot; tài liệu cũ có thể dựa trên v6 |
| Thiết kế/chia việc trước đây | ../output/Ban_do_AI_cho_BPMN_ToBe_Chuong3.md; ../output/NHAN_XET_BPMN_V6_VA_DINH_HUONG_V7.md; PHAN_CHIA_CODE_SONG_SONG_V1.md | Cơ chế AI/luật và giả định V1; dùng làm bối cảnh, không thay BPMN chuẩn |
| Router và quyền | web/src/App.tsx; web/src/components/ProtectedRoute.tsx; web/src/context/AuthContext.tsx | Tuyến màn hình theo vai trò |
| Layout và thiết kế | web/src/components/AppLayout.tsx; web/src/components/StatusBadge.tsx; web/src/components/Deadline.tsx; web/src/components/ConfirmDialog.tsx; web/src/styles/tokens.css; web/src/components/student/studentStyles.css | Điều hướng, trạng thái, modal, token |
| Sinh viên | web/src/pages/student/StudentDashboard.tsx; StudentSubmission.tsx; StudentResult.tsx; StudentAppeal.tsx; web/src/components/student/CriterionCard.tsx; EvidenceViewer.tsx; studentService.ts | Tự chấm, nộp/bổ sung, nhận điểm, phản hồi |
| BCS | web/src/pages/bcs/BcsDashboard.tsx; BcsCases.tsx; BcsCaseDetail.tsx; BcsScores.tsx; BcsAppeals.tsx; web/src/components/staff/SupplementRequestModal.tsx; MeetingRecordModal.tsx; SafeFilePreviewModal.tsx | Xử lý hồ sơ, họp, công bố, khiếu nại |
| Quản trị/GVCN | web/src/pages/admin/AdminCampaigns.tsx; web/src/pages/gvcn/GvcnFinalScores.tsx | Cấu hình đợt và xem bảng điểm cuối |
| API và luật | web/src/api/client.ts; web/src/api/types.ts; api/app/routes/student.py; bcs.py; admin.py; ai_reviews.py; notifications.py; gvcn.py; internal.py; api/app/services/workflow_service.py; deadline_service.py; rule_check_service.py; score_decision_service.py | Xác minh hành động UI có endpoint và nhánh điều kiện |
| Kiểm thử hiện có | web/src/tests/student; web/src/tests/staff; web/src/tests/integration; api/tests | Điểm đặt ca kiểm thử khi triển khai kế hoạch |

Đã quét các tệp .bpmn, .drawio, .xml và Markdown trong hai thư mục dự án/đầu vào; không thấy tệp .xml quy trình độc lập khác cần đối soát. Bản BPMN được chỉ định nằm ngoài hai thư mục này và đã được đọc trực tiếp.

### Ký hiệu file trong ma trận

Để ma trận dễ đọc, ký hiệu SD = StudentDashboard.tsx; SS = StudentSubmission.tsx; SR = StudentResult.tsx; SA = StudentAppeal.tsx; BD = BcsDashboard.tsx; BL = BcsCases.tsx; BC = BcsCaseDetail.tsx; BS = BcsScores.tsx; BA = BcsAppeals.tsx; AC = AdminCampaigns.tsx; GF = GvcnFinalScores.tsx. Tất cả nằm dưới web/src/pages theo vai trò. L = web/src/components/AppLayout.tsx; CD = web/src/components/ConfirmDialog.tsx. Cột “API/luật” nêu điểm tự động không có màn hình riêng.

## 2. Traceability matrix: từng phần tử BPMN → giao diện

### 2.1. Pool sinh viên và các event subprocess

| ID (loại) | UI / API/luật tương ứng | Trạng thái | Nhận xét đối soát |
|---|---|---|---|
| ST_Start (message start) | SD; thông báo mở đợt từ workflow_service.py | Khớp | Có trạng thái đợt và thông báo; không cần nút Start. |
| ST_Login (user) | LoginPage.tsx, AuthContext.tsx | Khớp | Đăng nhập và điều hướng theo vai trò. |
| ST_Self (user) | SS, CriterionCard.tsx, EvidenceViewer.tsx | Khớp | Tự chấm, ghi chú và tệp; biểu mẫu dài cần cải thiện phân cấp. |
| ST_Submit (user) | SS, CD; student.py /submit | Thiếu | Có nộp, nhưng cảnh báo thiếu minh chứng không nằm trong nội dung xác nhận cuối. |
| ST_GetDraft (message catch) | SD, SR; notifications.py | Khớp | Chỉ hiện điểm sau PUBLISHED. |
| ST_View (user) | SR | Khớp | Có xem điểm và hai CTA phản hồi trong hạn. |
| ST_EndSilent (end) | SR, SD; ACCEPTED_AUTO | Khớp | Thể hiện tự chấp nhận khi hết hạn. |
| ST_GAppeal (XOR) | SR → SA hoặc xác nhận đồng ý; student.py | Khớp | Hai lựa chọn loại trừ; backend kiểm tra trạng thái và hạn. |
| ST_SendAppeal (user) | SA; student.py /appeals | Khớp | Chọn tiêu chí, nhập lý do, xác nhận nộp. |
| ST_GetResolution (message catch) | SA, SD; notifications.py | Khớp | Hiển thị giải quyết và thông báo. |
| ST_EndAppeal (end) | SA; RESOLVED | Khớp | Có trạng thái hoàn tất giải trình. |
| ST_SendAccept (user) | SR, CD; student.py /accept | Khớp | CTA đồng ý và xác nhận. |
| ST_EndAccept (end) | SR; ACCEPTED | Khớp | Có trạng thái chấp nhận rõ. |
| ES_Info (event subprocess) | SS, SD | Khớp | Luồng bổ sung INFO bằng trang nộp hiện có. |
| ES_Info_Start (message start) | SD/notifications; SS | Khớp | Thông báo yêu cầu và hạn bổ sung. |
| ST_SendInfo (user) | SS; student.py /submit | Khớp | Sửa thông tin và nộp lại. |
| ES_Info_End (end) | SS, SD; BCS_REVIEW | Khớp | Sau nộp bổ sung quay về hàng chờ BCS. |
| ES_Proof (event subprocess) | SS, SD | Khớp | Luồng minh chứng bổ sung qua cùng form. |
| ES_Proof_Start (message start) | SD/notifications; SS | Khớp | Có yêu cầu PROOF và deadline. |
| ST_SendProof (user) | SS, EvidenceViewer.tsx | Khớp | Upload và nộp minh chứng mới. |
| ES_Proof_End (end) | SS, SD; BCS_REVIEW | Khớp | Có phản hồi đã nộp. |
| ES_Remind (event subprocess) | SD; notifications.py | Khớp | Nhận thông báo nhắc hạn. |
| ES_Remind_Start (message start) | SD; deadline_service.py | Khớp | Timer gửi thông báo, UI có danh sách. |
| ES_Remind_End (end) | SD; đánh dấu đã đọc | Khớp | Có thao tác đọc thông báo. |
| ES_Closed (event subprocess) | SD | Khớp | Có CLOSED_NO_SUBMIT và CLOSED_INCOMPLETE. |
| ES_Closed_Start (message start) | SD/notifications | Khớp | Backend tạo thông báo khi đóng. |
| ES_Closed_End (end) | SD, SS | Khớp | Khóa form và hiện trạng thái đóng. |
| ES_AutoAccept (event subprocess) | SR, SD | Khớp | Nhận trạng thái ACCEPTED_AUTO. |
| ES_AutoAccept_Start (message start) | SD/notifications; deadline_service.py | Khớp | Backend phát thông báo tự chấp nhận. |
| ES_AutoAccept_End (end) | SR | Khớp | Điểm đã tự ghi nhận. |
| ST_ViewTimeout (timer boundary) | SR, SA; deadline_service.py | Thiếu | Backend chặn quá hạn; UI chỉ tính ngày ở lần render, chưa thấy đồng hồ làm mới trạng thái CTA đúng lúc hết hạn. |

### 2.2. Mở đợt, hồ sơ, kiểm tra và AI

| ID (loại) | UI / API/luật tương ứng | Trạng thái | Nhận xét đối soát |
|---|---|---|---|
| SC_Start (timer start) | AC; admin.py; deadline_service.py | Khớp | Cấu hình giờ mở, tick chuyển SCHEDULED → OPEN. |
| SC_Notify (send) | SD/notifications; workflow_service.py | Khớp | Thông báo mở đợt. |
| SC_PerStudent (multi-instance subprocess) | BD, BL; danh sách case trong bcs.py | Khớp | Có hồ sơ và tiến độ từng SV; không có AND gateway. |
| PST_Start (start) | BD, BL | Khớp | Mỗi case có trạng thái đầu. |
| SC_WaitSubmission (event gateway) | SS, SD; deadline_service.py | Khớp | Có nộp hoặc hết hạn. |
| SC_GetSubmission (message catch) | SS; student.py /submit | Khớp | Backend nhận hồ sơ. |
| SC_SubmissionTimeout (timer catch) | SD, SS; deadline_service.py | Khớp | Chặn nộp và đóng case chưa nộp. |
| SC_RecordNoSubmit (send) | SD; BD/BL; deadline_service.py | Thiếu | SV được báo; chưa thấy kênh cảnh báo riêng cho BCS như tên task. |
| PST_EndNoSubmit (end) | SD, BL; CLOSED_NO_SUBMIT | Khớp | Có trạng thái kết thúc. |
| SC_CheckCompleteness (service) | SS, BC; workflow_service.py | Khớp | Luật kiểm tra trường và tệp bắt buộc. |
| SC_GComplete (XOR) | SS, SD; workflow_service.py | Khớp | Đủ → BCS_REVIEW; thiếu → NEEDS_INFO hoặc đóng khi hết lượt. |
| SC_Package (service) | BC; ai_review_service.py | Khớp | Snapshot phiên bản hồ sơ/quy tắc tồn tại, UI hiện phiên bản AI khi bật. |
| SC_MissingNotice (send) | SD/notifications, SS | Khớp | Thông báo thiếu và hạn bổ sung. |
| SC_WaitInfo (event gateway) | SS, SD; deadline_service.py | Khớp | Nộp lại hoặc hết hạn. |
| SC_GetInfo (message catch) | SS; student.py /submit | Khớp | Nhận hồ sơ cập nhật. |
| SC_InfoTimeout (timer catch) | SD; deadline_service.py | Khớp | Đóng hồ sơ thiếu thông tin quá hạn. |
| SC_CloseIncomplete (send) | SD/notifications, BL | Khớp | Có trạng thái và thông báo SV. |
| SC_EndIncomplete (end) | SD, BL; CLOSED_INCOMPLETE | Khớp | Có trạng thái kết thúc. |
| SC_AlertEventSub (event subprocess) | BD, BL, BC | Thiếu | BCS thấy hàng chờ/chi tiết nhưng chưa có inbox cảnh báo AI có thể mở theo cờ. |
| EA_Start (conditional start) | BC; ai_review_service.py | Thiếu | Chưa thấy alertPending/trigger tương đương tạo thông báo BCS khi AI FLAGGED. |
| EA_SendAlert (service) | BD, BC; notifications.py | Thiếu | Không thấy thông báo cảnh báo riêng gửi tới BCS; UI phải tự vào case. |
| EA_End (end) | BD/BC | Thiếu | Không có trạng thái đã gửi/đọc cảnh báo để kiểm chứng nhánh. |
| SC_AIReview (subprocess) | BC; ai_reviews.py, internal.py | Thiếu | Có UI pilot bấm chạy và xem kết quả, nhưng bị khóa bằng VITE_AI_REVIEW_ENABLED; không phải luồng tự động khi nộp. |
| AI_Start (start) | BC | Thiếu | Chỉ khởi động khi BCS chủ động bấm ở pilot. |
| AI_Read (service) | BC; GeminiReadProvider | Thiếu | Có triển khai thử nghiệm, chưa bật ở bản dùng; không cần nút riêng. |
| AI_GReadable (XOR) | BC; kết quả đọc/lỗi AI | Thiếu | Có hiển thị lỗi chung, thiếu phân biệt “không đọc được” với “lỗi kỹ thuật/schema” theo nhánh BPMN. |
| SC_CheckEvidenceRules (service) | BC, SS; rule_check_service.py | Khớp | Kiểm tra ngày kỳ, tiêu chí, trùng tệp; có tình trạng NOT_CONFIGURED. |
| AI_Transparency (service) | BC; GeminiTransparencyProvider | Thiếu | Có code và thẻ kết luận pilot, chưa bật production và chưa thành quyết định BCS tường minh. |
| AI_End (end) | BC; NEEDS_HUMAN/COMPLETED | Thiếu | Pilot có kết quả, thiếu trạng thái nghiệp vụ cuối cho từng minh chứng sau BCS kết luận. |
| AI_ErrorEnd (error end) | BC; ai review error_code | Khớp | Có lỗi an toàn và đường xem thủ công. |
| SC_AIError (error boundary) | BC; bcs review | Khớp | Bản BPMN này đưa lỗi về BCS qua gateway nhập nhánh; UI vẫn cho BCS xử lý tay. |
| SC_GValid (XOR) | BC; ai_review_service.py | Thiếu | Điều kiện tự duyệt trong BPMN chưa được mở; pilot cố ý luôn cần BCS. Phải ghi đây là khoảng trống có chủ đích, không tự bật. |
| SC_Flag (service) | BC; rule findings/AI verdict | Thiếu | Có cờ/nhận xét, chưa thành trạng thái quyết định “cần xem xét” có người chịu trách nhiệm và dấu đã xử lý. |
| SC_BCSFlags (user) | BC; bcs.py /claims/.../review | Thiếu | BCS nhập điểm/lý do nhưng thiếu quyết định minh chứng ACCEPT / REQUEST_SUPPLEMENT / REJECT_ITEM / HOLD độc lập với điểm. |
| SC_GProofNeed (XOR) | BC, SupplementRequestModal.tsx | Thiếu | Chỉ có yêu cầu bổ sung và chấm điểm; nhánh mặc định BPMN đi “không hợp lệ”, chưa mô tả HOLD/hết lượt rõ trên UI. |
| SC_RequestProof (send) | BC, SupplementRequestModal.tsx; bcs.py | Khớp | Có lý do, tiêu chí, giới hạn lượt và thông báo SV. |
| SC_WaitProof (event gateway) | SS, BC; deadline_service.py | Khớp | Chờ tệp hoặc hết hạn. |
| SC_GetProof (message catch) | SS; student.py /submit | Khớp | Nhận tệp mới, quay lại BCS_REVIEW. |
| SC_ProofTimeout (timer catch) | BC; deadline_service.py | Khớp | Bản BPMN mới quay lại BCSFlags qua Gateway_13j85dv; backend cũng trả BCS_REVIEW, không tự trừ điểm. |
| SC_InvalidConclusion (user) | BC | Thiếu | Có thể nhập 0 điểm/lý do nhưng không có nút/kết luận “minh chứng không hợp lệ” và lịch sử quyết định riêng. |
| SC_MergeReview (XOR merge) | BC; bcs.py /complete-review | Khớp | Hợp dòng sau kiểm tra; không cần CTA riêng. |
| SC_Decision (service) | BC; score_decision_service.py và workflow_service.py | Thiếu | Có gợi ý theo luật và tính tổng khi BCS hoàn tất, nhưng chưa gắn quyết định minh chứng tường minh vào điểm dự kiến/căn cứ theo đúng thứ tự BPMN. |
| SC_Draft (service) | BC, BS; PROPOSED | Khớp | Lưu proposed_total khi hoàn tất review. |
| PST_End (end) | BL, BS; PROPOSED | Khớp | Case hoàn tất trước họp/công bố. |
| Gateway_13j85dv (XOR merge) | BC; AI error hoặc proof timeout → BCS_REVIEW | Khớp | Gateway mới không cần UI riêng; cả hai nhánh đều trở lại BCS. |
| Gateway_144bgxy (XOR merge) | SD; hết lượt INFO hoặc timeout → CLOSED_INCOMPLETE | Khớp | Gateway mới nhập hai nhánh đóng hồ sơ. |
| Gateway_0zn6mno (XOR merge) | SS; nộp đầu hoặc nộp bổ sung → kiểm tra đủ | Khớp | Một form dùng cho hai đầu vào, cần microcopy phân biệt. |

### 2.3. Họp, công bố, phản hồi và chốt điểm

| ID (loại) | UI / API/luật tương ứng | Trạng thái | Nhận xét đối soát |
|---|---|---|---|
| SC_MeetBCS (manual) | BS, MeetingRecordModal.tsx; bcs.py /meetings | Khớp | Ghi nhận cuộc họp, không số hóa việc họp thực tế. |
| SC_ReviewDraft (user) | BS, BC | Thiếu | BS chỉ xem bảng; BC khóa sửa khi PROPOSED. Không có thao tác BCS rà soát/chỉnh dự thảo sau họp trước công bố. |
| SC_ClassMeeting (manual) | BS, MeetingRecordModal.tsx | Khớp | Ghi nhận họp lớp. |
| SC_PublishDraft (user) | BS, CD; bcs.py /publish | Khớp | CTA công bố, xác nhận và backend chặn thiếu họp/case. |
| SC_RespPerStudent (multi-instance subprocess) | SR, SA, BA | Khớp | Phản hồi theo từng case. |
| P2_Start (start) | SR; PUBLISHED | Khớp | Mở khoảng phản hồi khi công bố. |
| SC_NotifyDraft (send) | SD/notifications, SR | Khớp | Thông báo điểm dự kiến. |
| SC_WaitAppeal (event gateway) | SR, SA; deadline_service.py | Khớp | Đồng ý, khiếu nại hoặc hết hạn. |
| SC_GetAccept (message catch) | SR; student.py /accept | Khớp | Ghi nhận lựa chọn. |
| P2_EndAccept (end) | SR; ACCEPTED | Khớp | Hiển thị đã đồng ý. |
| SC_GetAppeal (message catch) | SA; student.py /appeals | Khớp | Gửi lý do theo tiêu chí. |
| SC_AppealTimeout (timer catch) | SR; deadline_service.py | Khớp | Backend tự chuyển ACCEPTED_AUTO. |
| SC_AutoAccept (send) | SR/SD; deadline_service.py | Khớp | Có thông báo và trạng thái tự chấp nhận. |
| P2_EndAuto (end) | SR; ACCEPTED_AUTO | Khớp | Có trạng thái hoàn tất. |
| SC_HandleAppeal (user) | BA; bcs.py /appeals/.../resolve | Khớp | BCS xem lý do, tệp và nhập kết luận. |
| SC_GAdjust (XOR) | BA; KEEP/ADJUST | Khớp | Hai nhánh có radio và backend xử lý. |
| SC_Edit (user) | BA; trường điểm mới/lý do | Khớp | Có sửa điểm; nên tăng kiểm tra trước khi gửi. |
| SC_UpdateScore (service) | BA/SR; bcs.py /resolve | Khớp | Backend cập nhật proposed_total. |
| SC_ReplyAppeal (send) | SA/notifications; bcs.py | Khớp | Có phản hồi cho SV. |
| P2_EndReply (end) | SA; RESOLVED | Khớp | Kết quả giải trình hiển thị. |
| SC_RemindEventSub (event subprocess) | SD; deadline_service.py | Khớp | Nhắc trước hạn. |
| SC_Remind_Start (timer start) | SD; reminder_after_hours | Khớp | Timer theo cấu hình. |
| SC_GResponded (XOR) | SR/SA; backend chỉ chọn PUBLISHED | Khớp | Đã phản hồi không bị nhắc thừa. |
| SC_SendReminder (send) | SD/notifications | Khớp | Gửi nhắc khi chưa phản hồi. |
| SC_Remind_End (end) | SD | Khớp | Thông báo được ghi nhận. |
| SC_Remind_Skip (end) | SR/SA | Khớp | Không phát thông báo nếu đã phản hồi. |
| Gateway_0p1br5d (XOR merge) | BA; KEEP hoặc ADJUST → thông báo | Khớp | Điểm nhập nhánh mới không cần CTA riêng. |
| SC_Finalize (user) | BA; bcs.py /finalize | Thiếu | Có nút, nhưng UI chỉ chặn khi còn appeal OPEN; có thể cho bấm khi vẫn còn case PUBLISHED/chưa tự chấp nhận rồi backend mới báo lỗi. |
| SC_SendFinal (user) | BA → GF | Thiếu | Chưa có hành động “Gửi bảng điểm đã chốt cho GVCN” và bằng chứng đã gửi; GVCN chỉ tự xem/tải CSV. |
| SC_End (end) | GF; FINALIZED | Thiếu | Có quyền đọc kết quả cuối, chưa xác nhận bước bàn giao theo BPMN. |

### 2.4. Chức năng UI ngoài các node BPMN

| UI/chức năng | Trạng thái | Quyết định thiết kế |
|---|---|---|
| AC: tạo đợt, chọn template, nhập GPA, sửa cấu hình | Thừa | Là điều kiện chuẩn bị trước SC_Start; giữ, nhưng trình bày như luồng “Chuẩn bị đợt”, tránh trộn với luồng đang chấm. |
| PrintEvaluationFormModal.tsx tại SS, SR, BC | Thừa | Tác vụ in/đối chiếu hỗ trợ, giữ và ghi “bản in tham khảo”. |
| GF: tải CSV; BL/BS: tìm kiếm, lọc, phân trang | Thừa | Công cụ quản trị/tra cứu hợp lý, không phải nhánh BPMN. |
| BC: nút “Phân tích minh chứng” pilot | Thừa | Trigger thử nghiệm ngoài BPMN; giữ sau feature flag, giải thích rõ kết quả chỉ hỗ trợ BCS. |

## 3. Các điểm gãy nghiệp vụ và UX theo mức ưu tiên

| Mức | ID | Bằng chứng tĩnh | Tác động | Hướng xử lý trước khi code |
|---|---|---|---|---|
| High | H1 — Dữ liệu demo lọt vào UI quản trị live | AC khởi tạo campaign bằng staffStore.getCampaign() ở dòng 29; khi API trả mảng rỗng không xóa campaign ở dòng 95–101; khi tải template lỗi lại dựng template giả ở 109–130. | Quản trị có thể thấy đợt/mẫu giả như dữ liệu thật, hoặc bấm thao tác theo ID demo. | Tách nguồn demo/live; campaign = null khi chưa có dữ liệu, empty/error riêng; chỉ dùng fallback mock trong VITE_DEMO_MODE. |
| High | H2 — Quyết định minh chứng chưa tương ứng SC_BCSFlags/SC_GProofNeed | BC chỉ lưu approved_score và reason (dòng 190–247, 827–970); API review_claim cũng chỉ ghi điểm/lý do. BPMN cần ACCEPT, REQUEST_SUPPLEMENT, REJECT_ITEM; nhánh default hiện dẫn SC_InvalidConclusion. | Không có dấu vết BCS chấp nhận cờ sai, từ chối hay tạm giữ; điểm số bị dùng thay cho quyết định minh chứng. | Chốt hợp đồng quyết định, API/audit và panel BCS theo từng minh chứng; default không được ngầm suy ra “không hợp lệ” khi chưa chọn. |
| High | H3 — Không thể rà soát/chỉnh dự thảo đúng vị trí sau họp | BS ghi biên bản và công bố (dòng 68–129, 274–379); BC khóa input khi PROPOSED (dòng 862–965). Không có endpoint chỉnh nháp sau PROPOSED. | SC_ReviewDraft là user task nhưng chỉ có xem; phát hiện sai sau họp phải đi đường vòng hoặc không sửa được trước công bố. | Thiết kế bước “Rà soát dự thảo” có xác nhận, sửa có lý do, phiên bản và audit; thống nhất lại thứ tự họp BCS → rà soát → họp lớp → công bố. |
| High | H4 — Thiếu bàn giao bảng điểm cho GVCN | BA chỉ finalize ở dòng 116–133; GF chỉ GET CSV sau FINALIZED. | SC_SendFinal/SC_End thiếu hành động và bằng chứng đã giao. | Chốt cách gửi (thông báo trong app + snapshot/link CSV hay xác nhận nhận); bổ sung trạng thái bàn giao và CTA theo API. |
| High | H5 — Banner toàn cục báo “dữ liệu minh họa/AI chưa kích hoạt” bất kể môi trường | L hiển thị demo-banner vô điều kiện ở dòng 17–30. | Người dùng production có thể hiểu sai tính thật của dữ liệu và trạng thái AI. | Chỉ hiện banner demo khi VITE_DEMO_MODE; trạng thái AI phải đọc cờ thực, diễn đạt theo từng tính năng. |
| Medium | M1 — CTA chốt điểm báo có thể bấm quá sớm | BA tính canFinalize chỉ từ openAppeals.length === 0 và !isFinalized (dòng 70–71); backend còn yêu cầu campaign PUBLISHED và tất cả case ACCEPTED/ACCEPTED_AUTO/RESOLVED/CLOSED. | Nút mở xác nhận rồi API trả 422/409, gây hụt hẫng. | Lấy readiness và lý do chặn từ backend; hiện danh sách case còn chờ, không suy từ appeal list. |
| Medium | M2 — Cảnh báo thiếu minh chứng biến mất khỏi bước xác nhận | SS đặt feedback info ở dòng 304–309, nhưng CD có message cố định ở 677–680 và handleConfirmSubmit xóa feedback ở 320. | SV có thể nộp thiếu tệp, bị chuyển NEEDS_INFO mà không đọc cảnh báo ngay tại quyết định cuối. | Đưa danh sách tiêu chí thiếu vào hộp xác nhận; CTA và phản hồi sau nộp dùng màu/câu chữ “Đã tiếp nhận, cần bổ sung” thay vì danger. |
| Medium | M3 — Cảnh báo cho BCS chưa có inbox riêng | EA_SendAlert yêu cầu thông báo; BC có thẻ AI, BD/BL có hàng chờ nhưng không thấy nguồn alertPending hay danh sách cảnh báo đã gửi/đã đọc. | Cờ AI có thể bị bỏ qua nếu BCS không mở từng case. | Thiết kế hàng đợi “Cần xem do AI/luật”, số chưa xử lý, lý do và deep link tới minh chứng. Giữ AI tắt cho đến khi pilot đạt. |
| Medium | M4 — Hạn phản hồi không tự cập nhật CTA trên màn đang mở | SR/SA so Date.now() khi render, không thấy timer làm mới parent; backend vẫn chặn quá hạn. | Sau đúng giờ hết hạn, nút có thể còn sáng cho đến lần render tiếp. | Countdown theo server time hoặc refresh khi đến hạn; xử lý DEADLINE_EXPIRED bằng tải lại và chuyển sang ACCEPTED_AUTO khi tick xong. |
| Medium | M5 — Empty/error ở quản trị và GVCN chưa tách rõ | AC không có trạng thái không có đợt; GF trả lỗi nếu chưa có campaign, trước FINALIZED có pending state. | Người dùng khó phân biệt chưa mở đợt với lỗi hệ thống. | State machine rõ empty/pending/error/success/partial cho từng trang; CTA phù hợp vai trò. |
| Medium | M6 — Modal và nhãn form thiếu ngữ nghĩa hỗ trợ bàn phím | CD là div nổi, chưa có role=dialog, aria-modal, focus trap, Escape; LoginPage label chưa gắn htmlFor; nhiều input BC/BA chỉ có placeholder hoặc label rời. | Điều hướng bàn phím/đọc màn hình khó, đặc biệt ở xác nhận nộp/công bố/chốt. | Sửa modal chung, liên kết label-id, aria-describedby lỗi ngay cạnh trường, focus đầu/lúc đóng. |
| Low | L1 — Microcopy kỹ thuật và dữ liệu cố định | BS dòng 158 hiện “Lớp: LOP-DEMO”; nhiều màn lộ NEEDS_INFO, PROPOSED, PUBLISHED trong câu thông báo. | Sản phẩm trông như bản thử, người dùng phải hiểu mã nội bộ. | Dùng tên lớp từ API và nhãn tiếng Việt; giữ mã chỉ trong chi tiết kỹ thuật. |
| Low | L2 — Phân cấp thị giác thiếu nhất quán | BC gần 1.000 dòng, ba vùng dài, chữ 0.7–0.85rem; nhiều màu/khoảng cách inline thay cho tokens.css; AC hơn 1.000 dòng. | Khó quét tác vụ chính và khó giữ nhất quán khi thay UI. | Ưu tiên vùng quyết định hiện tại, dồn thông tin thứ cấp vào disclosure/tab; trích component theo nghiệp vụ sau khi khóa hợp đồng trạng thái. |

**Lưu ý diễn giải v7:** Gateway_13j85dv đã gom lỗi AI và proof timeout về BCS; không còn được mô tả “quá hạn minh chứng → tự từ chối”. SC_GValid có nhánh tự duyệt theo ngưỡng, nhưng hiện tắt là chủ đích an toàn trong pilot, không phải lý do để bật AI khi chưa có đánh giá trên hồ sơ thật. SC_GProofNeed vẫn có default sang SC_InvalidConclusion; cần làm rõ trường hợp không chọn quyết định, HOLD và hết lượt trước khi nối UI.

## 4. Kiểm toán năm trạng thái UI

Ký hiệu: Có = có render rõ; Một phần = có nhưng trộn với trạng thái khác/thiếu hướng xử lý; Thiếu = chưa thấy trong mã trang. “Partial” nghĩa là dữ liệu hoặc nghiệp vụ mới hoàn thành một phần (chờ bổ sung, chờ AI, chờ phản hồi, lỗi một bước nhưng vẫn thao tác thủ công), không phải lỗi mạng.

| Màn hình | Empty | Loading/Pending | Error | Success/Ideal | Partial | Hành động UX ưu tiên |
|---|---|---|---|---|---|---|
| LoginPage | Không áp dụng | Có | Có | Có (redirect) | Không áp dụng | Gắn label-id, lỗi có role alert. |
| SD | Một phần: chỉ empty thông báo; thiếu “chưa có đợt” | Có | Có | Có | Có theo case status | Tách không có đợt khỏi lỗi API. |
| SS | Một phần: không có case thành lỗi | Có | Có | Có | Có NEEDS_INFO/NEEDS_PROOF | Cảnh báo thiếu minh chứng trong xác nhận. |
| SR | Có trạng thái chưa công bố | Có | Có | Có | Có ACCEPTED/APPEALED/RESOLVED | Làm mới CTA theo hạn thật. |
| SA | Có khi chưa thể khiếu nại | Có | Có | Có | Có OPEN/RESOLVED | Hạn, nhãn lỗi theo tiêu chí. |
| BD | Một phần: không có đợt thành lỗi | Có | Có | Có | Có số lượng công việc | Empty “chưa có đợt”; alert BCS. |
| BL | Có khi lọc rỗng | Có | Có | Có | Có trạng thái case | Phân biệt không có hồ sơ và không khớp bộ lọc. |
| BC | Có khi không có minh chứng | Có | Có | Có | Có AI queued/running/stale/fail, luật NOT_CONFIGURED | Gom AI/rule/BCS thành quyết định rõ trên mỗi minh chứng. |
| BS | Có khi bảng lọc rỗng | Có | Có | Có | Một phần: chỉ nêu điều kiện công bố | Bước rà soát draft và readiness theo chuỗi. |
| BA | Có khi không có appeal | Có | Có | Có | Có OPEN/RESOLVED | Readiness chốt toàn lớp từ backend. |
| AC | Thiếu khi API trả mảng rỗng | Một phần: cờ loading, trang demo vẫn render | Một phần: lỗi và campaign giả cùng hiển thị | Có | Thiếu | Tách live/demo, empty/error trước khi cho thao tác. |
| GF | Một phần: thiếu đợt thành lỗi | Có | Có | Có khi FINALIZED | Có trạng thái chờ chốt | Nêu rõ chưa được BCS gửi/chưa chốt. |

### Phân cấp, biểu mẫu và CTA

1. **Thứ bậc hành động:** SS có “Lưu nháp”, “Nộp” ở cuối; SR có “Khiếu nại/Đồng ý”; BC có “Yêu cầu bổ sung/Hoàn tất”. Cấu trúc cơ bản đúng, nhưng BC cần đưa quyết định cho minh chứng bị gắn cờ lên trước ô điểm. BS cần thêm bước rà soát trước CTA công bố; BA cần readiness trước CTA chốt.
2. **Biểu mẫu:** AdminCampaigns.tsx và BcsCaseDetail.tsx chứa nhiều khối điều kiện/inline style, khó duy trì thứ tự đọc. Điểm số nên có inputMode decimal, nhãn liên kết, giới hạn/mức điểm hiển thị sát ô, lỗi ngay dưới ô thay vì chỉ banner đầu trang. Không dùng lựa chọn mức điểm để tự sinh lý do kết luận chung chung khi có cờ AI; BCS phải nêu căn cứ thật.
3. **Microcopy:** “Đã tiếp nhận nhưng cần bổ sung” là trạng thái một phần, không phải thất bại; “AI gắn cờ” là yêu cầu xem xét, không phải xác nhận giả. Không hiển thị mã trạng thái kỹ thuật thay cho lời hướng dẫn. Khi CTA bị khóa, nêu điều kiện và bước tiếp theo bằng văn bản cạnh nút, không chỉ title hover.
4. **Visual system:** tokens.css có token cơ bản và nút/badge; nhiều trang vẫn dùng kích thước, màu, bố cục inline. Trước khi tái cấu trúc nên định nghĩa token spacing, typography, semantic color và component phản hồi chung. Đây là nhận xét mã nguồn, chưa phải đánh giá ảnh chụp màn hình ở các kích thước.

## 5. Kế hoạch can thiệp từng file, chưa thực thi

### P0 — Khóa ngữ nghĩa dữ liệu và nhánh nghiệp vụ

| File sẽ can thiệp | Thay đổi cụ thể | Phụ thuộc/hợp đồng cần chốt | Tiêu chí nghiệm thu |
|---|---|---|---|
| web/src/pages/admin/AdminCampaigns.tsx | Khởi tạo null ở live; render loading, empty, error tách biệt; xóa fallback template demo khi live; chặn CTA khi chưa có campaign thật. | api/app/routes/admin.py trả mảng rỗng và lỗi có mã rõ. | API rỗng không hiện đợt/mẫu giả, không gửi request bằng ID demo. |
| web/src/components/AppLayout.tsx | Banner theo VITE_DEMO_MODE và trạng thái từng tính năng; chỉ hiện dữ liệu minh họa trong demo. | Cấu hình env frontend/backend thống nhất. | Production không có banner sai; pilot AI được ghi rõ là hỗ trợ thử nghiệm. |
| web/src/pages/bcs/BcsCaseDetail.tsx | Thêm quyết định minh chứng từng mục: chấp nhận, yêu cầu bổ sung, từ chối có lý do, tạm giữ; đặt căn cứ AI/luật và tệp gốc cạnh quyết định; tách “đã xem” và “đã chốt”; không suy từ score=0. | Cần mở rộng api/app/routes/bcs.py, schema/audit và dịch vụ workflow cho reviewDecision. Xác nhận sửa default của SC_GProofNeed trong BPMN nếu có HOLD. | Mỗi cờ có quyết định BCS có thể truy vết; không hoàn tất khi cờ chưa xử lý. |
| web/src/components/staff/SupplementRequestModal.tsx | Hiện lượt còn lại, hạn sẽ cấp, tiêu chí và loại yêu cầu; nếu hết lượt thì chỉ dẫn quay về BCS kết luận trên dữ liệu hiện có. | bcs.py trả giới hạn/hạn hiện hành. | Không tạo vòng lặp vô hạn; quá hạn PROOF không tự kết luận sai. |
| web/src/pages/bcs/BcsScores.tsx | Thêm bước rà soát bảng điểm sau họp BCS với số mục cần quyết định, xác nhận, sửa có lý do; chỉ cho ghi họp lớp/công bố sau khi rà soát xong; thay “LOP-DEMO”. | Backend cần hợp đồng phiên bản dự thảo, edit/audit sau PROPOSED và readiness theo đợt. | Theo đúng SC_MeetBCS → SC_ReviewDraft → SC_ClassMeeting → SC_PublishDraft. |
| web/src/pages/bcs/BcsAppeals.tsx | Dùng can_finalize/reasons từ backend, không suy chỉ từ openAppeals; hiển thị SV còn chờ phản hồi và trạng thái campaign; thêm bước bàn giao GVCN sau chốt. | bcs.py/workflow_service.py cần readiness + endpoint/sự kiện handoff idempotent. | CTA chỉ mở khi backend sẵn sàng; có bằng chứng gửi cho GVCN. |
| web/src/pages/gvcn/GvcnFinalScores.tsx | Phân biệt chưa chốt, đã chốt nhưng chưa bàn giao, đã nhận; giữ tải CSV là công cụ xem. | API GVCN trả handoff timestamp/receipt. | GVCN biết bản nào được BCS gửi, lúc nào. |

### P1 — Làm rõ trạng thái và form

| File sẽ can thiệp | Thay đổi cụ thể | Tiêu chí nghiệm thu |
|---|---|---|
| web/src/pages/student/StudentSubmission.tsx | Đưa danh sách minh chứng thiếu vào CD; hiển thị luồng NEEDS_INFO/NEEDS_PROOF với hạn và lượt còn; phản hồi “đã tiếp nhận, cần bổ sung”. | SV biết chính xác thiếu gì trước nút cuối; không có thông báo success/danger mâu thuẫn. |
| web/src/pages/student/StudentResult.tsx; StudentAppeal.tsx | Cập nhật deadline khi màn đang mở, disable CTA đúng hạn, tải lại sau DEADLINE_EXPIRED/CASE_CHANGED. | Không còn nút sáng sau hạn; lỗi chuyển thành hướng dẫn rõ. |
| web/src/pages/student/StudentDashboard.tsx; web/src/pages/bcs/BcsDashboard.tsx; web/src/pages/bcs/BcsCases.tsx | Empty theo nghĩa “chưa có đợt”, “không có hồ sơ”, “lọc không thấy”; BCS thêm hàng đợi cờ AI/luật và số chưa xử lý. | Không dùng lỗi API cho empty; BCS vào đúng hồ sơ từ cảnh báo. |
| web/src/pages/bcs/BcsCaseDetail.tsx; web/src/api/types.ts | Biểu diễn AI unreadable, schema error, FLAGGED, UNKNOWN, stale, rate limited khác nhau; hiển thị đầu ra có dẫn nguồn và nhắc BCS phải kết luận. | Mỗi trạng thái có CTA thủ công phù hợp, không tự duyệt. |
| web/src/pages/admin/AdminCampaigns.tsx; web/src/pages/bcs/BcsAppeals.tsx; web/src/components/student/CriterionCard.tsx | Lỗi nhập sát trường, kiểm tra score theo mức và quy tắc, nhãn tiếng Việt, mô tả vì sao CTA disabled. | Người dùng sửa được lỗi ngay tại nơi nhập; backend vẫn là nguồn kiểm tra cuối. |

### P2 — Hệ thiết kế và khả năng truy cập

| File sẽ can thiệp | Thay đổi cụ thể | Tiêu chí nghiệm thu |
|---|---|---|
| web/src/components/ConfirmDialog.tsx; web/src/components/staff/MeetingRecordModal.tsx; SupplementRequestModal.tsx | role=dialog, aria-modal, focus trap, Escape, trả focus về CTA, mô tả hành động không thể hoàn tác. | Dùng bàn phím và trình đọc màn hình hoàn tất modal. |
| web/src/pages/LoginPage.tsx; web/src/pages/bcs/BcsCaseDetail.tsx; BcsAppeals.tsx | htmlFor/id, aria-describedby, role=alert/status; số điểm có nhãn và đơn vị rõ. | Input được đọc đúng tên và lỗi. |
| web/src/styles/tokens.css; web/src/components/StatusBadge.tsx; web/src/components/student/studentStyles.css | Token chữ/khoảng cách/màu theo nghĩa, component empty/loading/error/partial; chuẩn hóa text size tối thiểu và responsive. | Các màn chính có cùng hệ ưu tiên và trạng thái, không dựa màu đơn lẻ. |
| web/src/App.tsx; web/src/components/AppLayout.tsx | Nếu bước rà soát/bàn giao cần trang riêng thì thêm route/điều hướng theo role; giữ ProtectedRoute. | Không có route trống hoặc CTA dẫn sai vai trò. |

### Hợp đồng API/BPMN phải xác nhận trước khi giao AI code

1. BCS reviewDecision có những giá trị nào, ý nghĩa HOLD và hết lượt; sửa default SC_GProofNeed sang chờ quyết định rõ thay vì tự hiểu là không hợp lệ.
2. Có cho BCS sửa dự thảo sau PROPOSED không, ai được sửa, phiên bản snapshot/audit và giới hạn trước khi công bố.
3. “Gửi bảng điểm cho GVCN” là thông báo trong app, bản CSV cố định, hay xác nhận nhận; cần bằng chứng gửi/nhận.
4. Nguồn readiness cho publish/finalize và danh sách lý do chặn từ server; frontend chỉ hiển thị, không tự suy hết điều kiện nghiệp vụ.
5. AI pilot vẫn có feature flag; không kích hoạt tự duyệt hoặc gọi Gemini LIVE trong công việc UX này.

## 6. Thứ tự triển khai sau khi duyệt kế hoạch

1. Chốt hợp đồng nghiệp vụ/BPMN ở 5 điểm trên; lưu bản BPMN chuẩn vào kho dự án.
2. Làm P0 theo tuyến quản trị → BCS xem cờ và chốt điểm → họp/rà soát/công bố → chốt/bàn giao; mỗi bước có trạng thái API rõ.
3. Làm P1 cho sinh viên, alert BCS và các trạng thái một phần.
4. Làm P2 UI chung và accessibility, sau đó kiểm thử luồng theo vai trò.

Các ca kiểm thử tối thiểu cho lần triển khai: API không có campaign không hiện demo; nộp thiếu minh chứng có xác nhận đúng; INFO hết lượt đóng hồ sơ; PROOF hết hạn quay BCS; AI lỗi/UNKNOWN vẫn cho BCS quyết định; cờ được BCS ACCEPT/REQUEST/REJECT/HOLD; họp và rà soát đúng thứ tự; công bố chỉ khi đủ điều kiện; sinh viên phản hồi đúng hạn; khi hết hạn không gửi tiếp; finalize chỉ khi mọi case sẵn sàng; GVCN nhận đúng bản cuối. Đây là kế hoạch kiểm thử tương lai, không phải kết quả đã chạy trong lượt khảo sát.
