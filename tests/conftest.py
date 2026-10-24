"""
Pytest configuration and shared fixtures for Package D tests.
"""
import os
import sys
from pathlib import Path
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
