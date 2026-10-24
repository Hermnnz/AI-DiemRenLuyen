"""
API Client helper for Acceptance Testing & Integration.
Manages session cookies, CSRF tokens, and role-based authentications.
"""
import os
from typing import Any, Dict, Optional
from fastapi.testclient import TestClient

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo@123456")


class AcceptanceTestClient:
    """Black-box HTTP client for testing the API contract and user journeys."""

    def __init__(self, app=None):
        if app is None:
            from api.app.main import app as fastapi_app
            self.app = fastapi_app
        else:
            self.app = app
        self.client = TestClient(self.app)
        self.csrf_token: Optional[str] = None
        self.current_user: Optional[Dict[str, Any]] = None

    def login(self, username: str, password: str = DEMO_PASSWORD) -> Dict[str, Any]:
        """Authenticate as a demo user and capture session cookie & CSRF token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            self.csrf_token = data.get("csrf_token")
            self.current_user = data.get("user")
        return response.json()

    def logout(self):
        """Clear session and authentication state."""
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        self.client.post("/api/v1/auth/logout", headers=headers)
        self.csrf_token = None
        self.current_user = None

    def login_as_student(self, username: str = "sv001"):
        return self.login(username=username)

    def login_as_bcs(self, username: str = "bcs001"):
        return self.login(username=username)

    def login_as_gvcn(self, username: str = "gvcn001"):
        return self.login(username=username)

    def login_as_admin(self, username: str = "admin001"):
        return self.login(username=username)

    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None, require_csrf: bool = False) -> Dict[str, str]:
        req_headers = dict(headers or {})
        if require_csrf and self.csrf_token and "X-CSRF-Token" not in req_headers:
            req_headers["X-CSRF-Token"] = self.csrf_token
        return req_headers

    def get(self, path: str, **kwargs):
        headers = self._prepare_headers(kwargs.pop("headers", None))
        return self.client.get(path, headers=headers, **kwargs)

    def post(self, path: str, **kwargs):
        headers = self._prepare_headers(kwargs.pop("headers", None), require_csrf=True)
        return self.client.post(path, headers=headers, **kwargs)

    def put(self, path: str, **kwargs):
        headers = self._prepare_headers(kwargs.pop("headers", None), require_csrf=True)
        return self.client.put(path, headers=headers, **kwargs)

    def delete(self, path: str, **kwargs):
        headers = self._prepare_headers(kwargs.pop("headers", None), require_csrf=True)
        return self.client.delete(path, headers=headers, **kwargs)
