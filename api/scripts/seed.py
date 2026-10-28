import os
import sys
import json

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from datetime import datetime
from api.app.security import hash_password

from api.app.database import SessionLocal, engine, Base
from api.app.config import settings
from api.app.models import (
    User,
    Class,
    ClassMember,
    Campaign,
    Criterion,
    UserPosition,
)
from api.app.services.template_service import ensure_templates_seeded


def run_seed():
    demo_password = os.getenv("DEMO_PASSWORD", "Demo123456")
    password_hash = hash_password(demo_password)

    fixtures_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "contracts", "seed-fixtures.json")
    )
    if os.path.exists(fixtures_path):
        with open(fixtures_path, "r", encoding="utf-8") as f:
            fixtures = json.load(f).get("seed_data", {})
    else:
        raise FileNotFoundError(f"Fixture file not found at: {fixtures_path}")

    # Ensure tables exist (creates tables if migration not run or during testing)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[Seed] Khởi tạo dữ liệu mẫu (Idempotent)...")

        # 1. Seed Class
        cls_data = fixtures["class"]
        existing_cls = db.query(Class).filter(Class.code == cls_data["code"]).first()
        if not existing_cls:
            existing_cls = Class(
                id=cls_data["id"],
                code=cls_data["code"],
                name=cls_data["name"]
            )
            db.add(existing_cls)
            db.flush()
            print(f"  + Tạo lớp: {existing_cls.code} - {existing_cls.name}")
        else:
            print(f"  = Lớp đã tồn tại: {existing_cls.code}")

        # 2. Seed Users
        for u_data in fixtures["users"]:
            existing_user = db.query(User).filter(User.username == u_data["username"]).first()
            if not existing_user:
                existing_user = User(
                    id=u_data["id"],
                    username=u_data["username"],
                    password_hash=password_hash,
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    is_active=True
                )
                db.add(existing_user)
                db.flush()
                print(f"  + Tạo tài khoản: {existing_user.username} ({existing_user.role})")
            else:
                print(f"  = Tài khoản đã tồn tại: {existing_user.username}")

            # Class membership if belongs to class
            if u_data.get("class_id"):
                existing_member = db.query(ClassMember).filter(
                    ClassMember.class_id == u_data["class_id"],
                    ClassMember.user_id == existing_user.id,
                    ClassMember.member_role == u_data["role"]
                ).first()
                if not existing_member:
                    member = ClassMember(
                        class_id=u_data["class_id"],
                        user_id=existing_user.id,
                        member_role=u_data["role"]
                    )
                    db.add(member)
                    print(f"    -> Thêm thành viên lớp: {existing_user.username} vai trò {u_data['role']}")

        # 3. Seed Campaign
        c_data = fixtures["campaign"]
        existing_campaign = db.query(Campaign).filter(Campaign.id == c_data["id"]).first()
        if not existing_campaign:
            existing_campaign = Campaign(
                id=c_data["id"],
                class_id=c_data["class_id"],
                title=c_data["title"],
                term=c_data["term"],
                status=c_data["status"],
                open_at=datetime.fromisoformat(c_data["open_at"].replace("Z", "+00:00")),
                submission_deadline_at=datetime.fromisoformat(c_data["submission_deadline_at"].replace("Z", "+00:00")),
                supplement_period_hours=c_data["supplement_period_hours"],
                appeal_period_hours=c_data["appeal_period_hours"],
                reminder_after_hours=c_data["reminder_after_hours"],
                max_info_rounds=c_data["max_info_rounds"],
                max_proof_rounds=c_data["max_proof_rounds"],
                created_by=None
            )
            db.add(existing_campaign)
            db.flush()
            print(f"  + Tạo đợt đánh giá: {existing_campaign.title} ({existing_campaign.status})")
        else:
            print(f"  = Đợt đánh giá đã tồn tại: {existing_campaign.title}")

        # 4. Seed Criteria
        for crit in c_data["criteria"]:
            existing_crit = db.query(Criterion).filter(
                Criterion.campaign_id == existing_campaign.id,
                Criterion.code == crit["code"]
            ).first()
            if not existing_crit:
                new_crit = Criterion(
                    id=crit["id"],
                    campaign_id=existing_campaign.id,
                    code=crit["code"],
                    title=crit["title"],
                    description=crit["description"],
                    max_score=crit["max_score"],
                    requires_evidence=crit["requires_evidence"],
                    sort_order=crit["sort_order"]
                )
                db.add(new_crit)
                print(f"  + Tạo tiêu chí: {crit['code']} - {crit['title']} (Tối đa {crit['max_score']})")
            else:
                print(f"  = Tiêu chí đã tồn tại: {crit['code']}")

        # 5. Seed Evaluation Templates (Legacy Demo & 49K14.1)
        print("  + Khởi tạo mẫu quy tắc chấm có phiên bản...")
        ensure_templates_seeded(db)

        # 6. Seed Cadre Position for demo BCS
        bcs_user = db.query(User).filter(User.username == "bcs001").first()
        admin_user = db.query(User).filter(User.username == "admin001").first()
        if bcs_user and admin_user:
            existing_pos = db.query(UserPosition).filter(
                UserPosition.user_id == bcs_user.id,
                UserPosition.term == "HK1-2026-2027"
            ).first()
            if not existing_pos:
                pos = UserPosition(
                    user_id=bcs_user.id,
                    term="HK1-2026-2027",
                    position_title="Lớp trưởng",
                    organization="Lớp Công nghệ thông tin K46 - Minh họa",
                    is_confirmed=True,
                    confirmed_by=admin_user.id
                )
                db.add(pos)
                print(f"  + Gán chức vụ cán bộ: {bcs_user.username} - Lớp trưởng")

        db.commit()
        print("[Seed] Hoàn tất seed dữ liệu thành công không tạo bản ghi trùng.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Lỗi seed dữ liệu: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
