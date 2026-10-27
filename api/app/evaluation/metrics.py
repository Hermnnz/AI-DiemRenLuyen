"""Evaluation metrics calculation for AI Read and Transparency.

Includes strict citation ground-truth verification and allowlisted safe metric aggregation.
"""

import re
from typing import Any, Dict, List, Optional
from api.app.evaluation.schemas import (
    ALLOWED_POST_PROCESSING_REASONS,
    AggregateMetrics,
    CaseEvaluationResult,
    CaseReadEvaluation,
    CaseTransparencyEvaluation,
    ConfusionMatrix,
    ExpectedFact,
    ExpectedRead,
    ExpectedTransparency,
    FactMatchDetail,
)


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return " ".join(text.strip().lower().split())


def match_fact(expected: ExpectedFact, extracted: Dict[str, Any]) -> bool:
    if expected.kind != extracted.get("kind"):
        return False
    if expected.page is not None:
        act_page = extracted.get("page")
        if act_page is None or act_page != expected.page:
            return False

    exp_val = normalize_text(expected.value)
    act_val = normalize_text(str(extracted.get("value", "")))

    if not exp_val or not act_val:
        return False

    if expected.match_mode == "exact":
        return exp_val == act_val
    elif expected.match_mode == "contains":
        return exp_val in act_val
    elif expected.match_mode == "regex":
        try:
            pattern = re.compile(expected.value, re.IGNORECASE)
            return bool(pattern.search(act_val))
        except re.error:
            return exp_val in act_val

    return False


def verify_citation(citation: Dict[str, Any], read_facts: List[Dict[str, Any]]) -> bool:
    """Verifies that a citation has all required fields and strictly matches an actual fact

    from AI_Read SIMULTANEOUSLY across page, kind, value, and source_excerpt.
    Does not accept 1-character fragments or short substrings.
    """
    if not isinstance(citation, dict) or not read_facts:
        return False

    cit_page = citation.get("page")
    cit_kind = citation.get("kind")
    raw_val = citation.get("value")
    raw_excerpt = citation.get("source_excerpt")

    # 1. All 4 fields must be present and non-empty
    if cit_page is None or not isinstance(cit_page, int) or cit_page < 1:
        return False
    if not cit_kind or not isinstance(cit_kind, str) or not cit_kind.strip():
        return False
    if not raw_val or not isinstance(raw_val, str) or not raw_val.strip():
        return False
    if not raw_excerpt or not isinstance(raw_excerpt, str) or not raw_excerpt.strip():
        return False

    cit_val = normalize_text(raw_val)
    cit_excerpt = normalize_text(raw_excerpt)
    cit_kind_norm = cit_kind.strip().lower()

    # Reject 1-character fragments or overly short strings (< 2 chars)
    if len(cit_val) < 2 or len(cit_excerpt) < 2:
        return False

    # 2. Must match at least one fact in read_facts SIMULTANEOUSLY across all 4 fields
    for rf in read_facts:
        if not isinstance(rf, dict):
            continue

        rf_page = rf.get("page")
        rf_kind = str(rf.get("kind", "")).strip().lower()
        rf_val = normalize_text(str(rf.get("value", "")))
        rf_excerpt = normalize_text(str(rf.get("source_excerpt", "")))

        # Page must match
        if cit_page != rf_page:
            continue

        # Kind must match
        if cit_kind_norm != rf_kind:
            continue

        # Full match of value and excerpt after whitespace/case normalization
        val_match = (cit_val == rf_val)
        excerpt_match = (cit_excerpt == rf_excerpt)

        # MUST MATCH BOTH VALUE AND SOURCE_EXCERPT SIMULTANEOUSLY!
        if val_match and excerpt_match:
            return True

    return False


def evaluate_read_step(
    expected: ExpectedRead,
    actual: Optional[Dict[str, Any]],
    duration: float,
    safe_error_code: Optional[str] = None,
) -> CaseReadEvaluation:
    if not actual or safe_error_code:
        return CaseReadEvaluation(
            readable_expected=expected.readable,
            readable_actual=None,
            readable_match=False,
            unreadable_reason=None,
            expected_fact_count=len(expected.expected_facts),
            extracted_fact_count=0,
            matched_fact_count=0,
            precision=0.0,
            recall=0.0,
            missing_facts=[f.model_dump() for f in expected.expected_facts],
            fact_details=[
                FactMatchDetail(
                    expected_kind=f.kind,
                    expected_value=f.value,
                    found=False,
                )
                for f in expected.expected_facts
            ],
            duration_seconds=round(duration, 3),
            usage_metadata=None,
            safe_error_code=safe_error_code,
        )

    readable_act = bool(actual.get("readable", False))
    readable_match = readable_act == expected.readable
    extracted_facts = actual.get("facts", []) or []

    fact_details: List[FactMatchDetail] = []
    missing_facts: List[Dict[str, Any]] = []
    matched_count = 0

    used_extracted_indexes = set()
    for exp_fact in expected.expected_facts:
        found = False
        matched_val = None
        matched_pg = None

        for idx, ext_fact in enumerate(extracted_facts):
            if idx in used_extracted_indexes:
                continue
            if match_fact(exp_fact, ext_fact):
                found = True
                matched_val = ext_fact.get("value")
                matched_pg = ext_fact.get("page")
                used_extracted_indexes.add(idx)
                break

        if found:
            matched_count += 1
            fact_details.append(
                FactMatchDetail(
                    expected_kind=exp_fact.kind,
                    expected_value=exp_fact.value,
                    found=True,
                    matched_value=matched_val,
                    matched_page=matched_pg,
                )
            )
        else:
            missing_facts.append(exp_fact.model_dump())
            fact_details.append(
                FactMatchDetail(
                    expected_kind=exp_fact.kind,
                    expected_value=exp_fact.value,
                    found=False,
                )
            )

    exp_count = len(expected.expected_facts)
    ext_count = len(extracted_facts)

    precision = round(matched_count / ext_count, 4) if ext_count > 0 else 0.0
    recall = round(matched_count / exp_count, 4) if exp_count > 0 else 1.0

    return CaseReadEvaluation(
        readable_expected=expected.readable,
        readable_actual=readable_act,
        readable_match=readable_match,
        unreadable_reason=actual.get("unreadable_reason"),
        expected_fact_count=exp_count,
        extracted_fact_count=ext_count,
        matched_fact_count=matched_count,
        precision=precision,
        recall=recall,
        missing_facts=missing_facts,
        fact_details=fact_details,
        duration_seconds=round(duration, 3),
        usage_metadata=actual.get("usage_metadata"),
        safe_error_code=None,
    )


def evaluate_transparency_step(
    expected: ExpectedTransparency,
    actual: Optional[Dict[str, Any]],
    read_facts: List[Dict[str, Any]],
    duration: float,
    safe_error_code: Optional[str] = None,
) -> CaseTransparencyEvaluation:
    if not actual or safe_error_code:
        return CaseTransparencyEvaluation(
            verdict_expected=expected.verdict,
            verdict_actual=None,
            verdict_raw=None,
            post_processing_reason=None,
            verdict_source=None,
            verdict_match=False,
            is_false_flag=False,
            is_missed_flag=False,
            is_inconclusive=False,
            reason=None,
            citation_count=0,
            valid_citations=None,  # Chưa đánh giá khi không có kết luận đối chiếu
            safe_citation_error=None,
            visual_signals_count=0,
            authenticity=None,
            duration_seconds=round(duration, 3),
            usage_metadata=None,
            safe_error_code=safe_error_code,
        )

    verdict_act = actual.get("verdict", "UNKNOWN")
    raw_v = actual.get("raw_verdict", verdict_act)
    if raw_v not in {"SUPPORTED", "FLAGGED", "UNKNOWN"}:
        raw_v = verdict_act

    raw_pp = actual.get("post_processing_reason")
    post_proc = raw_pp if raw_pp in ALLOWED_POST_PROCESSING_REASONS else None

    # Determine verdict_source:
    if post_proc or (raw_v != verdict_act):
        verdict_source = "SYSTEM_OVERRIDE"
    else:
        verdict_source = "MODEL_DIRECT"

    verdict_match = verdict_act == expected.verdict
    is_false_flag = expected.verdict == "SUPPORTED" and verdict_act == "FLAGGED"
    is_missed_flag = expected.verdict == "FLAGGED" and verdict_act == "SUPPORTED"
    is_inconclusive = expected.verdict in {"SUPPORTED", "FLAGGED"} and verdict_act == "UNKNOWN"

    citations = actual.get("citations", []) or []
    valid_citations = True
    safe_citation_err = None

    # Strict citation grounding check
    if verdict_act == "SUPPORTED" and len(citations) == 0:
        valid_citations = False
        safe_citation_err = "MISSING_CITATIONS_FOR_SUPPORTED"

    for cit in citations:
        if not verify_citation(cit, read_facts):
            valid_citations = False
            safe_citation_err = "FABRICATED_OR_UNGROUNDED_CITATION"
            break

    visual_signals = actual.get("visual_signals", []) or []

    return CaseTransparencyEvaluation(
        verdict_expected=expected.verdict,
        verdict_actual=verdict_act,
        verdict_raw=raw_v,
        post_processing_reason=post_proc,
        verdict_source=verdict_source,
        verdict_match=verdict_match,
        is_false_flag=is_false_flag,
        is_missed_flag=is_missed_flag,
        is_inconclusive=is_inconclusive,
        reason=actual.get("reason"),
        citation_count=len(citations),
        valid_citations=valid_citations,
        safe_citation_error=safe_citation_err,
        visual_signals_count=len(visual_signals),
        authenticity=actual.get("authenticity"),
        duration_seconds=round(duration, 3),
        usage_metadata=actual.get("usage_metadata"),
        safe_error_code=safe_citation_err if not valid_citations and safe_citation_err else None,
    )


def compute_aggregate_metrics(case_results: List[CaseEvaluationResult]) -> AggregateMetrics:
    total = len(case_results)
    if total == 0:
        return AggregateMetrics()

    successful = sum(1 for c in case_results if c.status == "COMPLETED")
    failed = sum(1 for c in case_results if c.status == "FAILED")
    skipped = sum(1 for c in case_results if c.status == "SKIPPED")
    executed = sum(1 for c in case_results if c.status != "SKIPPED")

    # Confusion matrix
    conf_matrix = ConfusionMatrix()
    exact_matches = 0
    false_flags = 0
    missed_flags = 0
    unknowns = 0
    model_flagged_count = 0
    system_flagged_count = 0
    system_unknown_count = 0

    assessed_cases = 0
    human_supported_evaluated = 0
    human_flagged_evaluated = 0

    # Read metrics
    readable_matches = 0
    sum_fact_precision = 0.0
    sum_fact_recall = 0.0
    total_missing_facts = 0
    read_evaluated_cases = 0
    read_valid_evaluated_cases = 0

    # Citations (assessed strictly on cases with actual AI conclusion)
    invalid_citation_cases = 0
    sum_citations = 0

    # Latencies (strictly excluding SKIPPED cases)
    read_latencies: List[float] = []
    trans_latencies: List[float] = []
    total_latencies: List[float] = []

    # API errors (standardized safe codes only)
    api_errors: Dict[str, int] = {}

    # Tokens
    prompt_tokens = 0
    candidate_tokens = 0
    total_tokens_count = 0
    has_tokens = False

    for c in case_results:
        # Latency: Do NOT include 0.0s of SKIPPED cases
        if c.status != "SKIPPED":
            total_latencies.append(c.total_duration_seconds)

        if c.tokens:
            has_tokens = True
            prompt_tokens += c.tokens.get("prompt_tokens", 0)
            candidate_tokens += c.tokens.get("candidate_tokens", 0)
            total_tokens_count += c.tokens.get("total_tokens", 0)

        # Standardized safe error aggregation
        if c.safe_error_code:
            api_errors[c.safe_error_code] = api_errors.get(c.safe_error_code, 0) + 1

        # Read eval
        if c.read:
            read_latencies.append(c.read.duration_seconds)
            if c.read.readable_actual is not None:
                read_evaluated_cases += 1
                if c.read.readable_match:
                    readable_matches += 1
                if c.read.readable_actual is True:
                    read_valid_evaluated_cases += 1
                    sum_fact_precision += c.read.precision
                    sum_fact_recall += c.read.recall
                    total_missing_facts += len(c.read.missing_facts)
            if c.read.safe_error_code and c.read.safe_error_code != c.safe_error_code:
                api_errors[c.read.safe_error_code] = api_errors.get(c.read.safe_error_code, 0) + 1

        # Transparency eval: Only evaluate AI conclusion quality if verdict_actual is present
        if c.transparency:
            if c.transparency.duration_seconds > 0:
                trans_latencies.append(c.transparency.duration_seconds)

            exp_v = c.transparency.verdict_expected
            act_v = c.transparency.verdict_actual

            if act_v is not None:
                # Case has actual AI conclusion
                assessed_cases += 1
                sum_citations += c.transparency.citation_count
                if c.transparency.valid_citations is False:
                    invalid_citation_cases += 1

                if exp_v in conf_matrix.matrix and act_v in conf_matrix.matrix[exp_v]:
                    conf_matrix.matrix[exp_v][act_v] += 1

                if c.transparency.verdict_match:
                    exact_matches += 1

                if exp_v == "SUPPORTED":
                    human_supported_evaluated += 1
                    if act_v == "FLAGGED":
                        false_flags += 1

                if exp_v == "FLAGGED":
                    human_flagged_evaluated += 1
                    if act_v == "SUPPORTED":
                        missed_flags += 1

                if act_v == "UNKNOWN":
                    unknowns += 1

                # Track model direct vs system override based strictly on verdict_source
                if act_v == "FLAGGED":
                    if c.transparency.verdict_source == "SYSTEM_OVERRIDE":
                        system_flagged_count += 1
                    else:
                        model_flagged_count += 1
                if act_v == "UNKNOWN" and c.transparency.verdict_source == "SYSTEM_OVERRIDE":
                    system_unknown_count += 1
            elif c.status == "FAILED":
                # FAILED case without verdict: records into ERROR column of confusion matrix
                if exp_v in conf_matrix.matrix:
                    conf_matrix.matrix[exp_v]["ERROR"] += 1

            if c.transparency.safe_error_code and c.transparency.safe_error_code != c.safe_error_code:
                api_errors[c.transparency.safe_error_code] = api_errors.get(c.transparency.safe_error_code, 0) + 1

    # Quality metrics calculated strictly over actual evaluated cases (assessed_cases)
    exact_match_accuracy = round(exact_matches / assessed_cases, 4) if assessed_cases > 0 else 0.0
    false_flag_rate = round(false_flags / human_supported_evaluated, 4) if human_supported_evaluated > 0 else 0.0
    missed_flag_rate = round(missed_flags / human_flagged_evaluated, 4) if human_flagged_evaluated > 0 else 0.0
    unknown_rate = round(unknowns / assessed_cases, 4) if assessed_cases > 0 else 0.0

    # OCR metrics
    read_readability_acc = round(readable_matches / read_evaluated_cases, 4) if read_evaluated_cases > 0 else 0.0
    read_avg_prec = round(sum_fact_precision / read_valid_evaluated_cases, 4) if read_valid_evaluated_cases > 0 else 0.0
    read_avg_rec = round(sum_fact_recall / read_valid_evaluated_cases, 4) if read_valid_evaluated_cases > 0 else 0.0

    # Citations
    avg_citations = round(sum_citations / assessed_cases, 2) if assessed_cases > 0 else 0.0

    # Latencies
    avg_read_lat = round(sum(read_latencies) / len(read_latencies), 2) if read_latencies else 0.0
    avg_trans_lat = round(sum(trans_latencies) / len(trans_latencies), 2) if trans_latencies else 0.0
    avg_tot_lat = round(sum(total_latencies) / len(total_latencies), 2) if total_latencies else 0.0
    min_tot_lat = round(min(total_latencies), 2) if total_latencies else 0.0
    max_tot_lat = round(max(total_latencies), 2) if total_latencies else 0.0

    return AggregateMetrics(
        total_cases=total,
        successful_cases=successful,
        failed_cases=failed,
        skipped_cases=skipped,
        executed_cases=executed,
        assessed_cases=assessed_cases,
        human_supported_evaluated=human_supported_evaluated,
        human_flagged_evaluated=human_flagged_evaluated,
        confusion_matrix=conf_matrix,
        exact_match_accuracy=exact_match_accuracy,
        false_flag_count=false_flags,
        false_flag_rate=false_flag_rate,
        missed_flag_count=missed_flags,
        missed_flag_rate=missed_flag_rate,
        unknown_count=unknowns,
        unknown_rate=unknown_rate,
        model_flagged_count=model_flagged_count,
        system_flagged_count=system_flagged_count,
        system_unknown_count=system_unknown_count,
        read_evaluated_cases=read_evaluated_cases,
        read_valid_evaluated_cases=read_valid_evaluated_cases,
        read_readability_accuracy=read_readability_acc,
        read_avg_fact_precision=read_avg_prec,
        read_avg_fact_recall=read_avg_rec,
        total_missing_facts=total_missing_facts,
        invalid_citation_cases=invalid_citation_cases,
        avg_citations_per_case=avg_citations,
        latency_read_avg=avg_read_lat,
        latency_transparency_avg=avg_trans_lat,
        latency_total_avg=avg_tot_lat,
        latency_total_min=min_tot_lat,
        latency_total_max=max_tot_lat,
        api_errors=api_errors,
        total_prompt_tokens=prompt_tokens if has_tokens else None,
        total_candidate_tokens=candidate_tokens if has_tokens else None,
        total_tokens=total_tokens_count if has_tokens else None,
    )
