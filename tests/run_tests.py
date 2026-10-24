#!/usr/bin/env python
"""
Test runner script for Package D (Acceptance & Contract Testing).
Provides execution commands and formatted summary for Phase 1 and Phase 2.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent


def print_banner(text: str):
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Package D Test Runner")
    parser.add_argument(
        "--mode",
        choices=["runnable", "contract", "e2e", "all"],
        default="runnable",
        help="Test execution mode (default: runnable - runs contract tests and reports skipped e2e)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose pytest output")
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)

    pytest_cmd = [sys.executable, "-m", "pytest"]
    if args.verbose:
        pytest_cmd.append("-v")

    if args.mode == "contract":
        print_banner("Chạy Kiểm Thử Hợp Đồng (Contract Tests: OpenAPI, Fixtures, States)")
        pytest_cmd.append("tests/contract")
        ret = subprocess.run(pytest_cmd, cwd=ROOT_DIR, env=env).returncode

    elif args.mode == "e2e":
        print_banner("Chạy 16 Kiểm Thử Chấp Nhận (Section 9 Acceptance Tests)")
        env["RUN_ACCEPTANCE_TESTS"] = "1"
        pytest_cmd.append("tests/e2e")
        ret = subprocess.run(pytest_cmd, cwd=ROOT_DIR, env=env).returncode

    elif args.mode == "all":
        print_banner("Chạy Toàn Bộ Kiểm Thử (Contract + Acceptance)")
        env["RUN_ACCEPTANCE_TESTS"] = "1"
        pytest_cmd.append("tests")
        ret = subprocess.run(pytest_cmd, cwd=ROOT_DIR, env=env).returncode

    else:  # runnable (default)
        print_banner("Chạy Các Kiểm Thử Hiện Khả Dụng (Giai đoạn 1 - Package D)")
        print("-> Đang chạy kiểm thử hợp đồng (OpenAPI / Seed Fixtures / States)...")
        print("-> 16 kiểm thử chấp nhận được đánh dấu SKIPPED chờ ghép backend ở Giai đoạn 2.\n")
        pytest_cmd.append("tests")
        ret = subprocess.run(pytest_cmd, cwd=ROOT_DIR, env=env).returncode

    print("\n" + "=" * 70)
    print("  BẢNG TỔNG KẾT 16 TIÊU CHÍ CHẤP NHẬN MỤC 9")
    print("=" * 70)
    criteria = [
        ("Mục 9.1", "STUDENT chỉ thấy case của chính mình; sửa ID bị 404/403", "tests/e2e/test_01_student_isolation.py"),
        ("Mục 9.2", "BCS lớp A không mở case lớp B; GVCN không sửa điểm", "tests/e2e/test_02_bcs_gvcn_rbac.py"),
        ("Mục 9.3", "Form lưu nháp rồi tải lại giữ nguyên điểm và tệp; tổng đúng", "tests/e2e/test_03_draft_persistence.py"),
        ("Mục 9.4", "Nộp thiếu minh chứng bắt buộc -> NEEDS_INFO, bổ sung -> BCS_REVIEW", "tests/e2e/test_04_missing_evidence_info.py"),
        ("Mục 9.5", "Hết lượt/hạn bổ sung INFO đóng CLOSED_INCOMPLETE, không lặp", "tests/e2e/test_05_info_round_limit_close.py"),
        ("Mục 9.6", "BCS yêu cầu PROOF, quá hạn quay BCS kết luận, không tự trừ", "tests/e2e/test_06_bcs_proof_request.py"),
        ("Mục 9.7", "BCS nhập điểm vượt max/khác tự khai không lý do bị 422", "tests/e2e/test_07_bcs_scoring_validation.py"),
        ("Mục 9.8", "Chưa đủ 2 cuộc họp hoặc còn case chờ BCS -> không công bố", "tests/e2e/test_08_publication_gates.py"),
        ("Mục 9.9", "Trước công bố SV không thấy điểm; sau công bố thấy đúng điểm", "tests/e2e/test_09_score_visibility.py"),
        ("Mục 9.10", "SV đồng ý không thể khiếu nại và ngược lại; concurrency", "tests/e2e/test_10_mutual_exclusion_accept_appeal.py"),
        ("Mục 9.11", "BCS giải quyết khiếu nại KEEP/ADJUST; audit trail đầy đủ", "tests/e2e/test_11_appeal_resolution_audit.py"),
        ("Mục 9.12", "Deadline tick chạy 2 lần không trùng thông báo, không tăng lượt", "tests/e2e/test_12_deadline_tick_idempotent.py"),
        ("Mục 9.13", "Quá hạn phản hồi thành ACCEPTED_AUTO đúng 1 lần", "tests/e2e/test_13_auto_accept_timeout.py"),
        ("Mục 9.14", "Chỉ chốt khi mọi case đủ điều kiện; GVCN chỉ xem/tải CSV sau chốt", "tests/e2e/test_14_finalize_and_gvcn_csv.py"),
        ("Mục 9.15", "Tệp không xem qua URL storage; kiểm quyền và MIME PDF/JPG/PNG", "tests/e2e/test_15_file_security_mime.py"),
        ("Mục 9.16", "Đợt SCHEDULED chưa tạo case; tick ở open_at tạo đúng 1 case/SV", "tests/e2e/test_16_scheduled_campaign_open.py"),
    ]

    for code, desc, test_file in criteria:
        status_tag = "[CHỜ GHÉP GIAI ĐOẠN 2]" if args.mode != "e2e" and args.mode != "all" else "[TEST ĐÃ CHẠY]"
        print(f"  * {code:<9} {status_tag} {desc}")
    print("=" * 70)

    sys.exit(ret)


if __name__ == "__main__":
    main()
