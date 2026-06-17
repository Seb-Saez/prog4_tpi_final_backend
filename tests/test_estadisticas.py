"""Tests de integración del módulo de estadísticas.

Verifican los KPIs agregados y las reglas de negocio EST-01/EST-03
(los pedidos CANCELADO no se computan en ventas).

Nota: el endpoint /ventas-por-periodo usa func.to_char, específico de
PostgreSQL, por lo que no se ejecuta contra la SQLite in-memory de los tests.
"""
import pytest
from fastapi.testclient import TestClient


def _as(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


class TestEstadisticas:
    BASE = "/api/v1/estadisticas"

    @pytest.fixture
    def producto_id(self, client: TestClient, admin_token) -> int:
        _as(client, admin_token)
        resp = client.post("/api/v1/productos", json={
            "nombre": "Pizza Test",
            "descripcion": "Pizza para estadísticas",
            "precio_base": 150.00,
            "stock_cantidad": 100,
            "disponible": True,
        })
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    def _crear_pedido(self, client, client_token, producto_id, forma_pago_id, cantidad=1):
        _as(client, client_token)
        resp = client.post("/api/v1/pedidos", json={
            "modalidad_entrega": "RETIRO_LOCAL",
            "forma_pago_id": forma_pago_id,
            "items": [{"producto_id": producto_id, "cantidad": cantidad}],
        })
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    # ── Autorización ────────────────────────────────────────────────────────

    def test_resumen_requiere_admin(self, client: TestClient, client_token):
        _as(client, client_token)
        resp = client.get(f"{self.BASE}/resumen")
        assert resp.status_code == 403

    def test_resumen_sin_auth(self, client: TestClient):
        client.cookies.clear()
        resp = client.get(f"{self.BASE}/resumen")
        assert resp.status_code == 401

    # ── Resumen / KPIs ──────────────────────────────────────────────────────

    def test_resumen_ok(self, client: TestClient, admin_token, client_token,
                        producto_id, forma_pago_id):
        self._crear_pedido(client, client_token, producto_id, forma_pago_id, cantidad=2)

        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/resumen")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pedidos"] == 1
        assert float(data["ventas_totales"]) == 300.0
        assert float(data["ticket_promedio"]) == 300.0
        assert data["pedidos_pendientes"] == 1
        assert data["productos_activos"] >= 1

    def test_resumen_excluye_cancelado(self, client: TestClient, admin_token,
                                       client_token, producto_id, forma_pago_id):
        """EST-01: los pedidos CANCELADO no se computan en ventas."""
        # Dos pedidos de 150 c/u
        self._crear_pedido(client, client_token, producto_id, forma_pago_id)
        pid_cancelar = self._crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Cancelar uno (RN-05: con motivo)
        _as(client, client_token)
        resp = client.request(
            "DELETE", f"/api/v1/pedidos/{pid_cancelar}", json={"motivo": "test"}
        )
        assert resp.status_code == 200

        _as(client, admin_token)
        data = client.get(f"{self.BASE}/resumen").json()
        # Solo el pedido no cancelado suma
        assert data["total_pedidos"] == 1
        assert float(data["ventas_totales"]) == 150.0

    # ── Productos más vendidos ──────────────────────────────────────────────

    def test_productos_mas_vendidos(self, client: TestClient, admin_token,
                                    client_token, producto_id, forma_pago_id):
        self._crear_pedido(client, client_token, producto_id, forma_pago_id, cantidad=3)

        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/productos-mas-vendidos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cantidad_vendida"] == 3
        assert float(data[0]["ingresos"]) == 450.0

    def test_productos_mas_vendidos_excluye_cancelado(
        self, client: TestClient, admin_token, client_token, producto_id, forma_pago_id
    ):
        """EST-01: un producto vendido solo en un pedido cancelado no aparece."""
        pid = self._crear_pedido(client, client_token, producto_id, forma_pago_id)
        _as(client, client_token)
        client.request("DELETE", f"/api/v1/pedidos/{pid}", json={"motivo": "test"})

        _as(client, admin_token)
        data = client.get(f"{self.BASE}/productos-mas-vendidos").json()
        assert data == []

    # ── Pedidos por estado ──────────────────────────────────────────────────

    def test_pedidos_por_estado(self, client: TestClient, admin_token,
                                client_token, producto_id, forma_pago_id):
        self._crear_pedido(client, client_token, producto_id, forma_pago_id)

        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/pedidos-por-estado")
        assert resp.status_code == 200
        data = resp.json()
        estados = {row["estado"]: row["cantidad"] for row in data}
        assert estados.get("PENDIENTE") == 1

    # ── Ventas por categoría ────────────────────────────────────────────────

    def test_ventas_por_categoria(self, client: TestClient, admin_token):
        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/ventas-por-categoria")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    # ── Ventas por período (Postgres-only) ──────────────────────────────────

    @pytest.mark.skip(reason="func.to_char es específico de PostgreSQL; no corre en SQLite")
    def test_ventas_por_periodo(self, client: TestClient, admin_token):
        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/ventas-por-periodo")
        assert resp.status_code == 200

    # ── Resumen KPI: ventas_hoy y ventas_mes ─────────────────────────────────

    def test_resumen_incluye_ventas_hoy_y_mes(
        self, client: TestClient, admin_token, client_token, producto_id, forma_pago_id
    ):
        """ventas_hoy y ventas_mes están presentes en el resumen y son Decimal-safe."""
        self._crear_pedido(client, client_token, producto_id, forma_pago_id, cantidad=1)

        _as(client, admin_token)
        data = client.get(f"{self.BASE}/resumen").json()
        assert "ventas_hoy" in data
        assert "ventas_mes" in data
        # El pedido recién creado debe contar en ambos KPIs
        assert float(data["ventas_hoy"]) >= 150.0
        assert float(data["ventas_mes"]) >= 150.0

    def test_resumen_ventas_hoy_excluye_cancelado(
        self, client: TestClient, admin_token, client_token, producto_id, forma_pago_id
    ):
        """EST-01: los pedidos CANCELADO no se suman en ventas_hoy."""
        pid = self._crear_pedido(client, client_token, producto_id, forma_pago_id)
        _as(client, client_token)
        client.request("DELETE", f"/api/v1/pedidos/{pid}", json={"motivo": "test"})

        _as(client, admin_token)
        data = client.get(f"{self.BASE}/resumen").json()
        assert float(data["ventas_hoy"]) == 0.0

    # ── Ingresos por forma de pago ────────────────────────────────────────────

    def test_ingresos_por_forma_pago_requiere_admin(self, client: TestClient, client_token):
        _as(client, client_token)
        resp = client.get(f"{self.BASE}/ingresos-por-forma-pago")
        assert resp.status_code == 403

    def test_ingresos_por_forma_pago_sin_auth(self, client: TestClient):
        client.cookies.clear()
        resp = client.get(f"{self.BASE}/ingresos-por-forma-pago")
        assert resp.status_code == 401

    def test_ingresos_por_forma_pago_agrupa_correctamente(
        self, client: TestClient, admin_token, client_token, producto_id, forma_pago_id
    ):
        """Devuelve al menos un registro agrupado con total y cantidad correctos."""
        self._crear_pedido(client, client_token, producto_id, forma_pago_id, cantidad=2)

        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/ingresos-por-forma-pago")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # Cada ítem debe tener los campos del schema
        for item in data:
            assert "forma_pago" in item
            assert "total" in item
            assert "cantidad" in item
        # El pedido de 2 unidades de $150 = $300 debe aparecer
        totals = {item["forma_pago"]: float(item["total"]) for item in data}
        assert any(v >= 300.0 for v in totals.values())

    def test_ingresos_por_forma_pago_excluye_cancelado(
        self, client: TestClient, admin_token, client_token, producto_id, forma_pago_id
    ):
        """EST-01: los pedidos CANCELADO no se suman en ingresos por forma de pago."""
        pid = self._crear_pedido(client, client_token, producto_id, forma_pago_id)
        _as(client, client_token)
        client.request("DELETE", f"/api/v1/pedidos/{pid}", json={"motivo": "test"})

        _as(client, admin_token)
        resp = client.get(f"{self.BASE}/ingresos-por-forma-pago")
        assert resp.status_code == 200
        data = resp.json()
        # Si todos los pedidos están cancelados, la lista debe estar vacía
        assert data == []
