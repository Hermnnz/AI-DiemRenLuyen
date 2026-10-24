import argparse
import sys
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_tick(target_time: datetime):
    print(f"[DeadlineTick] Chạy kiểm tra hạn tại mốc thời gian (UTC): {target_time.isoformat()}")
    # Vỏ giai đoạn 0: Đặt cấu trúc lệnh, Gói A sẽ hoàn thiện chi tiết nghiệp vụ workflow/state transitions
    print("[DeadlineTick] Hoàn thành kiểm tra hạn thành công.")


def main():
    parser = argparse.ArgumentParser(description="Xử lý deadline và các mốc thời gian đợt đánh giá ĐRL.")
    parser.add_argument("--now", type=str, help="Thời gian giả lập định dạng ISO8601 (ví dụ: 2026-10-25T01:00:00Z)")
    args = parser.parse_args()

    if args.now:
        try:
            target_time = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        except ValueError as e:
            print(f"Lỗi định dạng thời gian --now: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        target_time = datetime.now(timezone.utc)

    run_tick(target_time)


if __name__ == "__main__":
    main()
