import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestDireccionCRUD:
    ENDPOINT = "/api/v1/direcciones"

    @pytest.fixture
    def direccion_payload(self):
        return {
            "alias": "Casa",
            "linea1": "Av. Siempre Viva 123",
            "ciudad": "Springfield",
            "provincia": "Buenos Aires",
            "codigo_postal": "1900",
            "es_principal": True,
        }

    def test_create_direccion(self, client: TestClient, client_headers, direccion_payload):
        resp = client.post(self.ENDPOINT, json=direccion_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["alias"] == "Casa"
        assert data["linea1"] == "Av. Siempre Viva 123"
        assert data["usuario_id"] > 0

    def test_create_direccion_unauthenticated(self, client: TestClient, direccion_payload):
        resp = client.post(self.ENDPOINT, json=direccion_payload)
        assert resp.status_code == 401

    def test_list_direcciones(self, client: TestClient, client_headers, direccion_payload):
        client.post(self.ENDPOINT, json=direccion_payload)
        client.post(self.ENDPOINT, json={
            **direccion_payload, "alias": "Trabajo", "es_principal": False,
        })
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_get_direccion_by_id(self, client: TestClient, client_headers, direccion_payload):
        created = client.post(self.ENDPOINT, json=direccion_payload)
        did = created.json()["id"]
        resp = client.get(f"{self.ENDPOINT}/{did}")
        assert resp.status_code == 200
        assert resp.json()["alias"] == "Casa"

    def test_get_direccion_not_found(self, client: TestClient, client_headers):
        resp = client.get(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_get_direccion_other_user(self, client: TestClient, client_token, admin_token,
                                       direccion_payload):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json=direccion_payload)
        did = created.json()["id"]

        _as(client, admin_token)
        resp = client.get(f"{self.ENDPOINT}/{did}")
        assert resp.status_code == 404

    def test_update_direccion(self, client: TestClient, client_headers, direccion_payload):
        created = client.post(self.ENDPOINT, json=direccion_payload)
        did = created.json()["id"]
        resp = client.patch(f"{self.ENDPOINT}/{did}", json={
            "alias": "Nuevo Hogar",
        })
        assert resp.status_code == 200
        assert resp.json()["alias"] == "Nuevo Hogar"

    def test_update_direccion_other_user(self, client: TestClient, client_token, admin_token,
                                           direccion_payload):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json=direccion_payload)
        did = created.json()["id"]

        _as(client, admin_token)
        resp = client.patch(f"{self.ENDPOINT}/{did}", json={
            "alias": "Robado",
        })
        assert resp.status_code == 404

    def test_delete_direccion(self, client: TestClient, client_headers, direccion_payload):
        created = client.post(self.ENDPOINT, json=direccion_payload)
        did = created.json()["id"]
        resp = client.delete(f"{self.ENDPOINT}/{did}")
        assert resp.status_code == 204

    def test_delete_direccion_other_user(self, client: TestClient, client_token, admin_token,
                                           direccion_payload):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json=direccion_payload)
        did = created.json()["id"]

        _as(client, admin_token)
        resp = client.delete(f"{self.ENDPOINT}/{did}")
        assert resp.status_code == 404
