"""Inclusive confidence gate shared by evidence acceptance and score suggestions."""

import math


def meets_confidence_threshold(value: object, threshold: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= threshold <= 1
        and threshold <= value <= 1
        and math.isfinite(value)
    )
