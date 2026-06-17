import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


@pytest.fixture
def mock_ws_auth_admin():
    with patch("app.modules.ws.router.decode_access_token") as mock_decode:
        mock_decode.return_value = {"sub": "admin", "roles": ["ADMIN"]}
        with patch("app.modules.ws.router.Session") as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = MagicMock(id=1)
            yield


@pytest.fixture
def mock_ws_auth_client():
    with patch("app.modules.ws.router.decode_access_token") as mock_decode:
        mock_decode.return_value = {"sub": "testuser", "roles": []}
        with patch("app.modules.ws.router.Session") as mock_session:
            mock_session.return_value.__enter__.return_value.exec.return_value.first.return_value = MagicMock(id=2)
            yield


class TestWsPedidos:

    def test_conectar_con_token_valido(self, client: TestClient,
                                        mock_ws_auth_admin):
        _as(client, "fake-token")
        with client.websocket_connect("/ws/pedidos") as ws:
            ws.send_json({"action": "subscribe-order", "order_id": 1})
            data = ws.receive_json()
            assert data["event"] == "SUBSCRIBED"
            assert data["data"]["order_id"] == 1

    def test_conectar_sin_token(self, client: TestClient):
        client.cookies.clear()
        with pytest.raises(Exception) as exc:
            with client.websocket_connect("/ws/pedidos"):
                pass

    def test_subscribe_con_order_id_no_entero(self, client: TestClient,
                                                mock_ws_auth_admin):
        _as(client, "fake-token")
        with client.websocket_connect("/ws/pedidos") as ws:
            ws.send_json({"action": "subscribe-order", "order_id": "abc"})
            data = ws.receive_json()
            assert data["event"] == "ERROR"
            assert "entero" in data["data"]["detail"]

    def test_unsubscribe(self, client: TestClient, mock_ws_auth_admin):
        _as(client, "fake-token")
        with client.websocket_connect("/ws/pedidos") as ws:
            ws.send_json({"action": "subscribe-order", "order_id": 1})
            ws.receive_json()
            ws.send_json({"action": "unsubscribe-order", "order_id": 1})
            ws.send_json({"action": "subscribe-order", "order_id": 2})
            data = ws.receive_json()
            assert data["event"] == "SUBSCRIBED"
            assert data["data"]["order_id"] == 2

    def test_subscribe_pedido_no_te_pertenece_cliente(
            self, client: TestClient, mock_ws_auth_client):
        _as(client, "fake-token")
        with client.websocket_connect("/ws/pedidos") as ws:
            ws.send_json({"action": "subscribe-order", "order_id": 999})
            data = ws.receive_json()
            assert data["event"] == "ERROR"
            assert "No puedes suscribirte" in data["data"]["detail"]


class TestWsCocina:

    def test_conectar_staff(self, client: TestClient, mock_ws_auth_admin):
        _as(client, "fake-token")
        with client.websocket_connect("/cocina/ws") as ws:
            ws.send_json({"ping": True})
            data = ws.receive_json()
            assert data["event"] == "PING"

    def test_conectar_staff_rechazado(self, client: TestClient,
                                       mock_ws_auth_client):
        _as(client, "fake-token")
        with pytest.raises(Exception) as exc:
            with client.websocket_connect("/cocina/ws"):
                pass

    def test_conectar_sin_token(self, client: TestClient):
        client.cookies.clear()
        with pytest.raises(Exception) as exc:
            with client.websocket_connect("/cocina/ws"):
                pass
