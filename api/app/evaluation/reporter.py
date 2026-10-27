"""Report generator for AI Pilot Evaluation (Stage F1).

Guarantees:
1. Strict allowlist fields only (no personal data, raw files, excerpts, or exceptions).
2. Prominent disclaimers distinguishing MOCK tool validation from real Gemini quality.
3. Distinction between synthetic script-generated labels and independent human-verified labels.
"""

import json
from pathlib import Path
from typing import Any, Dict

from api.app.evaluation.schemas import EvaluationReport
from pydantic import ValidationError


def _pct(val: float) -> str:
    return f"{val * 100:.1f}%"


def format_safe_validation_error(exc: Exception) -> str:
    """Format schema validation errors safely without printing raw input values or full ValidationError."""
    if isinstance(exc, ValidationError):
        lines = []
        for err in exc.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            err_type = err.get("type", "invalid_value")
            lines.append(f"  - Vị trí: '{loc}' | Loại lỗi: '{err_type}'")
        return "\n".join(lines[:10])
    elif isinstance(exc, json.JSONDecodeError):
        return f"Tệp không phải JSON hợp lệ (Dòng {exc.lineno}, Cột {exc.colno})."
    return "Tệp nhãn không hợp lệ hoặc thiếu cấu trúc bắt buộc."


def format_terminal_report(report: EvaluationReport) -> str:
    """Format full terminal report with ASCII tables and strict allowlisted safe fields."""
    summary = report.summary_metrics
    cm = summary.confusion_matrix.matrix

    lines = []
    lines.append("=" * 80)
    lines.append("  BÁO CÁO ĐÁNH GIÁ PILOT HỆ THỐNG AI (GIAI ĐOẠN F1)")
    lines.append("=" * 80)

    # Prominent Disclaimer Banner
    if report.is_mock_simulation:
        lines.append("  [!] CHẾ ĐỘ THỬ NGHIỆM: MOCK (GIẢ LẬP ĐỂ KIỂM TRA CÔNG CỤ & LUỒNG XỬ LÝ)")
        lines.append("  [!] CẢNH BÁO QUAN TRỌNG:")
        lines.append("      - Toàn bộ kết quả dưới đây KHÔNG PHẢI là độ chính xác của Google Gemini.")
        lines.append("      - Không sử dụng tỷ lệ 100% của MOCK để làm căn cứ đánh giá chất lượng AI.")
        lines.append("      - Chế độ MOCK chỉ kiểm tra tính hợp lệ của schema, logic metrics và bảo mật.")
    else:
        lines.append("  [*] CHẾ ĐỘ THỰC TẾ: LIVE (GỌI API GEMINI THỰC TẾ ĐỂ ĐỐI CHIẾU)")
    lines.append("-" * 80)

    # Dataset Provenance
    source_label = (
        "SYNTHETIC_SCRIPT_GENERATED (Dữ liệu giả lập do script tạo)"
        if report.dataset_source == "SYNTHETIC_SCRIPT_GENERATED"
        else "INDEPENDENT_HUMAN_VERIFIED (Bộ nhãn con người độc lập)"
    )
    audit_status = (
        "ĐÃ ĐƯỢC NGƯỜI ĐÁNH GIÁ ĐỘC LẬP XÁC NHẬN"
        if report.human_verified
        else "CHƯA XÁC NHẬN (Cần ban thẩm định độc lập đối soát)"
    )

    lines.append(f"  Nguồn dữ liệu nhãn:      {source_label}")
    lines.append(f"  Trạng thái thẩm định:    {audit_status}")
    lines.append(f"  Thời gian chạy:          {report.timestamp}")
    lines.append(f"  Chế độ:                  {report.mode}")
    lines.append(f"  Mô hình OCR (Read):      {report.model_read}")
    lines.append(f"  Mô hình Thẩm định:       {report.model_transparency}")
    lines.append(f"  Phiên bản bộ dữ liệu:    {report.dataset_version}")
    lines.append(
        f"  Tổng ca đánh giá:        {report.total_evaluated} "
        f"(Thành công: {summary.successful_cases}, Lỗi: {summary.failed_cases}, Bỏ qua: {summary.skipped_cases})"
    )
    lines.append("-" * 80)

    # 1. Confusion Matrix
    lines.append("  1. BẢNG ĐỐI CHIẾU NHÃN (CONFUSION MATRIX)")
    lines.append("     Human (Nhãn người) \\ AI (Nhãn mô hình):")
    lines.append("     " + "-" * 62)
    lines.append(f"     {'Nhãn chuẩn':<14} | {'SUPPORTED':<10} | {'FLAGGED':<10} | {'UNKNOWN':<10} | {'ERROR':<6} | {'Tổng':<6}")
    lines.append("     " + "-" * 62)
    for human_label in ["SUPPORTED", "FLAGGED", "UNKNOWN"]:
        row = cm.get(human_label, {})
        s_count = row.get("SUPPORTED", 0)
        f_count = row.get("FLAGGED", 0)
        u_count = row.get("UNKNOWN", 0)
        e_count = row.get("ERROR", 0)
        row_tot = s_count + f_count + u_count + e_count
        lines.append(f"     {human_label:<14} | {s_count:<10} | {f_count:<10} | {u_count:<10} | {e_count:<6} | {row_tot:<6}")
    lines.append("     " + "-" * 62)

    # 2. Key Verdict Metrics
    lines.append("")
    lines.append("  2. CHỈ SỐ THẨM ĐỊNH MINH CHỨNG (TRANSPARENCY METRICS) - CHẤT LƯỢNG KẾT LUẬN AI")
    if report.is_mock_simulation:
        lines.append("     *(Lưu ý: Chỉ số giả lập công cụ, không đại diện mô hình AI)*")
    lines.append(
        f"     - Số ca có kết luận AI thực tế:  {summary.assessed_cases} / {summary.total_cases} ca "
        f"(Thành công: {summary.successful_cases}, Lỗi: {summary.failed_cases}, Bỏ qua: {summary.skipped_cases})"
    )
    lines.append(
        f"     - Độ chính xác khớp hoàn toàn:  {_pct(summary.exact_match_accuracy)} "
        f"(trên {summary.assessed_cases} ca có kết luận đối chiếu)"
    )
    lines.append(
        f"     - Số ca gán cờ sai (False Flag): {summary.false_flag_count} "
        f"(Tỷ lệ: {_pct(summary.false_flag_rate)} trên {summary.human_supported_evaluated} ca SUPPORTED được thẩm định)"
    )
    lines.append(
        f"     - Số ca bỏ sót (Missed Flag):    {summary.missed_flag_count} "
        f"(Tỷ lệ: {_pct(summary.missed_flag_rate)} trên {summary.human_flagged_evaluated} ca FLAGGED được thẩm định)"
    )
    lines.append(
        f"     - Số ca chưa rõ (UNKNOWN):       {summary.unknown_count} "
        f"(Tỷ lệ: {_pct(summary.unknown_rate)} trên {summary.assessed_cases} ca có kết luận đối chiếu)"
    )
    lines.append(
        f"     - Phân loại ca FLAGGED:          Mô hình tự gắn: {summary.model_flagged_count} ca | "
        f"Hệ thống chuyển do visual concern: {summary.system_flagged_count} ca"
    )
    if summary.system_unknown_count > 0:
        lines.append(
            f"     - Ca chuyển UNKNOWN (Hệ thống):  {summary.system_unknown_count} ca "
            f"(do thiếu trích dẫn hoặc căn cứ)"
        )

    # 3. OCR Read Metrics
    lines.append("")
    lines.append("  3. CHỈ SỐ TRÍCH XUẤT DỮ KIỆN (AI READ METRICS)")
    if report.is_mock_simulation:
        lines.append("     *(Lưu ý: Chỉ số giả lập công cụ, không đại diện mô hình AI)*")
    lines.append(
        f"     - Độ chính xác đọc được:         {_pct(summary.read_readability_accuracy)} "
        f"(trên {summary.read_evaluated_cases} ca OCR được thực hiện)"
    )
    lines.append(
        f"     - Precision trích xuất dữ kiện: {_pct(summary.read_avg_fact_precision)} "
        f"(trên {summary.read_valid_evaluated_cases} ca đọc được)"
    )
    lines.append(
        f"     - Recall trích xuất dữ kiện:    {_pct(summary.read_avg_fact_recall)} "
        f"(trên {summary.read_valid_evaluated_cases} ca đọc được)"
    )
    lines.append(f"     - Tổng số dữ kiện bị thiếu:      {summary.total_missing_facts}")

    # 4. Citations & Integrity
    lines.append("")
    lines.append("  4. CHẤT LƯỢNG TRÍCH DẪN & TÍNH TOÀN VẸN (CITATION QUALITY)")
    lines.append(
        f"     - Số ca thiếu/sai trích dẫn:     {summary.invalid_citation_cases} "
        f"(trên {summary.assessed_cases} ca có kết luận; không tính ca 429/SKIPPED)"
    )
    lines.append(
        f"     - Số trích dẫn TB / ca:          {summary.avg_citations_per_case:.2f} "
        f"(trên {summary.assessed_cases} ca có kết luận đối chiếu)"
    )

    # 5. Performance & Latency
    lines.append("")
    lines.append("  5. THỜI GIAN XỬ LÝ & TÀI NGUYÊN (LATENCY & RESOURCES)")
    lines.append(f"     - Thời gian OCR (Read) TB:       {summary.latency_read_avg:.2f}s")
    lines.append(f"     - Thời gian Thẩm định TB:        {summary.latency_transparency_avg:.2f}s")
    lines.append(
        f"     - Tổng thời gian xử lý / ca:     TB {summary.latency_total_avg:.2f}s "
        f"(Min {summary.latency_total_min:.2f}s | Max {summary.latency_total_max:.2f}s) "
        f"[Tính trên {summary.executed_cases} ca thực thi, loại trừ ca SKIPPED]"
    )

    # 6. Tokens
    if summary.total_tokens is not None:
        lines.append("")
        lines.append("  6. THỐNG KÊ TOKEN (TỪ PHẢN HỒI CHÍNH THỨC GEMINI)")
        lines.append(f"     - Prompt tokens:                 {summary.total_prompt_tokens:,}")
        lines.append(f"     - Candidates tokens:             {summary.total_candidate_tokens:,}")
        lines.append(f"     - Tổng số tokens:                {summary.total_tokens:,}")
        lines.append("     * Ghi chú: Không ước tính chi phí tiền tệ do chưa cấu hình bảng giá chính thức.")

    # 7. Errors
    if summary.api_errors:
        lines.append("")
        lines.append("  7. THỐNG KÊ LỖI HỆ THỐNG / API (CHUẨN HÓA MÃ LỖI AN TOÀN)")
        for err_code, count in summary.api_errors.items():
            lines.append(f"     - {err_code:<35}: {count} ca")

    # 8. Per-case summary table (STRICT ALLOWLIST ONLY)
    lines.append("")
    lines.append("  8. CHI TIẾT TỪNG CA ĐÁNH GIÁ (CHỈ CHỨA TRƯỜNG AN TOÀN)")
    table_border = "  " + "-" * 105
    lines.append(table_border)
    lines.append(
        f"  {'Mã ca (Ẩn danh)':<16} | {'Tiêu chí':<9} | {'Human':<9} | {'AI gốc':<9} | {'AI cuối':<9} | "
        f"{'Nguồn':<10} | {'Khớp':<6} | {'Thời gian':<9} | {'Ghi chú an toàn / Hậu xử lý'}"
    )
    lines.append(table_border)
    for cr in report.case_reports:
        human_v = cr.verdict_expected
        ai_raw = cr.verdict_raw or "N/A"
        ai_v = cr.verdict_actual or "N/A"
        if cr.status == "FAILED":
            is_match = "LỖI"
            source_str = "LỖI"
        elif cr.status == "SKIPPED":
            is_match = "BỎ QUA"
            source_str = "BỎ QUA"
        else:
            is_match = "ĐÚNG" if cr.verdict_match else "SAI"
            source_str = "HỆ THỐNG" if cr.verdict_source == "SYSTEM_OVERRIDE" else "MÔ HÌNH"

        dur = f"{cr.total_duration_seconds:.2f}s"
        note_code = cr.safe_error_code or cr.post_processing_reason or "NONE"
        lines.append(
            f"  {cr.case_id:<16} | {cr.criterion_code:<9} | {human_v:<9} | {ai_raw:<9} | {ai_v:<9} | "
            f"{source_str:<10} | {is_match:<6} | {dur:<9} | {note_code}"
        )
    lines.append(table_border)
    lines.append("=" * 80)

    return "\n".join(lines)


def save_json_report(report: EvaluationReport, output_path: Path) -> Path:
    """Save strict allowlisted JSON report without raw file names, PII or exceptions."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = report.model_dump()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    return output_path
