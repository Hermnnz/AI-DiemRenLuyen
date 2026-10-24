from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ReviewResult(BaseModel):
    mode: str = "MANUAL"
    needs_human_review: bool = True
    findings: Optional[Dict[str, Any]] = None
    summary: str = "Chế độ kiểm tra thủ công — AI chưa kích hoạt."


class ReviewProvider(ABC):
    @abstractmethod
    def review(self, case_id: str) -> ReviewResult:
        """Đánh giá hồ sơ. Phiên bản V1 trả về kết quả yêu cầu người (BCS) xem xét thủ công."""
        pass


class ManualReviewProvider(ReviewProvider):
    def review(self, case_id: str) -> ReviewResult:
        return ReviewResult(
            mode="MANUAL",
            needs_human_review=True,
            findings=None,
            summary="Chế độ kiểm tra thủ công — Toàn bộ hồ sơ chuyển đến Ban cán sự xem xét."
        )
