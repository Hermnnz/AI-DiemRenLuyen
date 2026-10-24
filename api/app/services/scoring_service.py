from decimal import Decimal, InvalidOperation
from typing import Optional, List, Union
from api.app.schemas.common import AppError


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


def sum_scores(scores: List[Optional[Decimal]]) -> Decimal:
    total = Decimal("0.00")
    for s in scores:
        if s is not None:
            total += s
    return total.quantize(Decimal("0.01"))
