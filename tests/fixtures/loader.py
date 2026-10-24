"""
Utility loader for test contracts, seed fixtures, and specifications.
Package D: Acceptance Testing & Verification.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = ROOT_DIR / "contracts"


def get_contracts_dir() -> Path:
    return CONTRACTS_DIR


def load_openapi_spec() -> Dict[str, Any]:
    """Load and parse the OpenAPI 3.0.3 contract."""
    spec_path = CONTRACTS_DIR / "openapi.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"OpenAPI spec not found at: {spec_path}")
    with open(spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seed_fixtures() -> Dict[str, Any]:
    """Load and parse seed fixtures and mock responses."""
    fixtures_path = CONTRACTS_DIR / "seed-fixtures.json"
    if not fixtures_path.exists():
        raise FileNotFoundError(f"Seed fixtures not found at: {fixtures_path}")
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_states_doc() -> str:
    """Load the state machine specification markdown."""
    states_path = CONTRACTS_DIR / "states.md"
    if not states_path.exists():
        raise FileNotFoundError(f"States doc not found at: {states_path}")
    with open(states_path, "r", encoding="utf-8") as f:
        return f.read()
