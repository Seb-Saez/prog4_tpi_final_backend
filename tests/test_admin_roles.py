import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestAdminRoles:
    ENDPOINT_ROLES = "/api/v1/admin/roles"

    def test_list_roles_admin(self, client: TestClient, admin_headers):
        resp = client.get(self.ENDPOINT_ROLES)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        codigos = {r["codigo"] for r in data}
        assert "ADMIN" in codigos
        assert "CLIENT" in codigos
        assert "COCINA" in codigos
        assert "CAJA" in codigos

    def test_list_roles_forbidden_client(self, client: TestClient, client_headers):
        resp = client.get(self.ENDPOINT_ROLES)
        assert resp.status_code == 403

    def test_assign_role_to_user(self, client: TestClient, admin_headers):
        reg = client.post("/api/v1/auth/register", json={
            "username": "role_user",
            "email": "role@mail.com",
            "password": "Secret1234!",
            "full_name": "Role User",
        })
        uid = reg.json()["id"]
        resp = client.post(f"/api/v1/admin/usuarios/{uid}/roles", json={
            "rol_codigo": "CAJA",
        })
        assert resp.status_code == 200
        assert "CAJA" in resp.json()["roles"]

    def test_assign_role_forbidden_client(self, client: TestClient, admin_token, client_token):
        reg = client.post("/api/v1/auth/register", json={
            "username": "role_user2",
            "email": "role2@mail.com",
            "password": "Secret1234!",
            "full_name": "Role User 2",
        })
        uid = reg.json()["id"]
        _as(client, client_token)
        resp = client.post(f"/api/v1/admin/usuarios/{uid}/roles", json={
            "rol_codigo": "CAJA",
        })
        assert resp.status_code == 403

    def test_assign_nonexistent_role(self, client: TestClient, admin_headers):
        reg = client.post("/api/v1/auth/register", json={
            "username": "role_user3",
            "email": "role3@mail.com",
            "password": "Secret1234!",
            "full_name": "Role User 3",
        })
        uid = reg.json()["id"]
        resp = client.post(f"/api/v1/admin/usuarios/{uid}/roles", json={
            "rol_codigo": "FAKE_ROLE",
        })
        assert resp.status_code == 404

    def test_remove_role_from_user(self, client: TestClient, admin_headers):
        reg = client.post("/api/v1/auth/register", json={
            "username": "remove_role",
            "email": "removerole@mail.com",
            "password": "Secret1234!",
            "full_name": "Remove Role",
        })
        uid = reg.json()["id"]

        client.post(f"/api/v1/admin/usuarios/{uid}/roles", json={
            "rol_codigo": "CAJA",
        })
        resp = client.delete(f"/api/v1/admin/usuarios/{uid}/roles/CAJA")
        assert resp.status_code == 200
        assert "CAJA" not in resp.json()["roles"]

    def test_remove_role_forbidden_client(self, client: TestClient, admin_token, client_token):
        reg = client.post("/api/v1/auth/register", json={
            "username": "remove_role2",
            "email": "removerole2@mail.com",
            "password": "Secret1234!",
            "full_name": "Remove Role 2",
        })
        uid = reg.json()["id"]

        _as(client, client_token)
        resp = client.delete(f"/api/v1/admin/usuarios/{uid}/roles/CAJA")
        assert resp.status_code == 403
