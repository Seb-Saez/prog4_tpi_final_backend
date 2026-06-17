import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.producto.model import Producto
from app.modules.ingrediente.model import Ingrediente
from app.modules.producto_ingrediente.model import ProductoIngrediente


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

    def test_update_disponible_false_persiste_con_stock(self, client: TestClient, admin_headers):
        # Regresión: desmarcar "disponible" con stock > 0 debe persistir.
        # Antes el stock pisaba la decisión manual del admin y volvía a True.
        prod = self._seed_producto(client, "Para desactivar", 100.0)  # stock 5, disponible True
        resp = client.patch(f"{self.ENDPOINT}/{prod['id']}", json={"disponible": False})
        assert resp.status_code == 200, resp.text
        assert resp.json()["disponible"] is False
        # Y al volver a leerlo, sigue en False (no lo reactivó el stock).
        again = client.get(f"{self.ENDPOINT}/{prod['id']}")
        assert again.json()["disponible"] is False

    def test_update_stock_cero_reactiva_al_reponer(self, client: TestClient, admin_headers):
        # Si el stock llega a 0, se apaga por stock; al reponer, se reactiva solo.
        prod = self._seed_producto(client, "Cicla stock", 100.0)  # stock 5, disponible True
        sin_stock = client.patch(f"{self.ENDPOINT}/{prod['id']}", json={"stock_cantidad": 0})
        assert sin_stock.json()["disponible"] is False
        repuesto = client.patch(f"{self.ENDPOINT}/{prod['id']}", json={"stock_cantidad": 10})
        assert repuesto.json()["disponible"] is True

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


class TestProductoIngredientes:
    """Tests for GET /productos/{id}/ingredientes — enriched response."""

    ENDPOINT = "/api/v1/productos"

    def _seed_producto_con_ingrediente(
        self,
        session: Session,
        nombre_ingrediente: str = "Queso",
        stock_inicial: int = 8,
        es_removible: bool = False,
    ) -> tuple[Producto, Ingrediente]:
        producto = Producto(
            nombre=f"Prod-{nombre_ingrediente}",
            descripcion="Producto de prueba",
            precio_base=150,
            stock_cantidad=5,
            disponible=True,
        )
        session.add(producto)
        session.flush()

        ingrediente = Ingrediente(
            nombre=nombre_ingrediente,
            descripcion=nombre_ingrediente,
            es_alergeno=False,
            stock_cantidad=stock_inicial,
        )
        session.add(ingrediente)
        session.flush()

        session.add(ProductoIngrediente(
            producto_id=producto.id,
            ingrediente_id=ingrediente.id,
            cantidad=50,
            es_removible=es_removible,
        ))
        session.commit()
        session.refresh(producto)
        session.refresh(ingrediente)
        return producto, ingrediente

    def test_get_ingredientes_returns_nombre_and_stock(
        self, client: TestClient, admin_headers, session: Session
    ):
        """GET /productos/{id}/ingredientes includes nombre and stock_cantidad."""
        producto, ingrediente = self._seed_producto_con_ingrediente(
            session, nombre_ingrediente="Mozzarella", stock_inicial=12
        )
        resp = client.get(f"{self.ENDPOINT}/{producto.id}/ingredientes")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["ingrediente_id"] == ingrediente.id
        assert item["nombre"] == "Mozzarella"
        assert item["stock_cantidad"] == 12

    def test_get_ingredientes_not_found(self, client: TestClient, admin_headers):
        """Returns 404 when the product does not exist."""
        resp = client.get(f"{self.ENDPOINT}/99999/ingredientes")
        assert resp.status_code == 404

    def test_get_ingredientes_empty(self, client: TestClient, admin_headers):
        """Returns an empty list when the product has no ingredients."""
        resp = client.post(self.ENDPOINT, json={
            "nombre": "Sin ingredientes",
            "descripcion": "Sin ingredientes",
            "precio_base": 50.0,
            "stock_cantidad": 5,
            "disponible": True,
        })
        assert resp.status_code == 201, resp.text
        prod_id = resp.json()["id"]
        resp = client.get(f"{self.ENDPOINT}/{prod_id}/ingredientes")
        assert resp.status_code == 200
        assert resp.json() == []
