"""Tests for POST /api/v1/admin/usuarios — admin user creation with roles."""
import pytest
from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/admin/usuarios"


class TestAdminCreateUser:
    def _payload(self, suffix: str = "1", roles: list[str] | None = None) -> dict:
        return {
            "username": f"newuser_{suffix}",
            "full_name": f"New User {suffix}",
            "email": f"newuser_{suffix}@mail.com",
            "password": "Secret1234!",
            "roles": roles if roles is not None else ["CLIENT"],
        }

    def test_admin_creates_user_with_cocina_role(
        self, client: TestClient, admin_headers: dict
    ):
        resp = client.post(ENDPOINT, json=self._payload("cocina", ["COCINA"]))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "newuser_cocina"
        assert "COCINA" in data["roles"]

    def test_admin_creates_user_with_multiple_roles(
        self, client: TestClient, admin_headers: dict
    ):
        resp = client.post(ENDPOINT, json=self._payload("multi", ["COCINA", "CAJA"]))
        assert resp.status_code == 201, resp.text
        roles = resp.json()["roles"]
        assert "COCINA" in roles
        assert "CAJA" in roles

    def test_duplicate_email_rejected(
        self, client: TestClient, admin_headers: dict
    ):
        payload = self._payload("dup")
        client.post(ENDPOINT, json=payload)
        resp = client.post(ENDPOINT, json=payload)
        assert resp.status_code == 409, resp.text

    def test_non_admin_forbidden(
        self, client: TestClient, client_headers: dict
    ):
        resp = client.post(ENDPOINT, json=self._payload("forbidden"))
        assert resp.status_code == 403, resp.text
