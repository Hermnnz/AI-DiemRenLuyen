from decimal import Decimal, InvalidOperation
from typing import Optional, List, Union, Dict, Any
from api.app.schemas.common import AppError


# Bảng mức điểm cho phép đối với mẫu 49K14.1 (None nghĩa là kiểm tra theo cận trên max_score)
EXACT_LEVELS_49K14_1: Dict[str, List[Decimal]] = {
    "4a": [Decimal("0.00"), Decimal("2.00"), Decimal("4.00")],
    "4b_nckh": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00")],
    "4b_clb": [Decimal("0.00"), Decimal("2.00")],
    "4c": [Decimal("0.00"), Decimal("4.00"), Decimal("6.00")],
    "4d": [Decimal("0.00"), Decimal("2.00")],
    "4e": [Decimal("0.00"), Decimal("2.00"), Decimal("4.00")],
    "5a1": [Decimal("0.00"), Decimal("4.00"), Decimal("6.00")],
    "5a2": [Decimal("0.00"), Decimal("2.00"), Decimal("4.00")],
    "5b1": [Decimal("0.00"), Decimal("6.00"), Decimal("8.00"), Decimal("10.00")],
    "5b2": [Decimal("0.00"), Decimal("5.00")],
    "6a1": [Decimal("0.00"), Decimal("6.00"), Decimal("8.00"), Decimal("10.00")],
    "6a2": [Decimal("0.00"), Decimal("2.00"), Decimal("4.00"), Decimal("6.00")],
    "6b": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00")],
    "6c": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00")],
    "7a1": [Decimal("0.00"), Decimal("2.00"), Decimal("4.00")],
    "7a2": [Decimal("0.00"), Decimal("10.00")],
    "7a3": [Decimal("0.00"), Decimal("3.00"), Decimal("5.00")],
    "7b": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00"), Decimal("3.00"), Decimal("4.00")],
    "7c": [Decimal("0.00"), Decimal("2.00")],
    "8a": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00"), Decimal("3.00")],
    "8b": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00")],  # Tuyệt đối không quá 2.00
    "8c": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00"), Decimal("3.00")],
    "8d": [Decimal("0.00"), Decimal("1.00"), Decimal("2.00")],
}


def parse_score(score_str: Optional[Union[str, Decimal, float, int]]) -> Optional[Decimal]:
    if score_str is None:
        return None
    try:
        val = Decimal(str(score_str))
        return val.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise AppError(
            status_code=422,
            code="INVALID_SCORE",
            message="Định dạng điểm không hợp lệ (phải là số thập phân tối đa 2 chữ số sau dấu phẩy).",
        )


def validate_score_bounds(
    score: Optional[Decimal],
    max_score: Union[Decimal, str, float, int],
    field_name: str = "score"
) -> None:
    if score is None:
        return
    max_dec = Decimal(str(max_score))
    if score < Decimal("0.00") or score > max_dec:
        raise AppError(
            status_code=422,
            code="SCORE_OUT_OF_BOUNDS",
            message=f"Điểm {score:.2f} không được nhỏ hơn 0 hoặc vượt quá điểm tối đa ({max_dec:.2f}).",
            fields={field_name: f"Giá trị hợp lệ từ 0.00 đến {max_dec:.2f}"}
        )


def validate_criterion_levels(criterion_code: str, score: Optional[Decimal]) -> None:
    """Kiểm tra điểm có thuộc mức điểm quy định trong tài liệu nguồn hay không"""
    if score is None:
        return
    score = score.quantize(Decimal("0.01"))

    # Đối với 8b: đặc biệt chặn không vượt quá 2.00
    if criterion_code == "8b" and score > Decimal("2.00"):
        raise AppError(
            status_code=422,
            code="SCORE_OUT_OF_BOUNDS",
            message="Mục 8b tối đa là 2.00 điểm. Không được vượt quá 2.00 điểm.",
            fields={"8b": "Tối đa 2.00 điểm"}
        )

    allowed_levels = EXACT_LEVELS_49K14_1.get(criterion_code)
    if allowed_levels is not None:
        if score not in allowed_levels:
            levels_str = ", ".join(f"{x:.2f}" for x in allowed_levels)
            raise AppError(
                status_code=422,
                code="INVALID_SCORE_LEVEL",
                message=f"Mức điểm {score:.2f} không hợp lệ cho tiêu chí {criterion_code}. Các mức điểm quy định: [{levels_str}].",
                fields={criterion_code: f"Mức điểm hợp lệ: {levels_str}"}
            )


def sum_scores(scores: List[Optional[Decimal]]) -> Decimal:
    total = Decimal("0.00")
    for s in scores:
        if s is not None:
            total += s
    return total.quantize(Decimal("0.01"))


def convert_gpa_to_score(gpa: Decimal) -> Decimal:
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


def get_rating(total_score: Optional[Decimal]) -> Optional[str]:
    """
    Xếp loại tham khảo theo Mẫu Phiếu tự đánh giá ĐRL (Sheet Parameters):
    - 90 - 100: Xuất sắc
    - 80 - 89.99: Tốt
    - 65 - 79.99: Khá
    - 50 - 64.99: Trung bình
    - 35 - 49.99: Yếu
    - Dưới 35: Kém
    """
    if total_score is None:
        return None
    if total_score >= Decimal("90.00"):
        return "Xuất sắc"
    elif total_score >= Decimal("80.00"):
        return "Tốt"
    elif total_score >= Decimal("65.00"):
        return "Khá"
    elif total_score >= Decimal("50.00"):
        return "Trung bình"
    elif total_score >= Decimal("35.00"):
        return "Yếu"
    else:
        return "Kém"
