import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestProductoCRUD:
    ENDPOINT = "/api/v1/productos"

    def _seed_producto(self, client, nombre="Pizza", precio_base=200.0):
        resp = client.post(self.ENDPOINT, json={
            "nombre": nombre,
            "descripcion": nombre,
            "precio_base": precio_base,
            "stock_cantidad": 5,
            "disponible": True,
        })
        assert resp.status_code == 201, resp.text
        return resp.json()

    def test_create_producto(self, client: TestClient, admin_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Hamburguesa Clásica",
            "descripcion": "Carne, queso, lechuga y tomate",
            "precio_base": 100.00,
            "stock_cantidad": 10,
            "disponible": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Hamburguesa Clásica"
        assert data["precio_base"] == 100.0

    def test_create_producto_forbidden_client(self, client: TestClient, client_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Hamburguesa",
            "descripcion": "Desc",
            "precio_base": 100.0,
            "stock_cantidad": 5,
            "disponible": True,
        })
        assert resp.status_code == 403

    def test_create_producto_zero_stock_not_disponible(self, client: TestClient, admin_headers):
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Sin Stock",
            "descripcion": "No hay",
            "precio_base": 50.0,
            "stock_cantidad": 0,
            "disponible": True,
        })
        assert resp.status_code == 201, resp.text
        assert resp.json()["disponible"] is False

    def test_list_productos(self, client: TestClient, admin_headers, client_token):
        self._seed_producto(client, "Pizza", 200.0)
        self._seed_producto(client, "Empanada", 50.0)
        _as(client, client_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_list_productos_filter_disponible(self, client: TestClient, admin_headers, client_token):
        self._seed_producto(client, "Disponible1", 10.0)
        _as(client, client_token)
        resp = client.get(f"{self.ENDPOINT}?disponible=true")
        assert resp.status_code == 200
        assert all(p["disponible"] is True for p in resp.json())

    def test_get_producto_by_id(self, client: TestClient, admin_headers, client_token):
        prod = self._seed_producto(client, "Hamburguesa Clásica", 100.0)
        _as(client, client_token)
        resp = client.get(f"{self.ENDPOINT}/{prod['id']}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Hamburguesa Clásica"

    def test_get_producto_not_found(self, client: TestClient, client_headers):
        resp = client.get(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_list_productos_public(self, client: TestClient, admin_headers):
        # El catálogo es navegable sin sesión: invitado puede listar productos.
        self._seed_producto(client, "Pizza", 200.0)
        client.cookies.clear()  # anónimo
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_producto_public(self, client: TestClient, admin_headers):
        # El detalle de producto también es público.
        prod = self._seed_producto(client, "Hamburguesa", 100.0)
        client.cookies.clear()  # anónimo
        resp = client.get(f"{self.ENDPOINT}/{prod['id']}")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Hamburguesa"

    def test_update_producto(self, client: TestClient, admin_headers):
        prod = self._seed_producto(client, "Hamburguesa Clásica", 100.0)
        resp = client.patch(f"{self.ENDPOINT}/{prod['id']}", json={
            "precio_base": 120.0,
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["precio_base"] == 120.0

    def test_update_producto_forbidden_client(self, client: TestClient, admin_headers, client_token):
        prod = self._seed_producto(client, "Test", 50.0)
        _as(client, client_token)
        resp = client.patch(f"{self.ENDPOINT}/{prod['id']}", json={
            "nombre": "Hacked",
        })
        assert resp.status_code == 403

    def test_update_producto_not_found(self, client: TestClient, admin_headers):
        resp = client.patch(f"{self.ENDPOINT}/99999", json={
            "nombre": "Nope",
        })
        assert resp.status_code == 404

    def test_delete_producto(self, client: TestClient, admin_headers):
        prod = self._seed_producto(client, "ToDelete", 50.0)
        resp = client.delete(f"{self.ENDPOINT}/{prod['id']}")
        assert resp.status_code == 204

    def test_delete_producto_forbidden_client(self, client: TestClient, admin_headers, client_token):
        prod = self._seed_producto(client, "NoDel", 50.0)
        _as(client, client_token)
        resp = client.delete(f"{self.ENDPOINT}/{prod['id']}")
        assert resp.status_code == 403

    def test_delete_producto_not_found(self, client: TestClient, admin_headers):
        resp = client.delete(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404
