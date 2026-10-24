"""
Pytest configuration and shared fixtures for Package D tests.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest

# Ensure repo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.fixtures.loader import load_openapi_spec, load_seed_fixtures, load_states_doc
from tests.fixtures.client import AcceptanceTestClient, DEMO_PASSWORD


def pytest_configure(config):
    config.addinivalue_line("markers", "contract: Tests validating OpenAPI, fixtures, and state machine contracts")
    config.addinivalue_line("markers", "acceptance: Acceptance tests for the 16 criteria defined in Section 9")
    config.addinivalue_line("markers", "pending_backend: Tests marked as waiting for Phase 2 backend/UI integration")


@pytest.fixture(scope="session")
def openapi_spec():
    return load_openapi_spec()


@pytest.fixture(scope="session")
def seed_fixtures():
    return load_seed_fixtures()


@pytest.fixture(scope="session")
def states_doc():
    return load_states_doc()


@pytest.fixture(scope="session")
def demo_users(seed_fixtures):
    return {u["username"]: u for u in seed_fixtures["seed_data"]["users"]}


@pytest.fixture
def api_client():
    return AcceptanceTestClient()


@pytest.fixture(autouse=True)
def clean_db_for_acceptance_tests(request):
    """
    Tự động dọn dẹp và reset cơ sở dữ liệu về trạng thái sạch cho mỗi bài kiểm thử chấp nhận E2E.
    Đảm bảo tính cô lập (test isolation) giữa 16 kịch bản.
    """
    # Chỉ chạy đối với các test trong thư mục tests/e2e
    test_path = str(request.fspath)
    if "tests" in test_path and "e2e" in test_path:
        from api.app.database import SessionLocal
        from api.app.models import (
            Campaign,
            Case,
            Claim,
            EvidenceFile,
            SupplementRequest,
            Appeal,
            Meeting,
            ScoreSnapshot,
            Notification,
            AuditEvent,
        )
        from api.app.services.workflow_service import initialize_campaign_cases

        db = SessionLocal()
        try:
            db.query(Appeal).delete()
            db.query(ScoreSnapshot).delete()
            db.query(SupplementRequest).delete()
            db.query(EvidenceFile).delete()
            db.query(Claim).delete()
            db.query(Case).delete()
            db.query(Meeting).delete()
            db.query(Notification).delete()
            db.query(AuditEvent).delete()

            campaign = db.query(Campaign).first()
            if campaign:
                campaign.status = "OPEN"
                campaign.opened_at = datetime(2026, 10, 25, 0, 0, 0, tzinfo=timezone.utc)
                initialize_campaign_cases(db, campaign)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    yield
