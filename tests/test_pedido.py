import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestPedido:
    ENDPOINT = "/api/v1/pedidos"

    @pytest.fixture
    def producto_id(self, client: TestClient, admin_token) -> int:
        _as(client, admin_token)
        resp = client.post("/api/v1/productos", json={
            "nombre": "Hamburguesa Clásica",
            "descripcion": "Carne, queso, lechuga y tomate",
            "precio_base": 100.00,
            "stock_cantidad": 10,
            "disponible": True,
        })
        return resp.json()["id"]

    @pytest.fixture
    def direccion_id(self, client: TestClient, client_token) -> int:
        _as(client, client_token)
        resp = client.post("/api/v1/direcciones", json={
            "alias": "Casa",
            "linea1": "Av. Siempre Viva 123",
            "ciudad": "Springfield",
            "provincia": "Buenos Aires",
            "codigo_postal": "1900",
            "es_principal": True,
        })
        return resp.json()["id"]

    def test_crear_pedido_retiro(self, client: TestClient, client_token, producto_id,
                                  forma_pago_id):
        _as(client, client_token)
        resp = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 2}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["modalidad_entrega"] == "RETIRO_LOCAL"
        assert data["estado_pedido"]["codigo"] == "PENDIENTE"
        assert float(data["total"]) == 200.0
        assert len(data["detalles"]) == 1
        assert len(data["historial_estado_pedido"]) == 1

    def test_crear_pedido_delivery(self, client: TestClient, client_token, producto_id,
                                    forma_pago_id, direccion_id):
        _as(client, client_token)
        resp = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "DELIVERY",
            "forma_pago_id": forma_pago_id,
            "direccion_id": direccion_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["modalidad_entrega"] == "DELIVERY"
        assert data["direccion_id"] == direccion_id

    def test_crear_pedido_delivery_sin_direccion(self, client: TestClient, client_token,
                                                    producto_id, forma_pago_id):
        _as(client, client_token)
        resp = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "DELIVERY",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        assert resp.status_code == 422

    def test_crear_pedido_producto_no_disponible(self, client: TestClient, admin_token,
                                                   client_token, forma_pago_id):
        _as(client, admin_token)
        resp = client.post("/api/v1/productos", json={
            "nombre": "No Disponible",
            "descripcion": "No disponible",
            "precio_base": 50.0,
            "stock_cantidad": 0,
            "disponible": False,
        })
        pid = resp.json()["id"]

        _as(client, client_token)
        resp = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": pid, "cantidad": 1}],
        })
        assert resp.status_code == 400

    def test_crear_pedido_unauthenticated(self, client: TestClient, producto_id, forma_pago_id):
        client.cookies.clear()
        resp = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        assert resp.status_code == 401

    def test_listar_mis_pedidos(self, client: TestClient, client_token, producto_id,
                                  forma_pago_id):
        _as(client, client_token)
        client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        resp = client.get(f"{self.ENDPOINT}/mios")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_obtener_pedido(self, client: TestClient, client_token, producto_id, forma_pago_id):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        pid = created.json()["id"]
        resp = client.get(f"{self.ENDPOINT}/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_obtener_pedido_other_user_admin(self, client: TestClient, client_token,
                                                    admin_token, producto_id, forma_pago_id):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        pid = created.json()["id"]

        _as(client, admin_token)
        resp = client.get(f"{self.ENDPOINT}/{pid}")
        assert resp.status_code == 200

    def test_obtener_pedido_not_found(self, client: TestClient, client_token):
        _as(client, client_token)
        resp = client.get(f"{self.ENDPOINT}/99999")
        assert resp.status_code == 404

    def test_cancelar_pedido(self, client: TestClient, client_token, producto_id, forma_pago_id):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        pid = created.json()["id"]
        resp = client.patch(f"{self.ENDPOINT}/{pid}/cancelar")
        assert resp.status_code == 200
        assert resp.json()["estado_pedido"]["codigo"] == "CANCELADO"

    def test_listar_todos_admin(self, client: TestClient, admin_token, client_token, producto_id,
                                  forma_pago_id):
        _as(client, client_token)
        client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })

        _as(client, admin_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_listar_todos_forbidden_client(self, client: TestClient, client_token):
        _as(client, client_token)
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 403

    def test_avanzar_estado(self, client: TestClient, admin_token, client_token,
                              producto_id, forma_pago_id):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        pid = created.json()["id"]

        _as(client, admin_token)
        resp = client.patch(f"{self.ENDPOINT}/{pid}/avanzar")
        assert resp.status_code == 200
        assert resp.json()["estado_pedido"]["codigo"] == "CONFIRMADO"

    def test_avanzar_estado_forbidden_client(self, client: TestClient, client_token,
                                               producto_id, forma_pago_id):
        _as(client, client_token)
        created = client.post(self.ENDPOINT, json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        pid = created.json()["id"]
        resp = client.patch(f"{self.ENDPOINT}/{pid}/avanzar")
        assert resp.status_code == 403
