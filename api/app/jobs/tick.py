import argparse
import sys
import os
from datetime import datetime, timezone

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from api.app.database import SessionLocal
from api.app.services.deadline_service import run_deadline_tick


def run_tick(target_time: datetime):
    print(f"[DeadlineTick] Chạy kiểm tra hạn tại mốc thời gian (UTC): {target_time.isoformat()}")
    db = SessionLocal()
    try:
        stats = run_deadline_tick(db, target_time)
        print(f"[DeadlineTick] Kết quả: {stats}")
        print("[DeadlineTick] Hoàn thành kiểm tra hạn thành công.")
    finally:
        db.close()


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
