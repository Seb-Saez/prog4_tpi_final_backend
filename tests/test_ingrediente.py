import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestIngredienteCRUD:
    ENDPOINT = "/api/v1/ingredientes"

    def _seed_ingrediente(self, client, nombre="Queso", es_alergeno=False):
        resp = client.post(self.ENDPOINT, json={
            "nombre": nombre,
            "descripcion": nombre,
            "es_alergeno": es_alergeno,
        })
        assert resp.status_code == 201, resp.text
        return resp.json()

    def test_create_ingrediente(self, client: TestClient, admin_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Queso",
            "descripcion": "Queso mozzarella",
            "es_alergeno": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Queso"
        assert data["es_alergeno"] is True

    def test_create_ingrediente_forbidden_client(self, client: TestClient, client_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Queso", "descripcion": "Queso", "es_alergeno": False,
        })
        assert resp.status_code == 403

    def test_list_ingredientes(self, client: TestClient, admin_headers, client_token):
        self._seed_ingrediente(client, "Lechuga", False)
        self._seed_ingrediente(client, "Maní", True)
        _as(client, client_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_list_ingredientes_filter_alergeno(self, client: TestClient, admin_headers, client_token):
        self._seed_ingrediente(client, "Alérgeno1", True)
        _as(client, client_token)
        resp = client.get(f"{self.ENDPOINT}?es_alergeno=true")
        assert resp.status_code == 200
        assert all(i["es_alergeno"] is True for i in resp.json())

    def test_get_ingrediente_by_id(self, client: TestClient, admin_headers, client_token):
        ing = self._seed_ingrediente(client, "Tomate", False)
        _as(client, client_token)
        resp = client.get(f"{self.ENDPOINT}/{ing['id']}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Tomate"

    def test_get_ingrediente_not_found(self, client: TestClient, client_headers):
        resp = client.get(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_list_ingredientes_public(self, client: TestClient, admin_headers):
        # Los ingredientes (info de alérgenos) son públicos para el catálogo.
        self._seed_ingrediente(client, "Lechuga", False)
        client.cookies.clear()  # anónimo
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_ingrediente_public(self, client: TestClient, admin_headers):
        ing = self._seed_ingrediente(client, "Tomate", False)
        client.cookies.clear()  # anónimo
        resp = client.get(f"{self.ENDPOINT}/{ing['id']}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Tomate"

    def test_update_ingrediente(self, client: TestClient, admin_headers):
        ing = self._seed_ingrediente(client, "Cebolla", False)
        resp = client.patch(f"{self.ENDPOINT}/{ing['id']}", json={
            "es_alergeno": True,
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["es_alergeno"] is True

    def test_update_ingrediente_forbidden_client(self, client: TestClient, admin_headers, client_token):
        ing = self._seed_ingrediente(client, "Test", False)
        _as(client, client_token)
        resp = client.patch(f"{self.ENDPOINT}/{ing['id']}", json={
            "nombre": "Hacked",
        })
        assert resp.status_code == 403

    def test_delete_ingrediente(self, client: TestClient, admin_headers):
        ing = self._seed_ingrediente(client, "ToDelete", False)
        resp = client.delete(f"{self.ENDPOINT}/{ing['id']}")
        assert resp.status_code == 204

    def test_delete_ingrediente_not_found(self, client: TestClient, admin_headers):
        resp = client.delete(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_delete_ingrediente_forbidden_client(self, client: TestClient, admin_headers, client_token):
        ing = self._seed_ingrediente(client, "NoDel", False)
        _as(client, client_token)
        resp = client.delete(f"{self.ENDPOINT}/{ing['id']}")
        assert resp.status_code == 403
