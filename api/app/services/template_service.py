from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from api.app.models.entities import EvaluationTemplate, TemplateCriterion, Criterion, Campaign, Claim


TEMPLATE_LEGACY_DEMO_CODE = "LEGACY_DEMO"
TEMPLATE_49K14_1_CODE = "49K14_1_V1"

# Xếp loại tham khảo theo sheet Parameters
RATING_THRESHOLDS = [
    (Decimal("90.00"), "Xuất sắc"),
    (Decimal("80.00"), "Tốt"),
    (Decimal("65.00"), "Khá"),
    (Decimal("50.00"), "Trung bình"),
    (Decimal("35.00"), "Yếu"),
    (Decimal("0.00"), "Kém"),
]

RATING_SOURCE_NOTE = (
    "Xếp loại tham khảo theo Mẫu Phiếu tự đánh giá KQRL của SV (Sheet Parameters); "
    "chưa phải quy chế xếp loại chính thức của Trường khi chưa có văn bản công nhận."
)


def get_rating_from_score(score: Optional[Decimal]) -> Optional[str]:
    if score is None:
        return None
    for threshold, label in RATING_THRESHOLDS:
        if score >= threshold:
            return label
    return "Kém"


CRITERIA_49K14_1_DEFINITIONS: List[Dict[str, Any]] = [
    # Điều 4 (Tối đa 20)
    {
        "code": "4a",
        "section_code": "DIEU_4",
        "section_title": "Điều 4. Đánh giá về ý thức tham gia học tập",
        "section_max_score": Decimal("20.00"),
        "title": "Ý thức và thái độ trong học tập",
        "description": "Đi học chuyên cần, đúng giờ, nghiêm túc; đủ điều kiện dự thi tất cả các học phần (Không đủ điều kiện 1 HP trừ 2đ, từ 2 HP trở lên trừ hết điểm).",
        "max_score": Decimal("4.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Đủ điều kiện dự thi tất cả các học phần", "score": "4.00"},
                {"label": "Không đủ điều kiện dự thi 01 học phần (bị trừ 2 điểm)", "score": "2.00"},
                {"label": "Không đủ điều kiện dự thi từ 02 học phần trở lên (bị trừ hết số điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 1,
    },
    {
        "code": "4b_nckh",
        "section_code": "DIEU_4",
        "section_title": "Điều 4. Đánh giá về ý thức tham gia học tập",
        "section_max_score": Decimal("20.00"),
        "title": "Nghiên cứu khoa học hoặc tham dự kỳ thi sinh viên giỏi các cấp",
        "description": "Đăng ký, thực hiện, báo cáo đề tài NCKH đúng tiến độ với khoa (1đ) hoặc tham dự kỳ thi sinh viên giỏi các cấp (2đ). Tối đa 2đ. Minh chứng giấy xác nhận có mộc đỏ, không chấp nhận ảnh Sheet/Form đăng ký.",
        "max_score": Decimal("2.00"),
        "requires_evidence": True,
        "evidence_notes": "Bắt buộc giấy xác nhận có mộc đỏ, thời gian phù hợp kỳ đánh giá. Không chấp nhận ảnh Sheet/Form đăng ký.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không tham gia", "score": "0.00"},
                {"label": "Đăng ký, thực hiện, báo cáo đề tài NCKH đúng tiến độ với khoa (1.00 điểm)", "score": "1.00"},
                {"label": "Tham dự kỳ thi sinh viên giỏi các cấp (2.00 điểm)", "score": "2.00"},
            ],
        },
        "sort_order": 2,
    },
    {
        "code": "4b_clb",
        "section_code": "DIEU_4",
        "section_title": "Điều 4. Đánh giá về ý thức tham gia học tập",
        "section_max_score": Decimal("20.00"),
        "title": "Tham gia câu lạc bộ học thuật, hoạt động học thuật, ngoại khóa",
        "description": "Ý thức tham gia các CLB học thuật, hoạt động học thuật, hoạt động ngoại khóa (phải có minh chứng). Tối đa 2đ.",
        "max_score": Decimal("2.00"),
        "requires_evidence": True,
        "evidence_notes": "Phải là các CLB học thuật, hoạt động học thuật hoặc hoạt động ngoại khóa có minh chứng.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không tham gia (0.00 điểm)", "score": "0.00"},
                {"label": "Có tham gia CLB/hoạt động học thuật, ngoại khóa (2.00 điểm)", "score": "2.00"},
            ],
        },
        "sort_order": 3,
    },
    {
        "code": "4c",
        "section_code": "DIEU_4",
        "section_title": "Điều 4. Đánh giá về ý thức tham gia học tập",
        "section_max_score": Decimal("20.00"),
        "title": "Ý thức và thái độ trong kỳ thi, kiểm tra đánh giá các học phần",
        "description": "Không vi phạm quy chế thi và kiểm tra (Vi phạm 1 lần trừ 2đ, từ lần 2 trở đi trừ hết số điểm).",
        "max_score": Decimal("6.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không vi phạm quy chế thi (6.00 điểm)", "score": "6.00"},
                {"label": "Vi phạm quy chế thi 01 lần (bị trừ 2 điểm, còn 4.00 điểm)", "score": "4.00"},
                {"label": "Vi phạm quy chế thi từ 02 lần trở lên (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 4,
    },
    {
        "code": "4d",
        "section_code": "DIEU_4",
        "section_title": "Điều 4. Đánh giá về ý thức tham gia học tập",
        "section_max_score": Decimal("20.00"),
        "title": "Tinh thần vượt khó, phấn đấu vươn lên trong học tập",
        "description": "Được tập thể lớp công nhận có tinh thần vượt khó, phấn đấu vươn lên trong học tập.",
        "max_score": Decimal("2.00"),
        "requires_evidence": False,
        "evidence_notes": "Biên bản họp lớp hoặc giấy tờ hoàn cảnh vượt khó.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Được tập thể lớp công nhận (2.00 điểm)", "score": "2.00"},
                {"label": "Không được công nhận (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 5,
    },
    {
        "code": "4e",
        "section_code": "DIEU_4",
        "section_title": "Điều 4. Đánh giá về ý thức tham gia học tập",
        "section_max_score": Decimal("20.00"),
        "title": "Kết quả học tập (TBCHK quy đổi)",
        "description": "Sinh viên không được tự điền. Hệ thống của Trường sẽ tự động quy đổi và cộng điểm: TBCHK 3.20 - 4.00: 4đ; 2.00 - 3.19: 2đ; dưới 2.00: 0đ.",
        "max_score": Decimal("4.00"),
        "requires_evidence": False,
        "evidence_notes": "Do Hệ thống Đào tạo hoặc Quản trị viên import/quy đổi chính thức.",
        "allowed_input_roles": ["SYSTEM", "ADMIN"],
        "rule_config": {
            "type": "GPA_CONVERSION",
            "thresholds": [
                {"min_gpa": "3.20", "max_gpa": "4.00", "score": "4.00"},
                {"min_gpa": "2.00", "max_gpa": "3.199", "score": "2.00"},
                {"min_gpa": "0.00", "max_gpa": "1.999", "score": "0.00"},
            ],
        },
        "sort_order": 6,
    },
    # Điều 5 (Tối đa 25)
    {
        "code": "5a1",
        "section_code": "DIEU_5",
        "section_title": "Điều 5. Đánh giá về ý thức chấp hành nội quy, quy chế, quy định trong nhà trường",
        "section_max_score": Decimal("25.00"),
        "title": "Chấp hành các văn bản chỉ đạo của ngành, cấp trên và ĐHĐN",
        "description": "Ý thức chấp hành văn bản chỉ đạo trong nhà trường (Vi phạm 1 lần trừ 2đ, từ lần 2 trở đi trừ hết số điểm).",
        "max_score": Decimal("6.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Chấp hành tốt, không vi phạm (6.00 điểm)", "score": "6.00"},
                {"label": "Vi phạm 01 lần (bị trừ 2 điểm, còn 4.00 điểm)", "score": "4.00"},
                {"label": "Vi phạm từ 02 lần trở lên (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 7,
    },
    {
        "code": "5a2",
        "section_code": "DIEU_5",
        "section_title": "Điều 5. Đánh giá về ý thức chấp hành nội quy, quy chế, quy định trong nhà trường",
        "section_max_score": Decimal("25.00"),
        "title": "Tham gia các cuộc vận động, sinh hoạt chính trị",
        "description": "Tham gia đầy đủ, đạt yêu cầu các cuộc vận động, sinh hoạt chính trị (Không tham gia 1 lần hoặc vi phạm trừ 2đ, từ lần 2 trừ hết).",
        "max_score": Decimal("4.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Tham gia đầy đủ, đạt yêu cầu (4.00 điểm)", "score": "4.00"},
                {"label": "Không tham gia 01 lần hoặc vi phạm quy định (còn 2.00 điểm)", "score": "2.00"},
                {"label": "Vi phạm từ 02 lần trở lên hoặc không tham gia (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 8,
    },
    {
        "code": "5b1",
        "section_code": "DIEU_5",
        "section_title": "Điều 5. Đánh giá về ý thức chấp hành nội quy, quy chế, quy định trong nhà trường",
        "section_max_score": Decimal("25.00"),
        "title": "Chấp hành nội quy, quy chế và các quy định của nhà trường",
        "description": "Chấp hành nội quy, quy định nhà trường: Không vi phạm: 10đ; Vi phạm 1 lần: 8đ; Vi phạm 2 lần: 6đ; Vi phạm từ 3 lần: 0đ.",
        "max_score": Decimal("10.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không vi phạm (10.00 điểm)", "score": "10.00"},
                {"label": "Vi phạm 01 lần (bị trừ 2 điểm, còn 8.00 điểm)", "score": "8.00"},
                {"label": "Vi phạm 02 lần (bị trừ 4 điểm, còn 6.00 điểm)", "score": "6.00"},
                {"label": "Vi phạm từ 03 lần trở lên (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 9,
    },
    {
        "code": "5b2",
        "section_code": "DIEU_5",
        "section_title": "Điều 5. Đánh giá về ý thức chấp hành nội quy, quy chế, quy định trong nhà trường",
        "section_max_score": Decimal("25.00"),
        "title": "Chấp hành quy định về đóng học phí",
        "description": "Đóng học phí đầy đủ, đúng hạn: 5đ; Không đóng học phí hoặc đóng trễ hạn không phép: 0đ.",
        "max_score": Decimal("5.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Đóng học phí đầy đủ, đúng hạn (5.00 điểm)", "score": "5.00"},
                {"label": "Không đóng học phí hoặc đóng trễ hạn không phép (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 10,
    },
    # Điều 6 (Tối đa 20)
    {
        "code": "6a1",
        "section_code": "DIEU_6",
        "section_title": "Điều 6. Đánh giá về ý thức tham gia các hoạt động rèn luyện về chính trị, xã hội, văn hóa, văn nghệ, thể thao, phòng chống tội phạm và các tệ nạn xã hội",
        "section_max_score": Decimal("20.00"),
        "title": "Tham gia Tuần sinh hoạt công dân sinh viên",
        "description": "Tham gia đầy đủ, đạt yêu cầu: 10đ; Vắng không phép 1 lần: 8đ; Kết quả không đạt phải học lại: 6đ; Không tham gia: 0đ.",
        "max_score": Decimal("10.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Tham gia đầy đủ, đạt yêu cầu (10.00 điểm)", "score": "10.00"},
                {"label": "Vắng 01 lần không phép (bị trừ 2 điểm, còn 8.00 điểm)", "score": "8.00"},
                {"label": "Tham gia nhưng không đạt, phải học lại (còn 6.00 điểm)", "score": "6.00"},
                {"label": "Không tham gia, phải học lại (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 11,
    },
    {
        "code": "6a2",
        "section_code": "DIEU_6",
        "section_title": "Điều 6. Đánh giá về ý thức tham gia các hoạt động rèn luyện về chính trị, xã hội, văn hóa, văn nghệ, thể thao, phòng chống tội phạm và các tệ nạn xã hội",
        "section_max_score": Decimal("20.00"),
        "title": "Hoạt động CT-XH-VH-VN-TT do Trường và ĐHĐN điều động",
        "description": "Tham gia đầy đủ nghiêm túc: 6đ; Vắng 1 lần: 4đ; Vắng 2 lần: 2đ; Vắng từ 3 lần: 0đ.",
        "max_score": Decimal("6.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Tham gia đầy đủ, nghiêm túc (6.00 điểm)", "score": "6.00"},
                {"label": "Vắng 01 lần không phép (bị trừ 2 điểm, còn 4.00 điểm)", "score": "4.00"},
                {"label": "Vắng 02 lần không phép (bị trừ 4 điểm, còn 2.00 điểm)", "score": "2.00"},
                {"label": "Vắng từ 03 lần trở lên (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 12,
    },
    {
        "code": "6b",
        "section_code": "DIEU_6",
        "section_title": "Điều 6. Đánh giá về ý thức tham gia các hoạt động rèn luyện về chính trị, xã hội, văn hóa, văn nghệ, thể thao, phòng chống tội phạm và các tệ nạn xã hội",
        "section_max_score": Decimal("20.00"),
        "title": "Hoạt động công ích, tình nguyện, CTXH TRONG NHÀ TRƯỜNG",
        "description": "Tham gia hoạt động TRONG TRƯỜNG: 1đ/lần, tối đa 2đ. Bài Share KHÔNG được tính. Bắt buộc minh chứng có dấu mộc, chữ ký.",
        "max_score": Decimal("2.00"),
        "requires_evidence": True,
        "evidence_notes": "Hoạt động TRONG TRƯỜNG, bắt buộc mộc đỏ, chữ ký. Bài Share không tính. 1đ/lần, tối đa 2đ.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không tham gia (0.00 điểm)", "score": "0.00"},
                {"label": "Tham gia 01 lần hoạt động trong trường (1.00 điểm)", "score": "1.00"},
                {"label": "Tham gia từ 02 lần trở lên trong trường (2.00 điểm)", "score": "2.00"},
            ],
        },
        "sort_order": 13,
    },
    {
        "code": "6c",
        "section_code": "DIEU_6",
        "section_title": "Điều 6. Đánh giá về ý thức tham gia các hoạt động rèn luyện về chính trị, xã hội, văn hóa, văn nghệ, thể thao, phòng chống tội phạm và các tệ nạn xã hội",
        "section_max_score": Decimal("20.00"),
        "title": "Tuyên truyền, phòng chống tội phạm và tệ nạn XH TRONG TRƯỜNG",
        "description": "Hoạt động TRONG TRƯỜNG: 1đ/lần, tối đa 2đ. Minh chứng là bài share ATGT/pháp luật Trường/Đoàn trường hoặc thi tìm hiểu pháp luật có điểm ngoại khóa.",
        "max_score": Decimal("2.00"),
        "requires_evidence": True,
        "evidence_notes": "Hoạt động TRONG TRƯỜNG. Bài share hợp lệ của Trường/Đoàn trường hoặc thi tìm hiểu pháp luật được điểm ngoại khóa.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không tham gia (0.00 điểm)", "score": "0.00"},
                {"label": "Tham gia 01 hoạt động/bài share hợp lệ trong trường (1.00 điểm)", "score": "1.00"},
                {"label": "Tham gia từ 02 hoạt động/bài share hợp lệ trong trường (2.00 điểm)", "score": "2.00"},
            ],
        },
        "sort_order": 14,
    },
    # Điều 7 (Tối đa 25)
    {
        "code": "7a1",
        "section_code": "DIEU_7",
        "section_title": "Điều 7. Ý thức công dân trong quan hệ cộng đồng",
        "section_max_score": Decimal("25.00"),
        "title": "Chấp hành, tuyên truyền chủ trương Đảng, chính sách pháp luật Nhà nước",
        "description": "Ý thức chấp hành, tham gia tuyên truyền (Vi phạm 1 lần trừ 2đ, từ lần 2 trừ hết số điểm): Không vi phạm: 4đ, 1 lần: 2đ, >=2 lần: 0đ.",
        "max_score": Decimal("4.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Chấp hành tốt, không vi phạm (4.00 điểm)", "score": "4.00"},
                {"label": "Vi phạm 01 lần (bị trừ 2 điểm, còn 2.00 điểm)", "score": "2.00"},
                {"label": "Vi phạm từ 02 lần trở lên (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 15,
    },
    {
        "code": "7a2",
        "section_code": "DIEU_7",
        "section_title": "Điều 7. Ý thức công dân trong quan hệ cộng đồng",
        "section_max_score": Decimal("25.00"),
        "title": "Tham gia Bảo hiểm y tế (bắt buộc) theo Luật BHYT",
        "description": "Có tham gia BHYT: 10đ; Không tham gia BHYT (bị trừ 10 điểm): 0đ.",
        "max_score": Decimal("10.00"),
        "requires_evidence": False,
        "evidence_notes": "Thẻ BHYT hoặc ảnh ứng dụng VssID.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Có tham gia Bảo hiểm y tế bắt buộc (10.00 điểm)", "score": "10.00"},
                {"label": "Không tham gia Bảo hiểm y tế (bị trừ 10 điểm, còn 0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 16,
    },
    {
        "code": "7a3",
        "section_code": "DIEU_7",
        "section_title": "Điều 7. Ý thức công dân trong quan hệ cộng đồng",
        "section_max_score": Decimal("25.00"),
        "title": "Chấp hành quy định về an toàn giao thông và văn hóa giao thông",
        "description": "Không vi phạm: 5đ; Vi phạm 1 lần: 3đ (trừ 2đ); Vi phạm từ lần 2 trở đi: 0đ.",
        "max_score": Decimal("5.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Chấp hành tốt, không vi phạm an toàn giao thông (5.00 điểm)", "score": "5.00"},
                {"label": "Vi phạm 01 lần (bị trừ 2 điểm, còn 3.00 điểm)", "score": "3.00"},
                {"label": "Vi phạm từ 02 lần trở lên (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 17,
    },
    {
        "code": "7b",
        "section_code": "DIEU_7",
        "section_title": "Điều 7. Ý thức công dân trong quan hệ cộng đồng",
        "section_max_score": Decimal("25.00"),
        "title": "Hoạt động xã hội BÊN NGOÀI TRƯỜNG có thành tích ghi nhận, biểu dương",
        "description": "Hoạt động NGOÀI TRƯỜNG. Khen thưởng: 4đ; Chứng nhận offline ngoài trường: 2đ/lần; Chứng nhận online (quyên góp): 1đ/lần. Tối đa 4đ.",
        "max_score": Decimal("4.00"),
        "requires_evidence": True,
        "evidence_notes": "Hoạt động NGOÀI TRƯỜNG. Chấp nhận giấy khen mộc đỏ hoặc giấy chứng nhận online/offline hợp lệ.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không tham gia (0.00 điểm)", "score": "0.00"},
                {"label": "01 Giấy chứng nhận online ngoài trường (1.00 điểm)", "score": "1.00"},
                {"label": "01 Chứng nhận offline hoặc 02 online ngoài trường (2.00 điểm)", "score": "2.00"},
                {"label": "01 offline + 01 online ngoài trường (3.00 điểm)", "score": "3.00"},
                {"label": "Có giấy khen, bằng khen biểu dương ngoài trường (4.00 điểm)", "score": "4.00"},
            ],
        },
        "sort_order": 18,
    },
    {
        "code": "7c",
        "section_code": "DIEU_7",
        "section_title": "Điều 7. Ý thức công dân trong quan hệ cộng đồng",
        "section_max_score": Decimal("25.00"),
        "title": "Tinh thần chia sẻ, giúp đỡ người gặp khó khăn, hoạn nạn",
        "description": "Có tinh thần chia sẻ, giúp đỡ người gặp khó khăn, hoạn nạn: Có: 2đ; Không: 0đ.",
        "max_score": Decimal("2.00"),
        "requires_evidence": False,
        "evidence_notes": "Minh chứng hoạt động cứu trợ, hiến máu hoặc xác nhận của lớp.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Có tham gia giúp đỡ, chia sẻ (2.00 điểm)", "score": "2.00"},
                {"label": "Không tham gia (0.00 điểm)", "score": "0.00"},
            ],
        },
        "sort_order": 19,
    },
    # Điều 8 (Tối đa 10)
    {
        "code": "8a",
        "section_code": "DIEU_8",
        "section_title": "Điều 8. Đánh giá về ý thức và kết quả khi tham gia công tác cán bộ lớp, các đoàn thể, tổ chức trong nhà trường hoặc sinh viên đạt được thành tích trong học tập, rèn luyện",
        "section_max_score": Decimal("10.00"),
        "title": "Quản lý lớp, tổ chức Đảng, Đoàn TN, Hội SV và tổ chức khác trong Trường",
        "description": "Sinh viên có thể tự khai; mọi điểm trên 0 phải được Ban cán sự xác minh chức vụ, đóng góp trong kỳ và chốt. Tối đa 3đ.",
        "max_score": Decimal("3.00"),
        "requires_evidence": False,
        "evidence_notes": "Nếu tự khai trên 0 điểm, Ban cán sự xác minh chức vụ và mức độ hoàn thành nhiệm vụ.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "mandatory_bcs_review_if_positive": True,
            "options": [
                {"label": "Không có chức vụ / không hoàn thành (0.00 điểm)", "score": "0.00"},
                {"label": "Hoàn thành nhiệm vụ quản lý mức cơ bản (1.00 điểm)", "score": "1.00"},
                {"label": "Hoàn thành tốt nhiệm vụ được giao (2.00 điểm)", "score": "2.00"},
                {"label": "Hoàn thành xuất sắc nhiệm vụ quản lý (3.00 điểm)", "score": "3.00"},
            ],
        },
        "sort_order": 20,
    },
    {
        "code": "8b",
        "section_code": "DIEU_8",
        "section_title": "Điều 8. Đánh giá về ý thức và kết quả khi tham gia công tác cán bộ lớp, các đoàn thể, tổ chức trong nhà trường hoặc sinh viên đạt được thành tích trong học tập, rèn luyện",
        "section_max_score": Decimal("10.00"),
        "title": "Kỹ năng tổ chức, quản lý lớp và các tổ chức trong trường",
        "description": "Sinh viên có thể tự khai; mọi điểm trên 0 phải được Ban cán sự xác minh kỹ năng và chốt. Tối đa 2đ.",
        "max_score": Decimal("2.00"),
        "requires_evidence": False,
        "evidence_notes": "Nếu tự khai trên 0 điểm, Ban cán sự xác minh chức vụ và kỹ năng tổ chức. Tối đa 2 điểm.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "mandatory_bcs_review_if_positive": True,
            "options": [
                {"label": "Không có chức vụ / không có kỹ năng tổ chức (0.00 điểm)", "score": "0.00"},
                {"label": "Có kỹ năng tổ chức mức đạt yêu cầu (1.00 điểm)", "score": "1.00"},
                {"label": "Có kỹ năng tổ chức, quản lý tốt (2.00 điểm)", "score": "2.00"},
            ],
        },
        "sort_order": 21,
    },
    {
        "code": "8c",
        "section_code": "DIEU_8",
        "section_title": "Điều 8. Đánh giá về ý thức và kết quả khi tham gia công tác cán bộ lớp, các đoàn thể, tổ chức trong nhà trường hoặc sinh viên đạt được thành tích trong học tập, rèn luyện",
        "section_max_score": Decimal("10.00"),
        "title": "Hỗ trợ và tham gia tích cực các hoạt động chung của Lớp, Khoa, Trường",
        "description": "Sinh viên có thể tự khai kèm minh chứng; mọi điểm trên 0 phải được Ban cán sự xác minh và chốt. Tối đa 3đ.",
        "max_score": Decimal("3.00"),
        "requires_evidence": True,
        "evidence_notes": "Bắt buộc minh chứng. Ban cán sự xác minh chức vụ và hoạt động hỗ trợ Lớp/Khoa/Trường.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "mandatory_bcs_review_if_positive": True,
            "options": [
                {"label": "Không tham gia (0.00 điểm)", "score": "0.00"},
                {"label": "Có hỗ trợ hoạt động chung của lớp/khoa (1.00 điểm)", "score": "1.00"},
                {"label": "Tham gia tích cực bên Khoa hoặc Đoàn trường (2.00 điểm)", "score": "2.00"},
                {"label": "Tham gia rất tích cực, chủ chốt (3.00 điểm)", "score": "3.00"},
            ],
        },
        "sort_order": 22,
    },
    {
        "code": "8d",
        "section_code": "DIEU_8",
        "section_title": "Điều 8. Đánh giá về ý thức và kết quả khi tham gia công tác cán bộ lớp, các đoàn thể, tổ chức trong nhà trường hoặc sinh viên đạt được thành tích trong học tập, rèn luyện",
        "section_max_score": Decimal("10.00"),
        "title": "Đạt được thành tích trong học tập, rèn luyện",
        "description": "Bằng khen, giấy khen, chứng nhận thành tích HỌC TẬP, RÈN LUYỆN (không tính ngoại khóa). Cấp khoa: 1đ; Cấp trường trở lên: 2đ. Tối đa 2đ.",
        "max_score": Decimal("2.00"),
        "requires_evidence": True,
        "evidence_notes": "Bắt buộc minh chứng mộc đỏ, chữ ký về thành tích học tập, rèn luyện (không tính ngoại khóa). Cấp khoa 1đ, cấp trường trở lên 2đ. Tối đa 2đ.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": {
            "type": "OPTIONS",
            "options": [
                {"label": "Không có thành tích (0.00 điểm)", "score": "0.00"},
                {"label": "Giấy khen, chứng nhận cấp Khoa (1.00 điểm)", "score": "1.00"},
                {"label": "Bằng khen, giấy khen cấp Trường trở lên (2.00 điểm)", "score": "2.00"},
            ],
        },
        "sort_order": 23,
    },
]


CRITERIA_LEGACY_DEMO_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "code": "TC01",
        "section_code": "MUC_1",
        "section_title": "Tiêu chí 1",
        "section_max_score": Decimal("10.00"),
        "title": "Ý thức tham gia học tập",
        "description": "Dữ liệu minh họa — không dùng để ra quyết định thật. Tối đa 10 điểm.",
        "max_score": Decimal("10.00"),
        "requires_evidence": True,
        "evidence_notes": "Minh chứng bảng điểm học tập.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": None,
        "sort_order": 1,
    },
    {
        "code": "TC02",
        "section_code": "MUC_2",
        "section_title": "Tiêu chí 2",
        "section_max_score": Decimal("10.00"),
        "title": "Ý thức chấp hành nội quy, quy chế",
        "description": "Dữ liệu minh họa — không dùng để ra quyết định thật. Tối đa 10 điểm.",
        "max_score": Decimal("10.00"),
        "requires_evidence": False,
        "evidence_notes": None,
        "allowed_input_roles": ["STUDENT"],
        "rule_config": None,
        "sort_order": 2,
    },
    {
        "code": "TC03",
        "section_code": "MUC_3",
        "section_title": "Tiêu chí 3",
        "section_max_score": Decimal("10.00"),
        "title": "Ý thức tham gia hoạt động phong trào",
        "description": "Dữ liệu minh họa — không dùng để ra quyết định thật. Tối đa 10 điểm.",
        "max_score": Decimal("10.00"),
        "requires_evidence": True,
        "evidence_notes": "Chứng nhận tham gia hoạt động phong trào.",
        "allowed_input_roles": ["STUDENT"],
        "rule_config": None,
        "sort_order": 3,
    },
]


def ensure_templates_seeded(db: Session) -> None:
    """Khởi tạo các mẫu quy tắc chấm (Idempotent)"""
    now = datetime.now(timezone.utc)

    # 1. Mẫu Legacy Demo
    legacy_tpl = db.query(EvaluationTemplate).filter(EvaluationTemplate.code == TEMPLATE_LEGACY_DEMO_CODE).first()
    if not legacy_tpl:
        legacy_tpl = EvaluationTemplate(
            code=TEMPLATE_LEGACY_DEMO_CODE,
            name="Mẫu minh họa cũ (3 tiêu chí, tối đa 30 điểm)",
            description="Mẫu thử nghiệm gồm 3 tiêu chí TC01 - TC03 minh họa.",
            version=1,
            total_max_score=Decimal("30.00"),
            is_active=True,
            created_at=now,
        )
        db.add(legacy_tpl)
        db.flush()

        for c_def in CRITERIA_LEGACY_DEMO_DEFINITIONS:
            crit = TemplateCriterion(
                template_id=legacy_tpl.id,
                code=c_def["code"],
                section_code=c_def["section_code"],
                section_title=c_def["section_title"],
                section_max_score=c_def["section_max_score"],
                title=c_def["title"],
                description=c_def["description"],
                max_score=c_def["max_score"],
                requires_evidence=c_def["requires_evidence"],
                evidence_notes=c_def.get("evidence_notes"),
                allowed_input_roles=c_def.get("allowed_input_roles"),
                rule_config=c_def.get("rule_config"),
                sort_order=c_def["sort_order"],
            )
            db.add(crit)

    # 2. Bộ quy tắc toàn trường; mã kỹ thuật cũ được giữ để không đổi tham chiếu.
    v1_tpl = db.query(EvaluationTemplate).filter(EvaluationTemplate.code == TEMPLATE_49K14_1_CODE).first()
    if not v1_tpl:
        v1_tpl = EvaluationTemplate(
            code=TEMPLATE_49K14_1_CODE,
            name="Bộ quy tắc toàn trường (5 Điều, 23 dòng, tối đa 100 điểm)",
            description="Bộ quy tắc điểm rèn luyện đã được duyệt áp dụng toàn trường; nguồn lập trình là tài liệu hướng dẫn và phiếu tự đánh giá (Điều 4 đến Điều 8).",
            version=1,
            total_max_score=Decimal("100.00"),
            is_active=True,
            created_at=now,
        )
        db.add(v1_tpl)
        db.flush()

        for c_def in CRITERIA_49K14_1_DEFINITIONS:
            crit = TemplateCriterion(
                template_id=v1_tpl.id,
                code=c_def["code"],
                section_code=c_def["section_code"],
                section_title=c_def["section_title"],
                section_max_score=c_def["section_max_score"],
                title=c_def["title"],
                description=c_def["description"],
                max_score=c_def["max_score"],
                requires_evidence=c_def["requires_evidence"],
                evidence_notes=c_def.get("evidence_notes"),
                allowed_input_roles=c_def.get("allowed_input_roles"),
                rule_config=c_def.get("rule_config"),
                sort_order=c_def["sort_order"],
            )
            db.add(crit)

    db.commit()


def convert_gpa_to_4e_score(gpa: Decimal) -> Decimal:
    """
    Quy đổi GPA học kỳ sang điểm tiêu chí 4e:
    - 3.20 <= GPA <= 4.00 -> 4.00 điểm
    - 2.00 <= GPA < 3.20  -> 2.00 điểm
    - GPA < 2.00          -> 0.00 điểm
    """
    if gpa >= Decimal("3.20"):
        return Decimal("4.00")
    elif gpa >= Decimal("2.00"):
        return Decimal("2.00")
    else:
        return Decimal("0.00")
