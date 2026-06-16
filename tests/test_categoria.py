import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestCategoriaCRUD:
    ENDPOINT = "/api/v1/categorias"

    def _seed_categoria(self, client, nombre="Bebidas", descripcion="Bebidas frías"):
        resp = client.post(self.ENDPOINT, json={
            "nombre": nombre, "descripcion": descripcion,
        })
        assert resp.status_code == 201
        return resp.json()

    def test_create_categoria(self, client: TestClient, admin_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Bebidas",
            "descripcion": "Bebidas frías y calientes",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Bebidas"

    def test_create_categoria_forbidden_client(self, client: TestClient, client_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Bebidas",
            "descripcion": "Desc",
        })
        assert resp.status_code == 403

    def test_create_categoria_unauthenticated(self, client: TestClient):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Bebidas",
            "descripcion": "Desc",
        })
        assert resp.status_code == 401

    def test_list_categorias(self, client: TestClient, admin_headers, client_token):
        self._seed_categoria(client, "Bebidas", "Bebidas")
        self._seed_categoria(client, "Comidas", "Comidas")
        _as(client, client_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_get_categoria_by_id(self, client: TestClient, admin_headers, client_token):
        cat = self._seed_categoria(client, "Postres", "Dulces")
        _as(client, client_token)
        resp = client.get(f"{self.ENDPOINT}/{cat['id']}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Postres"

    def test_get_categoria_not_found(self, client: TestClient, client_headers):
        resp = client.get(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_update_categoria(self, client: TestClient, admin_headers, client_token):
        cat = self._seed_categoria(client, "Snacks", "Salados")
        resp = client.patch(f"{self.ENDPOINT}/{cat['id']}", json={
            "nombre": "Snacks Actualizados",
        })
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Snacks Actualizados"

    def test_update_categoria_forbidden_client(self, client: TestClient, admin_headers, client_token):
        cat = self._seed_categoria(client, "Test", "Test")
        _as(client, client_token)
        resp = client.patch(f"{self.ENDPOINT}/{cat['id']}", json={
            "nombre": "Hacked",
        })
        assert resp.status_code == 403

    def test_update_categoria_not_found(self, client: TestClient, admin_headers):
        resp = client.patch(f"{self.ENDPOINT}/99999", json={
            "nombre": "Nope",
        })
        assert resp.status_code == 404

    def test_delete_categoria(self, client: TestClient, admin_headers):
        cat = self._seed_categoria(client, "ToDelete", "Bye")
        resp = client.delete(f"{self.ENDPOINT}/{cat['id']}")
        assert resp.status_code == 204

    def test_delete_categoria_forbidden_client(self, client: TestClient, admin_headers, client_token):
        cat = self._seed_categoria(client, "NoDel", "Desc")
        _as(client, client_token)
        resp = client.delete(f"{self.ENDPOINT}/{cat['id']}")
        assert resp.status_code == 403

    def test_delete_categoria_not_found(self, client: TestClient, admin_headers):
        resp = client.delete(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404
