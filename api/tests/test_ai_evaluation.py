"""Unit tests for AI Pilot Evaluation framework (Stage F1).

Tests:
1. Fact normalization & matching modes (contains, exact, regex, page).
2. OCR Read step metrics (readability, precision, recall, missing facts, safe error codes).
3. "Bob" does NOT match "Alice Bob" (shorter extracted value must not match longer label).
4. OCR value evaluated strictly from `value`, NOT `source_excerpt`.
5. Transparency assessment metrics (verdict matching, false flags, missed flags).
6. Strict citation verification against AI_Read facts (simultaneous page, kind, value, excerpt matching; missing fields; fabricated value or excerpt; page 99).
7. Aggregate metrics & confusion matrix (accuracy, rates, zero division handling).
8. Security & Containment:
   - Path traversal containment (including .. and symlinks).
   - Pre-read file type & size checks (unsupported extension, empty file, oversized file).
   - Strict rule template and criterion rejection (NO generic fallback).
   - Mandatory positive limit on --live mode.
9. Privacy & Anti-Leakage:
   - Safe error formatting on malformed labels file (zero canary leakage).
   - Safe surrogate case IDs by order (zero canary leakage from user case.id).
   - Canary string verification across JSON report and terminal output.
10. Clear MOCK disclaimers and label provenance.
"""

import asyncio
import json
import os
from pathlib import Path
import pytest

from api.app.evaluation.metrics import (
    compute_aggregate_metrics,
    evaluate_read_step,
    evaluate_transparency_step,
    match_fact,
    normalize_text,
    verify_citation,
)
from api.app.evaluation.reporter import (
    format_safe_validation_error,
    format_terminal_report,
    save_json_report,
)
from api.app.evaluation.runner import EvaluationRunner, get_criterion_context
from api.app.evaluation.schemas import (
    AllowlistedCaseReport,
    CaseEvaluationResult,
    CaseReadEvaluation,
    CaseTransparencyEvaluation,
    EvaluationDataset,
    EvaluationReport,
    ExpectedFact,
    ExpectedRead,
    ExpectedTransparency,
    TestCase,
)


def test_normalize_text():
    assert normalize_text("   Đoàn   TNCS   ") == "đoàn tncs"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


def test_match_fact_exact():
    exp = ExpectedFact(kind="recipient", value="SV-ANON-001", match_mode="exact")
    assert match_fact(exp, {"kind": "recipient", "value": "SV-ANON-001"}) is True
    assert match_fact(exp, {"kind": "recipient", "value": "  sv-anon-001  "}) is True
    assert match_fact(exp, {"kind": "recipient", "value": "Sinh viên SV-ANON-001"}) is False
    assert match_fact(exp, {"kind": "issuer", "value": "SV-ANON-001"}) is False


def test_match_fact_contains():
    exp = ExpectedFact(kind="activity_name", value="Mùa hè xanh", match_mode="contains")
    assert match_fact(exp, {"kind": "activity_name", "value": "Chiến dịch Tình nguyện Mùa hè xanh 2026"}) is True
    assert match_fact(exp, {"kind": "activity_name", "value": "Hiến máu tình nguyện"}) is False
    assert match_fact(exp, {
        "kind": "activity_name",
        "value": "Chiến dịch tình nguyện Mùa hè xanh cấp Trường",
        "source_excerpt": "Chiến dịch tình nguyện Mùa hè xanh cấp Trường"
    }) is True


def test_match_fact_bob_not_matching_alice_bob():
    # "Bob" (shorter extracted) MUST NOT match "Alice Bob" (longer expected label)
    exp_alice_bob = ExpectedFact(kind="recipient", value="Alice Bob", match_mode="contains")
    act_bob = {"kind": "recipient", "value": "Bob"}
    assert match_fact(exp_alice_bob, act_bob) is False

    # In exact mode, it also fails
    exp_alice_bob_exact = ExpectedFact(kind="recipient", value="Alice Bob", match_mode="exact")
    assert match_fact(exp_alice_bob_exact, act_bob) is False

    # Conversely, extracted "Alice Bob" DOES contain expected "Bob"
    exp_bob = ExpectedFact(kind="recipient", value="Bob", match_mode="contains")
    act_alice_bob = {"kind": "recipient", "value": "Alice Bob"}
    assert match_fact(exp_bob, act_alice_bob) is True


def test_match_fact_evaluates_only_value_not_excerpt():
    exp = ExpectedFact(kind="recipient", value="Alice Bob", match_mode="contains")
    # value is Different, only source_excerpt has Alice Bob
    extracted = {"kind": "recipient", "value": "Different Person", "source_excerpt": "Alice Bob was present"}
    assert match_fact(exp, extracted) is False


def test_match_fact_regex():
    exp = ExpectedFact(kind="reference_code", value=r"VOL-\d{4}-\d+", match_mode="regex")
    assert match_fact(exp, {"kind": "reference_code", "value": "Mã: VOL-2026-991"}) is True
    assert match_fact(exp, {"kind": "reference_code", "value": "Mã: ABC-2026-XYZ"}) is False


def test_match_fact_with_page_restriction():
    exp = ExpectedFact(kind="issuer", value="Đoàn trường", match_mode="contains", page=2)
    assert match_fact(exp, {"kind": "issuer", "value": "Đoàn trường", "page": 2}) is True
    assert match_fact(exp, {"kind": "issuer", "value": "Đoàn trường", "page": 1}) is False
    # Missing page in extracted fact when expected.page has a number -> MUST be False
    assert match_fact(exp, {"kind": "issuer", "value": "Đoàn trường", "page": None}) is False
    assert match_fact(exp, {"kind": "issuer", "value": "Đoàn trường"}) is False


def test_match_fact_page_requirements():
    exp_with_page = ExpectedFact(kind="recipient", value="Alice Bob", match_mode="exact", page=1)

    # 1. Extracted fact is missing page (None) -> MUST return False
    extracted_missing_page = {"kind": "recipient", "value": "Alice Bob", "page": None}
    assert match_fact(exp_with_page, extracted_missing_page) is False

    # Also if 'page' key is omitted completely -> MUST return False
    extracted_no_page_key = {"kind": "recipient", "value": "Alice Bob"}
    assert match_fact(exp_with_page, extracted_no_page_key) is False

    # 2. Extracted fact has wrong page (e.g. page 2 instead of 1) -> MUST return False
    extracted_wrong_page = {"kind": "recipient", "value": "Alice Bob", "page": 2}
    assert match_fact(exp_with_page, extracted_wrong_page) is False

    # 3. Extracted fact has correct page -> returns True
    extracted_correct_page = {"kind": "recipient", "value": "Alice Bob", "page": 1}
    assert match_fact(exp_with_page, extracted_correct_page) is True


def test_evaluate_read_step_success():
    expected = ExpectedRead(
        readable=True,
        expected_facts=[
            ExpectedFact(kind="recipient", value="SV-ANON-001"),
            ExpectedFact(kind="activity_name", value="Mùa hè xanh"),
            ExpectedFact(kind="event_date", value="15/08/2026"),
        ],
    )
    actual = {
        "readable": True,
        "facts": [
            {"kind": "recipient", "value": "SV-ANON-001", "page": 1, "source_excerpt": "SV-ANON-001"},
            {"kind": "activity_name", "value": "Chiến dịch Mùa hè xanh", "page": 1, "source_excerpt": "Mùa hè xanh"},
            {"kind": "issuer", "value": "Đoàn TNCS", "page": 1, "source_excerpt": "Đoàn TNCS"},
        ],
    }
    eval_res = evaluate_read_step(expected, actual, duration=1.25)
    assert eval_res.readable_match is True
    assert eval_res.expected_fact_count == 3
    assert eval_res.extracted_fact_count == 3
    assert eval_res.matched_fact_count == 2
    assert eval_res.precision == round(2 / 3, 4)
    assert eval_res.recall == round(2 / 3, 4)
    assert len(eval_res.missing_facts) == 1
    assert eval_res.missing_facts[0]["kind"] == "event_date"


def test_evaluate_read_step_safe_error():
    expected = ExpectedRead(
        readable=True,
        expected_facts=[ExpectedFact(kind="recipient", value="SV-ANON-001")],
    )
    eval_res = evaluate_read_step(expected, actual=None, duration=0.5, safe_error_code="MODEL_TIMEOUT")
    assert eval_res.readable_match is False
    assert eval_res.safe_error_code == "MODEL_TIMEOUT"
    assert eval_res.precision == 0.0
    assert eval_res.recall == 0.0
    assert len(eval_res.missing_facts) == 1


# ---------------------------------------------------------------------------
# Citation Verification Tests (Simultaneous Matching - Requirement 1)
# ---------------------------------------------------------------------------


def test_verify_citation_valid():
    read_facts = [
        {"kind": "activity_name", "value": "Hiến máu nhân đạo", "page": 1, "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"},
        {"kind": "recipient", "value": "SV-ANON-001", "page": 1, "source_excerpt": "Sinh viên SV-ANON-001"},
    ]
    # Valid citation matching simultaneously page, kind, value, source_excerpt
    cit = {"kind": "activity_name", "value": "Hiến máu nhân đạo", "page": 1, "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}
    assert verify_citation(cit, read_facts) is True


def test_verify_citation_simultaneous_and_missing_fields():
    read_facts = [
        {"kind": "activity_name", "value": "Hiến máu nhân đạo", "page": 1, "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"},
    ]

    # 1. Missing page
    assert verify_citation({"kind": "activity_name", "value": "Hiến máu nhân đạo", "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}, read_facts) is False

    # 2. Missing kind
    assert verify_citation({"page": 1, "value": "Hiến máu nhân đạo", "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}, read_facts) is False

    # 3. Missing value
    assert verify_citation({"page": 1, "kind": "activity_name", "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}, read_facts) is False

    # 4. Missing source_excerpt
    assert verify_citation({"page": 1, "kind": "activity_name", "value": "Hiến máu nhân đạo"}, read_facts) is False

    # 5. Fabricated value with valid excerpt
    assert verify_citation({"page": 1, "kind": "activity_name", "value": "HOAT_DONG_BIA_DAT", "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}, read_facts) is False

    # 6. Fabricated excerpt with valid value
    assert verify_citation({"page": 1, "kind": "activity_name", "value": "Hiến máu nhân đạo", "source_excerpt": "TRICH_DOAN_BIA_DAT"}, read_facts) is False

    # 7. Mismatched page (e.g. page 99)
    assert verify_citation({"page": 99, "kind": "activity_name", "value": "Hiến máu nhân đạo", "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}, read_facts) is False

    # 8. Mismatched kind
    assert verify_citation({"page": 1, "kind": "recipient", "value": "Hiến máu nhân đạo", "source_excerpt": "Ngày hội Hiến máu nhân đạo 2026"}, read_facts) is False


def test_verify_citation_rejects_single_character_or_short_fragments():
    read_facts = [
        {
            "kind": "recipient",
            "value": "Alice Bob",
            "page": 1,
            "source_excerpt": "Recipient: Alice Bob",
        }
    ]

    # 1. Reject single character fragments ("A" and "R") against ("Alice Bob" and "Recipient: Alice Bob")
    cit_fragment = {
        "page": 1,
        "kind": "recipient",
        "value": "A",
        "source_excerpt": "R",
    }
    assert verify_citation(cit_fragment, read_facts) is False

    # 2. Reject partial substrings that do not match fully
    cit_partial_val = {
        "page": 1,
        "kind": "recipient",
        "value": "Alice",
        "source_excerpt": "Recipient: Alice Bob",
    }
    assert verify_citation(cit_partial_val, read_facts) is False

    cit_partial_excerpt = {
        "page": 1,
        "kind": "recipient",
        "value": "Alice Bob",
        "source_excerpt": "Recipient",
    }
    assert verify_citation(cit_partial_excerpt, read_facts) is False

    # 3. Full match after whitespace / case normalization must pass
    cit_full = {
        "page": 1,
        "kind": "recipient",
        "value": "  Alice   Bob  ",
        "source_excerpt": "Recipient:   Alice   Bob",
    }
    assert verify_citation(cit_full, read_facts) is True


def test_evaluate_transparency_citation_integrity():
    expected = ExpectedTransparency(verdict="SUPPORTED")
    read_facts = [
        {"kind": "activity_name", "value": "Chiến dịch Mùa hè xanh", "page": 1, "source_excerpt": "Mùa hè xanh"},
    ]

    # Case 1: SUPPORTED but citations is empty -> valid_citations must be False
    res_empty = evaluate_transparency_step(
        expected,
        actual={"verdict": "SUPPORTED", "reason": "OK", "citations": []},
        read_facts=read_facts,
        duration=0.5,
    )
    assert res_empty.valid_citations is False
    assert res_empty.safe_citation_error == "MISSING_CITATIONS_FOR_SUPPORTED"

    # Case 2: Citation on page 99 -> valid_citations must be False
    res_p99 = evaluate_transparency_step(
        expected,
        actual={
            "verdict": "SUPPORTED",
            "reason": "OK",
            "citations": [{"page": 99, "kind": "activity_name", "value": "Mùa hè xanh", "source_excerpt": "Mùa hè xanh"}],
        },
        read_facts=read_facts,
        duration=0.5,
    )
    assert res_p99.valid_citations is False
    assert res_p99.safe_citation_error == "FABRICATED_OR_UNGROUNDED_CITATION"

    # Case 3: Citation with invented non-existent value -> valid_citations must be False
    res_fake_val = evaluate_transparency_step(
        expected,
        actual={
            "verdict": "SUPPORTED",
            "reason": "OK",
            "citations": [{"page": 1, "kind": "activity_name", "value": "GIA_TRI_BIA_123", "source_excerpt": "Mùa hè xanh"}],
        },
        read_facts=read_facts,
        duration=0.5,
    )
    assert res_fake_val.valid_citations is False
    assert res_fake_val.safe_citation_error == "FABRICATED_OR_UNGROUNDED_CITATION"

    # Case 4: Valid citation -> valid_citations is True
    res_valid = evaluate_transparency_step(
        expected,
        actual={
            "verdict": "SUPPORTED",
            "reason": "OK",
            "citations": [{"page": 1, "kind": "activity_name", "value": "Chiến dịch Mùa hè xanh", "source_excerpt": "Mùa hè xanh"}],
        },
        read_facts=read_facts,
        duration=0.5,
    )
    assert res_valid.valid_citations is True
    assert res_valid.safe_citation_error is None


# ---------------------------------------------------------------------------
# Aggregate Metrics & Rates Tests
# ---------------------------------------------------------------------------


def test_compute_aggregate_metrics():
    cases = [
        CaseEvaluationResult(
            case_id="CASE_001",
            file="REDACTED",
            criterion_code="7b",
            status="COMPLETED",
            total_duration_seconds=1.0,
            tokens={"prompt_tokens": 100, "candidate_tokens": 50, "total_tokens": 150},
            read=CaseReadEvaluation(
                readable_expected=True,
                readable_actual=True,
                readable_match=True,
                precision=1.0,
                recall=1.0,
                duration_seconds=0.4,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="SUPPORTED",
                verdict_actual="SUPPORTED",
                verdict_match=True,
                citation_count=2,
                duration_seconds=0.6,
            ),
        ),
        CaseEvaluationResult(
            case_id="CASE_002",
            file="REDACTED",
            criterion_code="7b",
            status="COMPLETED",
            total_duration_seconds=1.2,
            read=CaseReadEvaluation(
                readable_expected=True,
                readable_actual=True,
                readable_match=True,
                precision=0.5,
                recall=1.0,
                duration_seconds=0.5,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="SUPPORTED",
                verdict_actual="FLAGGED",
                verdict_match=False,
                is_false_flag=True,
                citation_count=1,
                duration_seconds=0.7,
            ),
        ),
        CaseEvaluationResult(
            case_id="CASE_003",
            file="REDACTED",
            criterion_code="4b_nckh",
            status="COMPLETED",
            total_duration_seconds=0.9,
            read=CaseReadEvaluation(
                readable_expected=True,
                readable_actual=True,
                readable_match=True,
                precision=1.0,
                recall=0.5,
                duration_seconds=0.4,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="FLAGGED",
                verdict_actual="SUPPORTED",
                verdict_match=False,
                is_missed_flag=True,
                citation_count=1,
                duration_seconds=0.5,
            ),
        ),
        CaseEvaluationResult(
            case_id="CASE_004",
            file="REDACTED",
            criterion_code="7b",
            status="COMPLETED",
            total_duration_seconds=0.8,
            read=CaseReadEvaluation(
                readable_expected=False,
                readable_actual=False,
                readable_match=True,
                precision=0.0,
                recall=1.0,
                duration_seconds=0.3,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="UNKNOWN",
                verdict_actual="UNKNOWN",
                verdict_match=True,
                citation_count=0,
                duration_seconds=0.5,
            ),
        ),
    ]

    metrics = compute_aggregate_metrics(cases)
    assert metrics.total_cases == 4
    assert metrics.successful_cases == 4
    assert metrics.failed_cases == 0

    assert metrics.exact_match_accuracy == 0.5
    assert metrics.false_flag_count == 1
    assert metrics.false_flag_rate == 0.5
    assert metrics.missed_flag_count == 1
    assert metrics.missed_flag_rate == 1.0

    cm = metrics.confusion_matrix.matrix
    assert cm["SUPPORTED"]["SUPPORTED"] == 1
    assert cm["SUPPORTED"]["FLAGGED"] == 1
    assert cm["FLAGGED"]["SUPPORTED"] == 1
    assert cm["UNKNOWN"]["UNKNOWN"] == 1

    assert metrics.total_prompt_tokens == 100
    assert metrics.total_tokens == 150
    assert metrics.latency_total_avg == round((1.0 + 1.2 + 0.9 + 0.8) / 4, 2)


def test_compute_aggregate_metrics_zero_division():
    empty_metrics = compute_aggregate_metrics([])
    assert empty_metrics.total_cases == 0
    assert empty_metrics.exact_match_accuracy == 0.0
    assert empty_metrics.false_flag_rate == 0.0
    assert empty_metrics.missed_flag_rate == 0.0


# ---------------------------------------------------------------------------
# Strict Rule Template & Criterion Rejection Tests
# ---------------------------------------------------------------------------


def test_get_criterion_context_strict():
    ctx_7b = get_criterion_context("7b", "49K14_1_V1")
    assert ctx_7b is not None
    assert ctx_7b["code"] == "7b"

    # Unapproved criterion MUST return None (NO generic fallback)
    assert get_criterion_context("NON_EXISTENT_CRITERION", "49K14_1_V1") is None

    # Unapproved template MUST return None
    assert get_criterion_context("7b", "UNAPPROVED_TEMPLATE_2026") is None


def test_runner_rejects_unapproved_criterion(tmp_path: Path):
    img_path = tmp_path / "valid.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    dataset = EvaluationDataset(
        template_code="49K14_1_V1",
        cases=[
            TestCase(
                id="TEST_BAD_CRITERION",
                file="valid.png",
                criterion_code="INVALID_CODE_999",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ],
    )
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))
    assert report.case_reports[0].status == "FAILED"
    assert report.case_reports[0].safe_error_code == "UNAPPROVED_CRITERION"


def test_runner_rejects_unapproved_template(tmp_path: Path):
    dataset = EvaluationDataset(
        template_code="UNAPPROVED_TEMPLATE_XYZ",
        cases=[
            TestCase(
                id="TEST_BAD_TEMPLATE",
                file="valid.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ],
    )
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))
    assert report.case_reports[0].status == "FAILED"
    assert report.case_reports[0].safe_error_code == "UNAPPROVED_TEMPLATE"


# ---------------------------------------------------------------------------
# Path Traversal & Symlink Security Tests
# ---------------------------------------------------------------------------


def test_runner_rejects_path_traversal(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "secret.png"
    secret_file.write_bytes(b"dummy")

    dataset = EvaluationDataset(
        cases=[
            TestCase(
                id="TEST_TRAVERSAL",
                file="../secret/secret.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ]
    )
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=dataset_dir))
    assert report.case_reports[0].status == "FAILED"
    assert report.case_reports[0].safe_error_code == "PATH_TRAVERSAL_DETECTED"


# ---------------------------------------------------------------------------
# File Type and Size Pre-check Tests
# ---------------------------------------------------------------------------


def test_runner_rejects_unsupported_file_type(tmp_path: Path):
    bad_file = tmp_path / "document.docx"
    bad_file.write_bytes(b"dummy docx bytes")

    dataset = EvaluationDataset(
        cases=[
            TestCase(
                id="TEST_BAD_TYPE",
                file="document.docx",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ]
    )
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))
    assert report.case_reports[0].status == "FAILED"
    assert report.case_reports[0].safe_error_code == "UNSUPPORTED_FILE_TYPE"


def test_runner_rejects_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")

    dataset = EvaluationDataset(
        cases=[
            TestCase(
                id="TEST_EMPTY",
                file="empty.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ]
    )
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))
    assert report.case_reports[0].status == "FAILED"
    assert report.case_reports[0].safe_error_code == "FILE_EMPTY"


def test_runner_rejects_oversized_file(tmp_path: Path, monkeypatch):
    large_file = tmp_path / "large.png"
    large_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    orig_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = orig_stat(self, *args, **kwargs)
        if self.name == "large.png":
            vals = list(st)
            vals[6] = 12 * 1024 * 1024  # 12 MB
            return os.stat_result(vals)
        return st

    monkeypatch.setattr(Path, "stat", mock_stat)

    dataset = EvaluationDataset(
        cases=[
            TestCase(
                id="TEST_OVERSIZED",
                file="large.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ]
    )
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))
    assert report.case_reports[0].status == "FAILED"
    assert report.case_reports[0].safe_error_code == "FILE_TOO_LARGE"


# ---------------------------------------------------------------------------
# Live Mode Limit Validation
# ---------------------------------------------------------------------------


def test_runner_live_requires_positive_limit():
    with pytest.raises(ValueError, match="Chế độ --live bắt buộc phải cấu hình limit là số nguyên dương"):
        EvaluationRunner(live=True, limit=None)

    with pytest.raises(ValueError, match="Chế độ --live bắt buộc phải cấu hình limit là số nguyên dương"):
        EvaluationRunner(live=True, limit=0)

    with pytest.raises(ValueError, match="Chế độ --live bắt buộc phải cấu hình limit là số nguyên dương"):
        EvaluationRunner(live=True, limit=-5)


# ---------------------------------------------------------------------------
# Canary Privacy Leakage Tests (Requirement 2 & Requirement 1)
# ---------------------------------------------------------------------------


def test_no_sensitive_leak_in_json_and_terminal(tmp_path: Path):
    canaries = [
        "CANARY_SECRET_FILE_PATH_ABC123.png",
        "CANARY_STUDENT_SECRET_NGUYEN_VAN_A",
        "CANARY_STUDENT_NOTE_SECRET_456",
        "CANARY_HUMAN_EVALUATOR_PRIVATE_OPINION_67890",
        "CANARY_FACT_VALUE_SECRET_AAA",
        "CANARY_EXCERPT_SECRET_BBB",
        "CANARY_FREE_FORM_AI_REASON_TEXT_CCC",
        "CANARY_STUDENT_NAME_INSIDE_USER_CASE_ID_999",
    ]

    img_path = tmp_path / "valid_image.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    dataset = EvaluationDataset(
        template_code="49K14_1_V1",
        dataset_source="SYNTHETIC_SCRIPT_GENERATED",
        human_verified=False,
        cases=[
            TestCase(
                id=canaries[7],  # Sensitive name in case_id
                file="valid_image.png",
                criterion_code="7b",
                student_name=canaries[1],
                student_note=canaries[2],
                expected_read=ExpectedRead(
                    readable=True,
                    expected_facts=[
                        ExpectedFact(kind="recipient", value=canaries[4]),
                    ],
                ),
                expected_transparency=ExpectedTransparency(
                    verdict="SUPPORTED",
                    notes=canaries[3],
                ),
            )
        ],
    )

    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))

    # 1. Check Terminal Output
    term_text = format_terminal_report(report)
    for canary in canaries:
        assert canary not in term_text, f"Leaked sensitive canary '{canary}' in terminal report!"

    # 2. Check Saved JSON Report
    json_path = tmp_path / "out_report.json"
    save_json_report(report, json_path)
    json_text = json_path.read_text(encoding="utf-8")
    for canary in canaries:
        assert canary not in json_text, f"Leaked sensitive canary '{canary}' in JSON report!"

    # 3. Verify safe surrogate case ID by order is generated
    assert report.case_reports[0].case_id == "CASE_001"
    assert "CASE_001" in json_text
    assert "7b" in json_text
    assert "SUPPORTED" in json_text
    assert "CHẾ ĐỘ MOCK" in json_text
    assert "KHÔNG PHẢI LÀ ĐỘ CHÍNH XÁC" in json_text
    assert "SYNTHETIC_SCRIPT_GENERATED" in json_text


def test_malformed_labels_file_canary_leakage():
    canary_secret = "CANARY_SECRET_IN_MALFORMED_LABEL_INPUT_777"
    raw_invalid_json = json.dumps({
        "version": "1.0.0",
        "cases": [
            {
                "id": "CASE_01",
                "file": "test.png",
                "criterion_code": "7b",
                # Pass invalid string where a dict/ExpectedRead model is required
                "expected_read": canary_secret,
                "expected_transparency": {"verdict": "SUPPORTED"}
            }
        ]
    })

    with pytest.raises(Exception) as exc_info:
        EvaluationDataset.model_validate_json(raw_invalid_json)

    safe_output = format_safe_validation_error(exc_info.value)
    # Canary string MUST NOT appear in formatted error
    assert canary_secret not in safe_output, "Raw input value leaked in validation error message!"
    # Safe error message MUST point to the safe field location
    assert "expected_read" in safe_output


def test_dataset_version_canary_leakage_prevention(tmp_path: Path):
    canary_version = "CANARY_STUDENT_FAKE_NAME_VERSION_NGUYEN_VAN_A"
    img_path = tmp_path / "valid.png"
    img_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    # 1. Test that arbitrary version containing fake student name is sanitized to SAFE_VERSION
    dataset_unsafe = EvaluationDataset(
        version=canary_version,
        template_code="49K14_1_V1",
        cases=[
            TestCase(
                id="CASE_TEST_01",
                file="valid.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ],
    )
    runner = EvaluationRunner(live=False)
    report_unsafe = asyncio.run(runner.run_dataset(dataset_unsafe, dataset_dir=tmp_path))

    # Assert dataset_version in report object is sanitized
    assert report_unsafe.dataset_version == "SAFE_VERSION"
    assert canary_version not in report_unsafe.dataset_version

    # Assert terminal output has zero canary leakage
    term_text = format_terminal_report(report_unsafe)
    assert canary_version not in term_text
    assert "SAFE_VERSION" in term_text

    # Assert saved JSON has zero canary leakage
    json_path = tmp_path / "report_version.json"
    save_json_report(report_unsafe, json_path)
    json_text = json_path.read_text(encoding="utf-8")
    assert canary_version not in json_text
    assert "SAFE_VERSION" in json_text

    # 2. Test that strict technical semver formats (e.g. 1.0.0, 2.1.0) are preserved
    dataset_valid = EvaluationDataset(
        version="1.0.0",
        template_code="49K14_1_V1",
        cases=[
            TestCase(
                id="CASE_TEST_02",
                file="valid.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True),
                expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
            )
        ],
    )
    report_valid = asyncio.run(runner.run_dataset(dataset_valid, dataset_dir=tmp_path))
    assert report_valid.dataset_version == "1.0.0"


# ---------------------------------------------------------------------------
# Stage F1.1: Rate limit short-circuit, Start-index slicing, and Unicode font tests
# ---------------------------------------------------------------------------


def test_rate_limit_stops_subsequent_cases(tmp_path: Path):
    img_path = tmp_path / "valid.png"
    img_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    cases = [
        TestCase(
            id="CASE_1",
            file="valid.png",
            criterion_code="7b",
            expected_read=ExpectedRead(readable=True),
            expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
        ),
        TestCase(
            id="CASE_2",
            file="valid.png",
            criterion_code="7b",
            expected_read=ExpectedRead(readable=True),
            expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
        ),
        TestCase(
            id="CASE_3",
            file="valid.png",
            criterion_code="7b",
            expected_read=ExpectedRead(readable=True),
            expected_transparency=ExpectedTransparency(verdict="FLAGGED"),
            simulate_error="429",  # Simulates Gemini HTTP 429 MODEL_RATE_LIMITED
        ),
        TestCase(
            id="CASE_4",
            file="valid.png",
            criterion_code="7b",
            expected_read=ExpectedRead(readable=True),
            expected_transparency=ExpectedTransparency(verdict="UNKNOWN"),
        ),
    ]

    dataset = EvaluationDataset(cases=cases)
    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))

    # Total cases reported is 4
    assert report.total_evaluated == 4
    assert len(report.case_reports) == 4

    # Case 1 & 2 completed successfully
    assert report.case_reports[0].case_id == "CASE_001"
    assert report.case_reports[0].status == "COMPLETED"
    assert report.case_reports[1].case_id == "CASE_002"
    assert report.case_reports[1].status == "COMPLETED"

    # Case 3 failed due to rate limit 429
    assert report.case_reports[2].case_id == "CASE_003"
    assert report.case_reports[2].status == "FAILED"
    assert report.case_reports[2].safe_error_code == "MODEL_RATE_LIMITED"

    # Case 4 MUST NOT be called; marked as SKIPPED with safe error code
    assert report.case_reports[3].case_id == "CASE_004"
    assert report.case_reports[3].status == "SKIPPED"
    assert report.case_reports[3].safe_error_code == "SKIPPED_DUE_TO_RATE_LIMIT"
    assert report.case_reports[3].total_duration_seconds == 0.0

    # Aggregate metrics
    summary = report.summary_metrics
    assert summary.successful_cases == 2
    assert summary.failed_cases == 1
    assert summary.skipped_cases == 1
    assert summary.api_errors.get("MODEL_RATE_LIMITED") == 1
    assert summary.api_errors.get("SKIPPED_DUE_TO_RATE_LIMIT") == 1

    # Terminal report output contains SKIPPED information
    term_text = format_terminal_report(report)
    assert "CASE_003" in term_text
    assert "MODEL_RATE_LIMITED" in term_text
    assert "LỖI" in term_text
    assert "CASE_004" in term_text
    assert "SKIPPED_DUE_TO_RATE_LIMIT" in term_text
    assert "BỎ QUA" in term_text

    # JSON representation has null for valid_citations on 429 and SKIPPED
    json_dict = report.model_dump()
    assert json_dict["case_reports"][2]["valid_citations"] is None
    assert json_dict["case_reports"][3]["valid_citations"] is None


def test_start_index_preserves_original_case_ids(tmp_path: Path):
    img_path = tmp_path / "valid.png"
    img_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    cases = [
        TestCase(
            id=f"CASE_{i}",
            file="valid.png",
            criterion_code="7b",
            expected_read=ExpectedRead(readable=True),
            expected_transparency=ExpectedTransparency(verdict="SUPPORTED"),
        )
        for i in range(1, 6)
    ]

    dataset = EvaluationDataset(cases=cases)

    # Run starting at index 3 with limit 2 (runs original cases 3 and 4)
    runner = EvaluationRunner(live=False, start_index=3, limit=2)
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir=tmp_path))

    assert report.total_evaluated == 2
    assert len(report.case_reports) == 2

    # Original case IDs MUST be preserved as CASE_003 and CASE_004
    assert report.case_reports[0].case_id == "CASE_003"
    assert report.case_reports[1].case_id == "CASE_004"

    # Terminal report must show CASE_003 and CASE_004
    term_text = format_terminal_report(report)
    assert "CASE_003" in term_text
    assert "CASE_004" in term_text
    assert "CASE_001" not in term_text
    assert "CASE_002" not in term_text
    assert "CASE_005" not in term_text


def test_vietnamese_font_rendering_quality():
    from PIL import Image, ImageDraw
    from api.data.pilot_evaluation.generate_dataset import get_font

    font = get_font(size=22, bold=True)
    sample_texts = [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Độc lập - Tự do - Hạnh phúc",
        "GIẤY CHỨNG NHẬN THAM GIA HOẠT ĐỘNG",
        "Đoàn TNCS Hồ Chí Minh — Đoàn Trường Đại học Kinh tế",
        "Chiến dịch Tình nguyện Mùa hè xanh 2026",
    ]

    im = Image.new("RGB", (800, 300), color="#ffffff")
    draw = ImageDraw.Draw(im)

    for idx, text in enumerate(sample_texts):
        bbox = draw.textbbox((10, 10 + idx * 40), text, font=font)
        # Width and height of rendered text bounding box must be positive
        assert bbox[2] > bbox[0]
        assert bbox[3] > bbox[1]
        draw.text((10, 10 + idx * 40), text, font=font, fill="#000000")


def test_dataset_v1_1_0_labels_and_authenticity_compliance():
    labels_path = Path("api/data/pilot_evaluation/labels.json")
    assert labels_path.is_file()

    content = labels_path.read_text(encoding="utf-8")
    dataset = EvaluationDataset.model_validate_json(content)

    assert dataset.version == "1.1.0"
    assert dataset.dataset_source == "SYNTHETIC_SCRIPT_GENERATED"
    assert dataset.human_verified is False

    for c in dataset.cases:
        # Script-generated synthetic documents must never be claimed as AUTHENTIC
        assert c.expected_transparency.authenticity != "AUTHENTIC", (
            f"Case {c.id} illegally claims authenticity='AUTHENTIC' for a synthetic script-drawn paper!"
        )

    # CASE_001 must be FLAGGED due to date/issuer outside-term considerations
    case_001 = dataset.cases[0]
    assert case_001.expected_transparency.verdict == "FLAGGED"
    assert case_001.expected_transparency.authenticity == "UNVERIFIED"

    # CASE_002 remains SUPPORTED
    case_002 = dataset.cases[1]
    assert case_002.expected_transparency.verdict == "SUPPORTED"
    assert case_002.expected_transparency.authenticity == "UNVERIFIED"


def test_operational_failure_separated_from_ai_conclusion_quality():
    """Test 4 cases: 2 COMPLETED (1 match, 1 mismatch), 1 FAILED due to 429, 1 SKIPPED.

    Expectations:
    - exact_match_accuracy on assessed cases with conclusions is 50.0% (1 / 2).
    - invalid_citation_cases is NOT increased by 429 (remains 0).
    - latency_total_avg excludes 0.0s of SKIPPED cases.
    - Operational errors correctly record MODEL_RATE_LIMITED and SKIPPED_DUE_TO_RATE_LIMIT.
    - Confusion matrix records the FAILED case under ERROR, not AI verdict columns.
    """
    cases = [
        # Case 1: COMPLETED - match
        CaseEvaluationResult(
            case_id="CASE_001",
            file="REDACTED",
            criterion_code="7b",
            status="COMPLETED",
            total_duration_seconds=1.0,
            read=CaseReadEvaluation(
                readable_expected=True,
                readable_actual=True,
                readable_match=True,
                precision=1.0,
                recall=1.0,
                duration_seconds=0.4,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="SUPPORTED",
                verdict_actual="SUPPORTED",
                verdict_match=True,
                citation_count=2,
                valid_citations=True,
                duration_seconds=0.6,
            ),
        ),
        # Case 2: COMPLETED - mismatch (false flag)
        CaseEvaluationResult(
            case_id="CASE_002",
            file="REDACTED",
            criterion_code="7b",
            status="COMPLETED",
            total_duration_seconds=1.2,
            read=CaseReadEvaluation(
                readable_expected=True,
                readable_actual=True,
                readable_match=True,
                precision=1.0,
                recall=1.0,
                duration_seconds=0.5,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="SUPPORTED",
                verdict_actual="FLAGGED",
                verdict_match=False,
                is_false_flag=True,
                citation_count=1,
                valid_citations=True,
                duration_seconds=0.7,
            ),
        ),
        # Case 3: FAILED due to HTTP 429 MODEL_RATE_LIMITED
        CaseEvaluationResult(
            case_id="CASE_003",
            file="REDACTED",
            criterion_code="7b",
            status="FAILED",
            safe_error_code="MODEL_RATE_LIMITED",
            total_duration_seconds=0.5,
            read=CaseReadEvaluation(
                readable_expected=True,
                readable_actual=None,
                readable_match=False,
                safe_error_code="MODEL_RATE_LIMITED",
                duration_seconds=0.5,
            ),
            transparency=CaseTransparencyEvaluation(
                verdict_expected="FLAGGED",
                verdict_actual=None,
                verdict_match=False,
                safe_error_code="MODEL_RATE_LIMITED",
                duration_seconds=0.0,
            ),
        ),
        # Case 4: SKIPPED (short-circuited after 429)
        CaseEvaluationResult(
            case_id="CASE_004",
            file="REDACTED",
            criterion_code="7b",
            status="SKIPPED",
            safe_error_code="SKIPPED_DUE_TO_RATE_LIMIT",
            total_duration_seconds=0.0,
            read=None,
            transparency=None,
        ),
    ]

    metrics = compute_aggregate_metrics(cases)

    # 1. Operational / Pipeline counts
    assert metrics.total_cases == 4
    assert metrics.successful_cases == 2
    assert metrics.failed_cases == 1
    assert metrics.skipped_cases == 1
    assert metrics.executed_cases == 3

    # 2. Denominators for transparency quality
    assert metrics.assessed_cases == 2
    assert metrics.human_supported_evaluated == 2
    assert metrics.human_flagged_evaluated == 0

    # 3. AI Conclusion Accuracy: 1 match out of 2 assessed cases = 50.0%
    assert metrics.exact_match_accuracy == 0.5
    assert metrics.false_flag_count == 1
    assert metrics.false_flag_rate == 0.5
    assert metrics.missed_flag_count == 0
    assert metrics.missed_flag_rate == 0.0

    # 4. Citations: Invalid citations NOT increased by 429 or SKIPPED
    assert metrics.invalid_citation_cases == 0
    assert metrics.avg_citations_per_case == 1.5  # (2 + 1) / 2 assessed cases

    # 5. Latency: Excludes 0.0s of SKIPPED case
    # Executed latencies: [1.0, 1.2, 0.5] -> avg = 2.7 / 3 = 0.9s
    assert metrics.latency_total_avg == 0.9
    assert metrics.latency_total_min == 0.5
    assert metrics.latency_total_max == 1.2

    # 6. Errors
    assert metrics.api_errors.get("MODEL_RATE_LIMITED") == 1
    assert metrics.api_errors.get("SKIPPED_DUE_TO_RATE_LIMIT") == 1

    # 7. Confusion matrix: FAILED case is in ERROR column, NOT AI verdict columns
    cm = metrics.confusion_matrix.matrix
    assert cm["SUPPORTED"]["SUPPORTED"] == 1
    assert cm["SUPPORTED"]["FLAGGED"] == 1
    assert cm["FLAGGED"]["ERROR"] == 1
    assert cm["FLAGGED"]["SUPPORTED"] == 0

    # 8. Per-case Allowlisted Reports, JSON representation & Terminal output
    allowlisted_reports = [c.to_allowlisted_report() for c in cases]

    # Check that FAILED and SKIPPED cases have valid_citations=None
    assert allowlisted_reports[0].valid_citations is True
    assert allowlisted_reports[1].valid_citations is True
    assert allowlisted_reports[2].valid_citations is None  # FAILED due to 429
    assert allowlisted_reports[3].valid_citations is None  # SKIPPED

    report = EvaluationReport(
        timestamp="2026-10-26T12:00:00Z",
        mode="MOCK",
        is_mock_simulation=True,
        disclaimer="MOCK",
        dataset_source="SYNTHETIC_SCRIPT_GENERATED",
        human_verified=False,
        model_read="gemini-3.5-flash-lite",
        model_transparency="gemini-3.6-flash",
        dataset_version="1.1.0",
        total_evaluated=4,
        summary_metrics=metrics,
        case_reports=allowlisted_reports,
    )

    # Check Terminal Output
    term_text = format_terminal_report(report)
    lines = term_text.splitlines()

    row_c1 = next(l for l in lines if "CASE_001" in l)
    row_c2 = next(l for l in lines if "CASE_002" in l)
    row_c3 = next(l for l in lines if "CASE_003" in l)
    row_c4 = next(l for l in lines if "CASE_004" in l)

    assert "ĐÚNG" in row_c1
    assert "SAI" in row_c2
    assert "LỖI" in row_c3  # FAILED displays LỖI, NOT SAI
    assert "BỎ QUA" in row_c4  # SKIPPED displays BỎ QUA

    # Check JSON output serialization
    report_dict = report.model_dump()
    json_str = json.dumps(report_dict)

    # In JSON, valid_citations must be null for CASE_003 and CASE_004
    assert report_dict["case_reports"][0]["valid_citations"] is True
    assert report_dict["case_reports"][1]["valid_citations"] is True
    assert report_dict["case_reports"][2]["valid_citations"] is None
    assert report_dict["case_reports"][3]["valid_citations"] is None
    assert '"valid_citations": null' in json_str


def test_post_processing_telemetry_and_verdict_sources():
    """Verify safe telemetry distinguishes model direct verdicts from system post-processing overrides."""
    # 1. Model Direct SUPPORTED
    res_direct_sup = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="SUPPORTED"),
        actual={
            "verdict": "SUPPORTED",
            "raw_verdict": "SUPPORTED",
            "post_processing_reason": None,
            "citations": [{"page": 1, "kind": "recipient", "value": "SV-ANON", "source_excerpt": "SV-ANON"}],
            "visual_signals": [],
        },
        read_facts=[{"page": 1, "kind": "recipient", "value": "SV-ANON", "source_excerpt": "SV-ANON"}],
        duration=0.5,
    )
    assert res_direct_sup.verdict_raw == "SUPPORTED"
    assert res_direct_sup.verdict_actual == "SUPPORTED"
    assert res_direct_sup.verdict_source == "MODEL_DIRECT"
    assert res_direct_sup.post_processing_reason is None

    # 2. System Override: SUPPORTED -> FLAGGED due to visual concern
    res_override_flag = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="FLAGGED"),
        actual={
            "verdict": "FLAGGED",
            "raw_verdict": "SUPPORTED",
            "post_processing_reason": "FLAGGED_DUE_TO_VISUAL_CONCERN",
            "citations": [{"page": 1, "kind": "recipient", "value": "SV-ANON", "source_excerpt": "SV-ANON"}],
            "visual_signals": [{"page": 1, "description": "Dấu hiệu tẩy xóa", "concern": True}],
        },
        read_facts=[{"page": 1, "kind": "recipient", "value": "SV-ANON", "source_excerpt": "SV-ANON"}],
        duration=0.6,
    )
    assert res_override_flag.verdict_raw == "SUPPORTED"
    assert res_override_flag.verdict_actual == "FLAGGED"
    assert res_override_flag.verdict_source == "SYSTEM_OVERRIDE"
    assert res_override_flag.post_processing_reason == "FLAGGED_DUE_TO_VISUAL_CONCERN"

    # 3. System Override: SUPPORTED -> UNKNOWN due to missing citations
    res_override_unknown_cit = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="UNKNOWN"),
        actual={
            "verdict": "UNKNOWN",
            "raw_verdict": "SUPPORTED",
            "post_processing_reason": "UNKNOWN_DUE_TO_MISSING_CITATIONS",
            "citations": [],
            "visual_signals": [],
        },
        read_facts=[],
        duration=0.4,
    )
    assert res_override_unknown_cit.verdict_raw == "SUPPORTED"
    assert res_override_unknown_cit.verdict_actual == "UNKNOWN"
    assert res_override_unknown_cit.verdict_source == "SYSTEM_OVERRIDE"
    assert res_override_unknown_cit.post_processing_reason == "UNKNOWN_DUE_TO_MISSING_CITATIONS"

    # 4. System Override: FLAGGED -> UNKNOWN due to lack of basis
    res_override_unknown_basis = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="UNKNOWN"),
        actual={
            "verdict": "UNKNOWN",
            "raw_verdict": "FLAGGED",
            "post_processing_reason": "UNKNOWN_DUE_TO_LACK_OF_BASIS",
            "citations": [],
            "visual_signals": [],
        },
        read_facts=[],
        duration=0.4,
    )
    assert res_override_unknown_basis.verdict_raw == "FLAGGED"
    assert res_override_unknown_basis.verdict_actual == "UNKNOWN"
    assert res_override_unknown_basis.verdict_source == "SYSTEM_OVERRIDE"
    assert res_override_unknown_basis.post_processing_reason == "UNKNOWN_DUE_TO_LACK_OF_BASIS"

    # 5. Model Direct FLAGGED
    res_direct_flag = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="FLAGGED"),
        actual={
            "verdict": "FLAGGED",
            "raw_verdict": "FLAGGED",
            "post_processing_reason": None,
            "citations": [{"page": 1, "kind": "recipient", "value": "SV-ANON", "source_excerpt": "SV-ANON"}],
            "visual_signals": [{"page": 1, "description": "Không hợp lệ", "concern": True}],
        },
        read_facts=[{"page": 1, "kind": "recipient", "value": "SV-ANON", "source_excerpt": "SV-ANON"}],
        duration=0.5,
    )
    assert res_direct_flag.verdict_raw == "FLAGGED"
    assert res_direct_flag.verdict_actual == "FLAGGED"
    assert res_direct_flag.verdict_source == "MODEL_DIRECT"
    assert res_direct_flag.post_processing_reason is None

    # 6. Model Direct UNKNOWN
    res_direct_unk = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="UNKNOWN"),
        actual={
            "verdict": "UNKNOWN",
            "raw_verdict": "UNKNOWN",
            "post_processing_reason": None,
            "citations": [],
            "visual_signals": [],
        },
        read_facts=[],
        duration=0.4,
    )
    assert res_direct_unk.verdict_raw == "UNKNOWN"
    assert res_direct_unk.verdict_actual == "UNKNOWN"
    assert res_direct_unk.verdict_source == "MODEL_DIRECT"
    assert res_direct_unk.post_processing_reason is None


def test_post_processing_terminal_table_and_metrics_breakdown():
    """Verify terminal report and aggregate metrics properly differentiate model vs system FLAGGED."""
    c1 = CaseEvaluationResult(
        case_id="CASE_001",
        file="REDACTED",
        criterion_code="7b",
        status="COMPLETED",
        total_duration_seconds=1.0,
        transparency=CaseTransparencyEvaluation(
            verdict_expected="FLAGGED",
            verdict_actual="FLAGGED",
            verdict_raw="FLAGGED",
            verdict_source="MODEL_DIRECT",
            post_processing_reason=None,
            verdict_match=True,
            citation_count=1,
            valid_citations=True,
            duration_seconds=0.5,
        ),
    )
    c2 = CaseEvaluationResult(
        case_id="CASE_002",
        file="REDACTED",
        criterion_code="7b",
        status="COMPLETED",
        total_duration_seconds=1.2,
        transparency=CaseTransparencyEvaluation(
            verdict_expected="FLAGGED",
            verdict_actual="FLAGGED",
            verdict_raw="SUPPORTED",
            verdict_source="SYSTEM_OVERRIDE",
            post_processing_reason="FLAGGED_DUE_TO_VISUAL_CONCERN",
            verdict_match=True,
            citation_count=1,
            valid_citations=True,
            duration_seconds=0.6,
        ),
    )
    c3 = CaseEvaluationResult(
        case_id="CASE_003",
        file="REDACTED",
        criterion_code="7b",
        status="COMPLETED",
        total_duration_seconds=0.9,
        transparency=CaseTransparencyEvaluation(
            verdict_expected="UNKNOWN",
            verdict_actual="UNKNOWN",
            verdict_raw="SUPPORTED",
            verdict_source="SYSTEM_OVERRIDE",
            post_processing_reason="UNKNOWN_DUE_TO_MISSING_CITATIONS",
            verdict_match=True,
            citation_count=0,
            valid_citations=True,
            duration_seconds=0.4,
        ),
    )

    metrics = compute_aggregate_metrics([c1, c2, c3])
    assert metrics.assessed_cases == 3
    assert metrics.exact_match_accuracy == 1.0
    assert metrics.model_flagged_count == 1
    assert metrics.system_flagged_count == 1
    assert metrics.system_unknown_count == 1

    report = EvaluationReport(
        timestamp="2026-10-27T12:00:00Z",
        mode="MOCK",
        is_mock_simulation=True,
        disclaimer="MOCK",
        dataset_source="SYNTHETIC_SCRIPT_GENERATED",
        human_verified=False,
        model_read="gemini-3.5-flash-lite",
        model_transparency="gemini-3.6-flash",
        dataset_version="1.1.0",
        total_evaluated=3,
        summary_metrics=metrics,
        case_reports=[c.to_allowlisted_report() for c in [c1, c2, c3]],
    )

    term_output = format_terminal_report(report)
    lines = term_output.splitlines()

    # Section 2 breakdown assertions
    assert any("Mô hình tự gắn: 1 ca" in l and "Hệ thống chuyển do visual concern: 1 ca" in l for l in lines)
    assert any("Ca chuyển UNKNOWN (Hệ thống):  1 ca" in l for l in lines)

    # Section 8 per-case rows
    row1 = next(l for l in lines if "CASE_001" in l)
    row2 = next(l for l in lines if "CASE_002" in l)
    row3 = next(l for l in lines if "CASE_003" in l)

    # CASE_001: Model direct FLAGGED
    assert "FLAGGED" in row1
    assert "MÔ HÌNH" in row1
    assert "NONE" in row1

    # CASE_002: System override to FLAGGED
    assert "SUPPORTED" in row2  # AI gốc
    assert "FLAGGED" in row2    # AI cuối
    assert "HỆ THỐNG" in row2
    assert "FLAGGED_DUE_TO_VISUAL_CONCERN" in row2

    # CASE_003: System override to UNKNOWN
    assert "SUPPORTED" in row3  # AI gốc
    assert "UNKNOWN" in row3    # AI cuối
    assert "HỆ THỐNG" in row3
    assert "UNKNOWN_DUE_TO_MISSING_CITATIONS" in row3


def test_canary_leak_protection_in_telemetry():
    """Verify that arbitrary strings, raw prompts, or PII injected into post-processing reason are filtered."""
    CANARY_PROMPT = "CANARY_SECRET_SYSTEM_PROMPT_KEY_9999"
    CANARY_NAME = "NGUYEN_VAN_CANARY_STUDENT"

    eval_step = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="SUPPORTED"),
        actual={
            "verdict": "SUPPORTED",
            "raw_verdict": "SUPPORTED",
            "post_processing_reason": CANARY_PROMPT,  # Injected arbitrary string
            "reason": CANARY_NAME,                     # Injected PII
            "citations": [],
            "visual_signals": [],
        },
        read_facts=[],
        duration=0.5,
    )

    # Sanitized to None because CANARY_PROMPT is not in ALLOWED_POST_PROCESSING_REASONS
    assert eval_step.post_processing_reason is None
    assert eval_step.verdict_source == "MODEL_DIRECT"

    case_res = CaseEvaluationResult(
        case_id="CASE_CANARY_001",
        file="REDACTED",
        criterion_code="7b",
        status="COMPLETED",
        total_duration_seconds=0.5,
        transparency=eval_step,
    )

    allowlisted = case_res.to_allowlisted_report()
    assert allowlisted.post_processing_reason is None

    rep = EvaluationReport(
        timestamp="2026-10-27T12:00:00Z",
        mode="MOCK",
        is_mock_simulation=True,
        disclaimer="MOCK",
        dataset_source="SYNTHETIC_SCRIPT_GENERATED",
        human_verified=False,
        model_read="gemini-3.5-flash-lite",
        model_transparency="gemini-3.6-flash",
        dataset_version="1.1.0",
        total_evaluated=1,
        summary_metrics=compute_aggregate_metrics([case_res]),
        case_reports=[allowlisted],
    )

    term_str = format_terminal_report(rep)
    json_str = json.dumps(rep.model_dump())

    # CANARY STRINGS MUST NOT APPEAR IN TERMINAL OR JSON
    assert CANARY_PROMPT not in term_str
    assert CANARY_PROMPT not in json_str
    assert CANARY_NAME not in term_str
    assert CANARY_NAME not in json_str


def test_evaluation_runner_simulated_override_branches(tmp_path):
    """Verify that EvaluationRunner handles mock override simulations correctly end-to-end."""
    # Create a small dataset with simulated override
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    img_file = evidence_dir / "test.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    ds = EvaluationDataset(
        version="1.0.0",
        template_code="49K14_1_V1",
        dataset_source="SYNTHETIC_SCRIPT_GENERATED",
        human_verified=False,
        cases=[
            TestCase(
                id="CASE_OVERRIDE_FLAG",
                file="evidence/test.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True, expected_facts=[]),
                expected_transparency=ExpectedTransparency(verdict="FLAGGED"),
                simulate_error="SIMULATE_VISUAL_CONCERN_OVERRIDE",
            ),
            TestCase(
                id="CASE_OVERRIDE_UNK",
                file="evidence/test.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True, expected_facts=[]),
                expected_transparency=ExpectedTransparency(verdict="UNKNOWN"),
                simulate_error="SIMULATE_NO_CITATIONS_OVERRIDE",
            ),
        ],
    )

    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(ds, dataset_dir=tmp_path))

    assert report.total_evaluated == 2
    assert report.summary_metrics.system_flagged_count == 1
    assert report.summary_metrics.system_unknown_count == 1

    c1 = report.case_reports[0]
    assert c1.verdict_raw == "SUPPORTED"
    assert c1.verdict_actual == "FLAGGED"
    assert c1.verdict_source == "SYSTEM_OVERRIDE"
    assert c1.post_processing_reason == "FLAGGED_DUE_TO_VISUAL_CONCERN"

    c2 = report.case_reports[1]
    assert c2.verdict_raw == "SUPPORTED"
    assert c2.verdict_actual == "UNKNOWN"
    assert c2.verdict_source == "SYSTEM_OVERRIDE"
    assert c2.post_processing_reason == "UNKNOWN_DUE_TO_MISSING_CITATIONS"


def test_simulate_visual_concern_override_citations_not_fabricated(tmp_path):
    """Verify SIMULATE_VISUAL_CONCERN_OVERRIDE only cites real facts in read_dict or leaves citations=[],
    and is never flagged as a fabricated citation.
    """
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    img_file = evidence_dir / "test.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    # Subcase A: Dataset has expected facts (which mock read extracts)
    ds = EvaluationDataset(
        version="1.0.0",
        template_code="49K14_1_V1",
        dataset_source="SYNTHETIC_SCRIPT_GENERATED",
        human_verified=False,
        cases=[
            TestCase(
                id="CASE_WITH_FACTS",
                file="evidence/test.png",
                criterion_code="7b",
                expected_read=ExpectedRead(
                    readable=True,
                    expected_facts=[
                        ExpectedFact(kind="activity_name", value="Hoạt động tình nguyện", page=1),
                        ExpectedFact(kind="recipient", value="SV-001", page=1),
                    ],
                ),
                expected_transparency=ExpectedTransparency(verdict="FLAGGED"),
                simulate_error="SIMULATE_VISUAL_CONCERN_OVERRIDE",
            ),
            # Subcase B: Dataset has no expected facts (citations should be empty [])
            TestCase(
                id="CASE_WITHOUT_FACTS",
                file="evidence/test.png",
                criterion_code="7b",
                expected_read=ExpectedRead(readable=True, expected_facts=[]),
                expected_transparency=ExpectedTransparency(verdict="FLAGGED"),
                simulate_error="SIMULATE_VISUAL_CONCERN_OVERRIDE",
            ),
        ],
    )

    runner = EvaluationRunner(live=False)
    report = asyncio.run(runner.run_dataset(ds, dataset_dir=tmp_path))

    assert report.total_evaluated == 2
    # Neither case must be counted as invalid / fabricated citation!
    assert report.summary_metrics.invalid_citation_cases == 0

    c1 = report.case_reports[0]
    assert c1.citation_count == 2
    assert c1.valid_citations is True
    assert c1.safe_error_code is None
    assert c1.verdict_actual == "FLAGGED"
    assert c1.verdict_source == "SYSTEM_OVERRIDE"

    c2 = report.case_reports[1]
    assert c2.citation_count == 0
    assert c2.valid_citations is True
    assert c2.safe_error_code is None
    assert c2.verdict_actual == "FLAGGED"
    assert c2.verdict_source == "SYSTEM_OVERRIDE"

    # Both cases increment system_flagged_count
    assert report.summary_metrics.system_flagged_count == 2
    assert report.summary_metrics.model_flagged_count == 0


def test_override_without_post_processing_reason_increments_system_flagged():
    """Verify that when raw_verdict=SUPPORTED and verdict=FLAGGED but post_processing_reason is missing:
    1. evaluate_transparency_step assigns verdict_source='SYSTEM_OVERRIDE'.
    2. post_processing_reason remains None (no speculative deduction).
    3. compute_aggregate_metrics increments system_flagged_count based on verdict_source.
    """
    eval_step = evaluate_transparency_step(
        expected=ExpectedTransparency(verdict="FLAGGED"),
        actual={
            "verdict": "FLAGGED",
            "raw_verdict": "SUPPORTED",
            # post_processing_reason is omitted/None
            "citations": [],
            "visual_signals": [{"page": 1, "description": "Dấu hiệu nghi vấn", "concern": True}],
        },
        read_facts=[],
        duration=0.5,
    )
    assert eval_step.verdict_raw == "SUPPORTED"
    assert eval_step.verdict_actual == "FLAGGED"
    assert eval_step.verdict_source == "SYSTEM_OVERRIDE"
    assert eval_step.post_processing_reason is None

    case_res = CaseEvaluationResult(
        case_id="CASE_TEST_001",
        file="REDACTED",
        criterion_code="7b",
        status="COMPLETED",
        total_duration_seconds=0.5,
        transparency=eval_step,
    )

    allowlisted = case_res.to_allowlisted_report()
    assert allowlisted.verdict_source == "SYSTEM_OVERRIDE"
    assert allowlisted.post_processing_reason is None

    metrics = compute_aggregate_metrics([case_res])
    # Must increment system_flagged_count based on verdict_source, NOT model_flagged_count
    assert metrics.system_flagged_count == 1
    assert metrics.model_flagged_count == 0

    # Test explicit CaseTransparencyEvaluation with post_processing_reason=None but verdict_source="SYSTEM_OVERRIDE"
    case_explicit_none = CaseEvaluationResult(
        case_id="CASE_TEST_002",
        file="REDACTED",
        criterion_code="7b",
        status="COMPLETED",
        total_duration_seconds=0.5,
        transparency=CaseTransparencyEvaluation(
            verdict_expected="FLAGGED",
            verdict_actual="FLAGGED",
            verdict_raw="SUPPORTED",
            verdict_source="SYSTEM_OVERRIDE",
            post_processing_reason=None,
            verdict_match=True,
            citation_count=0,
            valid_citations=True,
            duration_seconds=0.5,
        ),
    )
    metrics_explicit = compute_aggregate_metrics([case_explicit_none])
    assert metrics_explicit.system_flagged_count == 1
    assert metrics_explicit.model_flagged_count == 0






