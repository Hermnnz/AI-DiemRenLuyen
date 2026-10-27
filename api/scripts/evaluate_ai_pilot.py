"""CLI Tool for AI Pilot Evaluation (Stage F1).

Evaluates AI_Read and AI_Transparency layers against human-labeled ground truth.

Usage:
    # 1. Default MOCK mode (Fast, deterministic, 0 API calls, 0 cost):
    python api/scripts/evaluate_ai_pilot.py

    # 2. Limit number of cases:
    python api/scripts/evaluate_ai_pilot.py --limit 3

    # 3. Specify custom labels and dataset directory:
    python api/scripts/evaluate_ai_pilot.py --labels-file path/to/labels.json --dataset-dir path/to/evidence_dir

    # 4. LIVE mode (Paid Google Gemini REST API calls, requires GEMINI_API_KEY):
    python api/scripts/evaluate_ai_pilot.py --live --limit 2
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure api directory is in python path
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from api.app.config import settings
from api.app.evaluation import (
    EvaluationDataset,
    EvaluationRunner,
    format_safe_validation_error,
    format_terminal_report,
    save_json_report,
)


def main():
    default_labels = repo_root / "api" / "data" / "pilot_evaluation" / "labels.json"
    default_dataset = repo_root / "api" / "data" / "pilot_evaluation"

    parser = argparse.ArgumentParser(
        description="Đánh giá hiệu năng AI Pilot (Tầng AI_Read và AI_Transparency) theo Stage F1."
    )
    parser.add_argument(
        "--labels-file",
        type=Path,
        default=default_labels,
        help=f"Đường dẫn tệp JSON nhãn chuẩn con người (mặc định: {default_labels})",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=None,
        help="Thư mục gốc chứa tệp minh chứng đã ẩn danh (mặc định: thư mục cha của labels-file)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Đường dẫn lưu báo cáo JSON kết quả (mặc định: output/ai_eval_report_<timestamp>.json)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Gọi API thật tới Google Gemini. Mặc định KHÔNG gọi (chạy MOCK giả lập an toàn).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số ca chạy tối đa (hữu ích khi kiểm thử hoặc hạn chế số lượt gọi API)",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Vị trí ca bắt đầu chạy trong bộ dữ liệu (1-based, mặc định: 1). Ví dụ: --start-index 3",
    )
    parser.add_argument(
        "--model-read",
        type=str,
        default=None,
        help=f"Mô hình cho tầng AI_Read (mặc định: {settings.GEMINI_MODEL})",
    )
    parser.add_argument(
        "--model-transparency",
        type=str,
        default=None,
        help=f"Mô hình cho tầng AI_Transparency (mặc định: {settings.GEMINI_TRANSPARENCY_MODEL})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Chỉ in tóm tắt ngắn, không in chi tiết từng ca.",
    )

    args = parser.parse_args()

    if args.start_index < 1:
        print("[LỖI] Tham số --start-index phải là số nguyên dương (>= 1).", file=sys.stderr)
        sys.exit(1)

    # 1. Validate labels file
    if not args.labels_file.is_file():
        print(f"[LỖI] Không tìm thấy tệp nhãn tại: {args.labels_file}", file=sys.stderr)
        sys.exit(1)

    dataset_dir = args.dataset_dir or args.labels_file.parent
    if not dataset_dir.is_dir():
        print(f"[LỖI] Thư mục chứa minh chứng không tồn tại: {dataset_dir}", file=sys.stderr)
        sys.exit(1)

    # 2. Check live constraints
    if args.live:
        if args.limit is None or args.limit <= 0:
            print(
                "[LỖI BẢO VỆ] Khi sử dụng tham số --live, bắt buộc phải chỉ định --limit là một số nguyên dương (> 0) để khống chế số lời gọi API.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not settings.GEMINI_API_KEY:
            print(
                "[LỖI] Tham số --live yêu cầu biến môi trường GEMINI_API_KEY trong .env.",
                file=sys.stderr,
            )
            sys.exit(1)

    # 3. Load dataset
    try:
        content = args.labels_file.read_text(encoding="utf-8")
        dataset = EvaluationDataset.model_validate_json(content)
    except Exception as exc:
        safe_msg = format_safe_validation_error(exc)
        print(f"[LỖI] Tệp nhãn không đúng định dạng schema:\n{safe_msg}", file=sys.stderr)
        sys.exit(1)

    if not dataset.cases:
        print("[CẢNH BÁO] Bộ dữ liệu không có ca đánh giá nào.", file=sys.stderr)
        sys.exit(0)

    # 4. Initialize runner
    runner = EvaluationRunner(
        live=args.live,
        api_key=settings.GEMINI_API_KEY,
        model_read=args.model_read,
        model_transparency=args.model_transparency,
        limit=args.limit,
        start_index=args.start_index,
    )

    mode_label = "LIVE (Gọi Gemini API thật)" if args.live else "MOCK (Giả lập mô hình không gọi API)"
    print(f"[*] Bắt đầu đánh giá Pilot: từ ca #{args.start_index} (Chế độ: {mode_label})...")

    # 5. Execute evaluation
    report = asyncio.run(runner.run_dataset(dataset, dataset_dir))

    # 6. Render report
    terminal_output = format_terminal_report(report)
    print(terminal_output)

    # 7. Save JSON report
    if args.output is None:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_dir = repo_root / "output"
        output_path = output_dir / f"ai_eval_report_{report.mode.lower()}_{timestamp_str}.json"
    else:
        output_path = args.output

    saved_path = save_json_report(report, output_path)
    print(f"[+] Báo cáo chi tiết đã được lưu tại: {saved_path}")


if __name__ == "__main__":
    main()
