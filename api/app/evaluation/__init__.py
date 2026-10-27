"""Evaluation pilot framework for AI_Read and AI_Transparency."""

from api.app.evaluation.schemas import (
    TestCase,
    EvaluationDataset,
    CaseEvaluationResult,
    AllowlistedCaseReport,
    EvaluationReport,
    ExpectedRead,
    ExpectedFact,
    ExpectedTransparency,
)
from api.app.evaluation.runner import EvaluationRunner, get_criterion_context
from api.app.evaluation.metrics import (
    compute_aggregate_metrics,
    evaluate_read_step,
    evaluate_transparency_step,
    match_fact,
    verify_citation,
)
from api.app.evaluation.reporter import (
    format_terminal_report,
    format_safe_validation_error,
    save_json_report,
)

__all__ = [
    "TestCase",
    "EvaluationDataset",
    "CaseEvaluationResult",
    "AllowlistedCaseReport",
    "EvaluationReport",
    "ExpectedRead",
    "ExpectedFact",
    "ExpectedTransparency",
    "EvaluationRunner",
    "get_criterion_context",
    "compute_aggregate_metrics",
    "evaluate_read_step",
    "evaluate_transparency_step",
    "match_fact",
    "verify_citation",
    "format_terminal_report",
    "format_safe_validation_error",
    "save_json_report",
]
