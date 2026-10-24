import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.app.database import Base, get_db
from api.app.main import app
from api.app.security import hash_password
from api.app.models.entities import (
    User,
    Class,
    ClassMember,
    Campaign,
    Criterion,
    Case,
    Claim,
)

# Test SQLite in-memory engine with StaticPool so all connections share the same memory DB
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db):
    # Create Class 1 (LOP-DEMO) and Class 2 (LOP-OTHER)
    cls1 = Class(id="c1111111-1111-1111-1111-111111111111", code="LOP-DEMO", name="Lớp Demo A")
    cls2 = Class(id="c2222222-2222-2222-2222-222222222222", code="LOP-OTHER", name="Lớp Demo B")
    db.add_all([cls1, cls2])
    db.flush()

    pwd_hash = hash_password("Demo@123456")

    # Users
    sv1 = User(id="u1111111-1111-1111-1111-111111111111", username="sv001", password_hash=pwd_hash, full_name="Nguyễn Văn A", role="STUDENT")
    sv2 = User(id="u1111111-1111-1111-1111-111111111112", username="sv002", password_hash=pwd_hash, full_name="Trần Thị B", role="STUDENT")
    sv3 = User(id="u1111111-1111-1111-1111-111111111113", username="sv003", password_hash=pwd_hash, full_name="Lê Văn C", role="STUDENT")
    bcs1 = User(id="u1111111-1111-1111-1111-111111111114", username="bcs001", password_hash=pwd_hash, full_name="Phạm Ban Cán Sự", role="BCS")
    gvcn1 = User(id="u1111111-1111-1111-1111-111111111115", username="gvcn001", password_hash=pwd_hash, full_name="Hoàng Giáo Viên", role="GVCN")
    admin1 = User(id="u1111111-1111-1111-1111-111111111116", username="admin001", password_hash=pwd_hash, full_name="Quản Trị Viên", role="ADMIN")

    # Other class members for cross-class isolation testing
    sv_other = User(id="u2222222-2222-2222-2222-222222222221", username="sv_other", password_hash=pwd_hash, full_name="SV Lớp Khác", role="STUDENT")
    bcs_other = User(id="u2222222-2222-2222-2222-222222222222", username="bcs_other", password_hash=pwd_hash, full_name="BCS Lớp Khác", role="BCS")

    db.add_all([sv1, sv2, sv3, bcs1, gvcn1, admin1, sv_other, bcs_other])
    db.flush()

    # Memberships
    mems = [
        ClassMember(class_id=cls1.id, user_id=sv1.id, member_role="STUDENT"),
        ClassMember(class_id=cls1.id, user_id=sv2.id, member_role="STUDENT"),
        ClassMember(class_id=cls1.id, user_id=sv3.id, member_role="STUDENT"),
        ClassMember(class_id=cls1.id, user_id=bcs1.id, member_role="BCS"),
        ClassMember(class_id=cls1.id, user_id=gvcn1.id, member_role="GVCN"),
        ClassMember(class_id=cls2.id, user_id=sv_other.id, member_role="STUDENT"),
        ClassMember(class_id=cls2.id, user_id=bcs_other.id, member_role="BCS"),
    ]
    db.add_all(mems)
    db.flush()

    # Campaign for LOP-DEMO
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id="camp1111-1111-1111-1111-111111111111",
        class_id=cls1.id,
        title="Đợt ĐRL Học kỳ 1",
        term="HK1-2026",
        status="OPEN",
        open_at=now - timedelta(days=2),
        submission_deadline_at=now + timedelta(days=5),
        supplement_period_hours=48,
        appeal_period_hours=72,
        reminder_after_hours=48,
        max_info_rounds=2,
        max_proof_rounds=2,
        opened_at=now - timedelta(days=2),
        created_by=admin1.id,
    )
    db.add(camp)
    db.flush()

    crit1 = Criterion(id="crit1111-1111-1111-1111-111111111111", campaign_id=camp.id, code="TC01", title="Ý thức học tập", description="Demo", max_score=Decimal("10.00"), requires_evidence=True, sort_order=1)
    crit2 = Criterion(id="crit1111-1111-1111-1111-111111111112", campaign_id=camp.id, code="TC02", title="Kỷ luật và nội quy", description="Demo", max_score=Decimal("10.00"), requires_evidence=False, sort_order=2)
    crit3 = Criterion(id="crit1111-1111-1111-1111-111111111113", campaign_id=camp.id, code="TC03", title="Hoạt động phong trào", description="Demo", max_score=Decimal("10.00"), requires_evidence=True, sort_order=3)
    db.add_all([crit1, crit2, crit3])
    db.flush()

    # Initialize cases for SV1, SV2, SV3
    cases = []
    for u in [sv1, sv2, sv3]:
        c = Case(
            id=f"case1111-{u.username}-1111-111111111111",
            campaign_id=camp.id,
            student_id=u.id,
            status="DRAFT",
            version=1,
            info_round=0,
            proof_round=0,
            created_at=now,
        )
        db.add(c)
        db.flush()
        cases.append(c)

        for cr in [crit1, crit2, crit3]:
            claim = Claim(
                case_id=c.id,
                criterion_id=cr.id,
                self_score=None,
                student_note=None,
                created_at=now,
            )
            db.add(claim)

    db.commit()

    return {
        "class_demo": cls1,
        "class_other": cls2,
        "campaign": camp,
        "criteria": [crit1, crit2, crit3],
        "users": {
            "sv001": sv1,
            "sv002": sv2,
            "sv003": sv3,
            "bcs001": bcs1,
            "gvcn001": gvcn1,
            "admin001": admin1,
            "sv_other": sv_other,
            "bcs_other": bcs_other,
        },
        "cases": cases,
    }


def login_helper(client: TestClient, username: str, password: str = "Demo@123456"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    data = resp.json()
    csrf_token = data["csrf_token"]
    cookies = resp.cookies
    headers = {"X-CSRF-Token": csrf_token}
    return {"cookies": cookies, "headers": headers, "user": data["user"]}
