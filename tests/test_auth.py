import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.modules.usuarios.model import Usuario


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestRegister:
    ENDPOINT = "/api/v1/auth/register"

    def test_register_ok(self, client: TestClient):
        resp = client.post(self.ENDPOINT, json={
            "username": "newuser",
            "email": "new@mail.com",
            "password": "Secret1234!",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@mail.com"
        assert data["full_name"] == "New User"
        assert "password" not in data
        assert "CLIENT" in data["roles"]

    def test_register_duplicate_username(self, client: TestClient):
        payload = {
            "username": "dupuser",
            "email": "dup1@mail.com",
            "password": "Secret1234!",
            "full_name": "Dup User",
        }
        resp1 = client.post(self.ENDPOINT, json=payload)
        assert resp1.status_code == 201

        resp2 = client.post(self.ENDPOINT, json=payload)
        assert resp2.status_code == 409

    def test_register_duplicate_email(self, client: TestClient, session: Session):
        first = {
            "username": "user_a",
            "email": "same@mail.com",
            "password": "Secret1234!",
            "full_name": "User A",
        }
        resp1 = client.post(self.ENDPOINT, json=first)
        assert resp1.status_code == 201

        second = {
            "username": "user_b",
            "email": "same@mail.com",
            "password": "Secret1234!",
            "full_name": "User B",
        }
        resp2 = client.post(self.ENDPOINT, json=second)
        assert resp2.status_code == 409

    def test_register_short_password(self, client: TestClient):
        resp = client.post(self.ENDPOINT, json={
            "username": "shortpwd",
            "email": "short@mail.com",
            "password": "1234567",
            "full_name": "Short Pwd",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        resp = client.post(self.ENDPOINT, json={
            "username": "bademail",
            "email": "not-an-email",
            "password": "Secret1234!",
            "full_name": "Bad Email",
        })
        assert resp.status_code == 422


class TestLogin:
    ENDPOINT = "/api/v1/auth/token"

    def test_login_admin_ok(self, client: TestClient, admin_headers):
        assert admin_headers is not None

    def test_login_client_ok(self, client: TestClient):
        client.post("/api/v1/auth/register", json={
            "username": "loginclient",
            "email": "login@mail.com",
            "password": "Secret1234!",
            "full_name": "Login Client",
        })
        resp = client.post(self.ENDPOINT, data={
            "username": "loginclient",
            "password": "Secret1234!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.headers.get("set-cookie", "")

    def test_login_wrong_password(self, client: TestClient):
        resp = client.post(self.ENDPOINT, data={
            "username": "admin",
            "password": "WrongPass1!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post(self.ENDPOINT, data={
            "username": "nobody",
            "password": "SomePass1!",
        })
        assert resp.status_code == 401

    def test_login_disabled_user(self, client: TestClient, admin_token):
        reg = client.post("/api/v1/auth/register", json={
            "username": "disableme",
            "email": "disable@mail.com",
            "password": "Secret1234!",
            "full_name": "Disable Me",
        })
        uid = reg.json()["id"]
        _as(client, admin_token)
        client.post(f"/api/v1/admin/usuarios/{uid}/desactivar")

        resp = client.post(self.ENDPOINT, data={
            "username": "disableme",
            "password": "Secret1234!",
        })
        assert resp.status_code == 400


class TestLogout:
    ENDPOINT = "/api/v1/auth/logout"

    def test_logout_ok(self, client: TestClient, client_headers):
        resp = client.post(self.ENDPOINT)
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie

    def test_logout_unauthenticated(self, client: TestClient):
        resp = client.post(self.ENDPOINT)
        assert resp.status_code == 401


class TestMe:
    ENDPOINT = "/api/v1/auth/me"

    def test_me_ok(self, client: TestClient, client_token):
        _as(client, client_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@mail.com"
        assert "password" not in data

    def test_me_admin(self, client: TestClient, admin_token):
        _as(client, admin_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert "ADMIN" in data["roles"]

    def test_me_unauthenticated(self, client: TestClient):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 401

    def test_me_invalid_token(self, client: TestClient):
        client.cookies.set("access_token", "invalidtoken")
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 401


class TestPrivado:
    ENDPOINT = "/api/v1/auth/privado"

    def test_privado_ok(self, client: TestClient, client_headers):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert "mensaje" in resp.json()

    def test_privado_unauthenticated(self, client: TestClient):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 401


class TestAdminUsers:
    ENDPOINT_LIST = "/api/v1/admin/usuarios"

    def test_list_users_admin(self, client: TestClient, admin_headers):
        resp = client.get(self.ENDPOINT_LIST)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_users_forbidden_client(self, client: TestClient, client_headers):
        resp = client.get(self.ENDPOINT_LIST)
        assert resp.status_code == 403

    def test_deactivate_user(self, client: TestClient, admin_token, client_token):
        reg = client.post("/api/v1/auth/register", json={
            "username": "to_deactivate",
            "email": "todeact@mail.com",
            "password": "Secret1234!",
            "full_name": "To Deactivate",
        })
        uid = reg.json()["id"]

        _as(client, admin_token)
        resp = client.post(f"/api/v1/admin/usuarios/{uid}/desactivar")
        assert resp.status_code == 200
        assert resp.json()["disabled"] is True

    def test_activate_user(self, client: TestClient, admin_token):
        reg = client.post("/api/v1/auth/register", json={
            "username": "to_activate",
            "email": "toact@mail.com",
            "password": "Secret1234!",
            "full_name": "To Activate",
        })
        uid = reg.json()["id"]

        _as(client, admin_token)
        client.post(f"/api/v1/admin/usuarios/{uid}/desactivar")
        resp = client.post(f"/api/v1/admin/usuarios/{uid}/activar")
        assert resp.status_code == 200
        assert resp.json()["disabled"] is False

    def test_deactivate_nonexistent_user(self, client: TestClient, admin_headers):
        resp = client.post("/api/v1/admin/usuarios/99999/desactivar")
        assert resp.status_code == 404
