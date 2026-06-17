import pytest
from fastapi.testclient import TestClient


class TestUnidadMedidaCRUD:
    ENDPOINT = "/api/v1/unidades-medida"

    def test_create_unidad(self, client: TestClient, session):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Kilogramo",
            "simbolo": "kg",
            "tipo": "MASA",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Kilogramo"
        assert data["id"] > 0

    def test_list_unidades(self, client: TestClient, session):
        client.post(self.ENDPOINT, json={
            "nombre": "Gramo", "simbolo": "g", "tipo": "MASA",
        })
        client.post(self.ENDPOINT, json={
            "nombre": "Unidad", "simbolo": "u", "tipo": "UNIDAD",
        })
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_get_unidad_by_id(self, client: TestClient, session):
        created = client.post(self.ENDPOINT, json={
            "nombre": "Litro", "simbolo": "L", "tipo": "VOLUMEN",
        })
        uid = created.json()["id"]
        resp = client.get(f"{self.ENDPOINT}/{uid}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Litro"

    def test_get_unidad_not_found(self, client: TestClient):
        resp = client.get(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_update_unidad(self, client: TestClient, session):
        created = client.post(self.ENDPOINT, json={
            "nombre": "Mililitro", "simbolo": "ml", "tipo": "VOLUMEN",
        })
        uid = created.json()["id"]
        resp = client.patch(f"{self.ENDPOINT}/{uid}", json={
            "simbolo": "mL",
        })
        assert resp.status_code == 200
        assert resp.json()["simbolo"] == "mL"

    def test_update_unidad_not_found(self, client: TestClient):
        resp = client.patch(f"{self.ENDPOINT}/99999", json={
            "nombre": "Nope",
        })
        assert resp.status_code == 404

    def test_update_unidad_simbolo_too_long_returns_422(self, client: TestClient, session):
        # Las columnas son VARCHAR(50/10/20). Un valor más largo debe rechazarse
        # en el borde (422), no llegar a la DB y reventar con un 500.
        created = client.post(self.ENDPOINT, json={
            "nombre": "Mililitro", "simbolo": "ml", "tipo": "VOLUMEN",
        })
        uid = created.json()["id"]
        resp = client.patch(f"{self.ENDPOINT}/{uid}", json={
            "simbolo": "A" * 15,  # excede max_length=10
        })
        assert resp.status_code == 422

    def test_create_unidad_simbolo_too_long_returns_422(self, client: TestClient, session):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Kilogramo", "simbolo": "A" * 15, "tipo": "MASA",
        })
        assert resp.status_code == 422

    def test_delete_unidad(self, client: TestClient, session):
        created = client.post(self.ENDPOINT, json={
            "nombre": "ToDelete", "simbolo": "x", "tipo": "OTRO",
        })
        uid = created.json()["id"]
        resp = client.delete(f"{self.ENDPOINT}/{uid}")
        if resp.status_code == 204:
            get_resp = client.get(f"{self.ENDPOINT}/{uid}")
            assert get_resp.status_code == 404
        else:
            assert resp.status_code == 204

    def test_delete_unidad_not_found(self, client: TestClient):
        resp = client.delete(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404
