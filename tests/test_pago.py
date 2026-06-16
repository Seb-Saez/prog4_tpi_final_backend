import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


@pytest.fixture
def mock_mp_sdk():
    with patch("app.modules.pago.service.mercadopago.SDK") as mock:
        instance = mock.return_value
        pref = instance.preference.return_value
        pref.create.return_value = {
            "status": 201,
            "response": {
                "id": "pref_test_123",
                "init_point": "https://www.mercadopago.com.ar/checkout?pref_id=pref_test_123",
            },
        }
        pref.get.return_value = {
            "status": 200,
            "response": {
                "init_point": "https://www.mercadopago.com.ar/checkout?pref_id=pref_test_123",
            },
        }
        merch = instance.merchant_order.return_value
        merch.get.return_value = {
            "status": 200,
            "response": {
                "payments": [{"id": "456"}],
            },
        }
        pay = instance.payment.return_value
        pay.get.return_value = {
            "status": 200,
            "response": {
                "id": "456",
                "external_reference": None,
                "status": "approved",
            },
        }
        yield mock


class TestPagoPreferencia:
    ENDPOINT = "/api/v1/pagos"

    @pytest.fixture
    def producto_id(self, client: TestClient, admin_token) -> int:
        _as(client, admin_token)
        resp = client.post("/api/v1/productos", json={
            "nombre": "Hamburguesa Clásica",
            "descripcion": "Carne y queso",
            "precio_base": 100.00,
            "stock_cantidad": 10,
            "disponible": True,
        })
        return resp.json()["id"]

    @pytest.fixture
    def pedido_id(self, client: TestClient, client_token, producto_id,
                  forma_pago_id) -> int:
        _as(client, client_token)
        resp = client.post("/api/v1/pedidos", json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": 2}],
        })
        return resp.json()["id"]

    def test_crear_preferencia_ok(self, client: TestClient, client_token,
                                  pedido_id, mock_mp_sdk):
        _as(client, client_token)
        resp = client.post(f"{self.ENDPOINT}/preferencia/{pedido_id}")
        assert resp.status_code == 201
        data = resp.json()
        assert "init_point" in data
        assert "preference_id" in data
        assert data["preference_id"] == "pref_test_123"

    def test_crear_preferencia_pedido_ya_tiene(self, client: TestClient,
                                                client_token, pedido_id,
                                                mock_mp_sdk):
        _as(client, client_token)
        resp1 = client.post(f"{self.ENDPOINT}/preferencia/{pedido_id}")
        assert resp1.status_code == 201

        sdk = mock_mp_sdk.return_value
        sdk.preference.return_value.create.reset_mock()

        resp2 = client.post(f"{self.ENDPOINT}/preferencia/{pedido_id}")
        assert resp2.status_code == 201
        data = resp2.json()
        assert data["preference_id"] == "pref_test_123"

    def test_crear_preferencia_other_user_forbidden(
            self, client: TestClient, client_token, admin_token, pedido_id,
            mock_mp_sdk):
        _as(client, admin_token)
        resp = client.post(f"{self.ENDPOINT}/preferencia/{pedido_id}")
        assert resp.status_code == 403

    def test_crear_preferencia_pedido_not_found(
            self, client: TestClient, client_token, mock_mp_sdk):
        _as(client, client_token)
        resp = client.post(f"{self.ENDPOINT}/preferencia/99999")
        assert resp.status_code == 404

    def test_crear_preferencia_unauthenticated(
            self, client: TestClient, pedido_id, mock_mp_sdk):
        client.cookies.clear()
        resp = client.post(f"{self.ENDPOINT}/preferencia/{pedido_id}")
        assert resp.status_code == 401

    def test_crear_preferencia_mp_error(self, client: TestClient, client_token,
                                         pedido_id, mock_mp_sdk):
        sdk = mock_mp_sdk.return_value
        sdk.preference.return_value.create.return_value = {
            "status": 400,
            "response": {"error": "bad request"},
        }
        _as(client, client_token)
        resp = client.post(f"{self.ENDPOINT}/preferencia/{pedido_id}")
        assert resp.status_code == 502


class TestPagoWebhook:
    ENDPOINT = "/api/v1/pagos/webhook"

    def test_webhook_payment_ignora_si_no_hay_external_ref(
            self, client: TestClient, mock_mp_sdk):
        data = {"topic": "payment", "id": "456"}
        resp = client.post(self.ENDPOINT, params=data)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_webhook_merchant_order_ignora_sin_external_ref(
            self, client: TestClient, mock_mp_sdk):
        data = {"topic": "merchant_order", "id": "789"}
        resp = client.post(self.ENDPOINT, params=data)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_webhook_unknown_topic_ignored(
            self, client: TestClient, mock_mp_sdk):
        resp = client.post(self.ENDPOINT, params={"topic": "something_else"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_webhook_sin_datos(self, client: TestClient, mock_mp_sdk):
        resp = client.post(self.ENDPOINT)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestPagoRedirect:
    ENDPOINT = "/pago/resultado"

    def test_redirect(self, client: TestClient):
        resp = client.get(
            self.ENDPOINT,
            params={"status": "success", "pedido_id": "42"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        location = resp.headers["location"]
        assert "status=success" in location
        assert "pedido_id=42" in location

    def test_redirect_missing_params(self, client: TestClient):
        resp = client.get(self.ENDPOINT, follow_redirects=False)
        assert resp.status_code == 422
