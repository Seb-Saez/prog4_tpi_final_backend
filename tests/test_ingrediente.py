import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.categoria.model import Categoria
from app.modules.producto.model import Producto
from app.modules.ingrediente.model import Ingrediente
from app.modules.producto_ingrediente.model import ProductoIngrediente
from app.modules.producto_categoria.model import ProductoCategoria


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


class TestAjustarStock:
    """Tests para el endpoint PATCH /ingredientes/{id}/stock (B3)."""

    ENDPOINT = "/api/v1/ingredientes"

    def _setup_producto_con_ingrediente(
        self,
        session: Session,
        ingrediente_nombre: str = "Carne",
        requiere_ingredientes: bool = True,
        es_removible: bool = False,
        stock_inicial: int = 10,
    ) -> tuple[Producto, Ingrediente]:
        """
        Crea directamente en BD un producto, categoría e ingrediente vinculados.
        Retorna (producto, ingrediente).
        """
        categoria = Categoria(
            nombre=f"Cat-{ingrediente_nombre}",
            descripcion="Categoría de prueba",
            requiere_ingredientes=requiere_ingredientes,
        )
        session.add(categoria)
        session.flush()

        producto = Producto(
            nombre=f"Prod-{ingrediente_nombre}",
            descripcion="Producto de prueba",
            precio_base=100,
            stock_cantidad=5,
            disponible=True,
        )
        session.add(producto)
        session.flush()

        session.add(ProductoCategoria(
            producto_id=producto.id,
            categoria_id=categoria.id,
            es_principal=True,
        ))

        ingrediente = Ingrediente(
            nombre=ingrediente_nombre,
            descripcion=ingrediente_nombre,
            es_alergeno=False,
            stock_cantidad=stock_inicial,
        )
        session.add(ingrediente)
        session.flush()

        session.add(ProductoIngrediente(
            producto_id=producto.id,
            ingrediente_id=ingrediente.id,
            cantidad=100,
            es_removible=es_removible,
        ))
        session.commit()

        session.refresh(producto)
        session.refresh(ingrediente)
        return producto, ingrediente

    def test_ajustar_stock_admin(self, client: TestClient, admin_headers, session: Session):
        """Admin puede ajustar el stock de un ingrediente."""
        _, ing = self._setup_producto_con_ingrediente(session)
        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["stock_cantidad"] == 5

    def test_ajustar_stock_forbidden_client(self, client: TestClient, client_headers, session: Session):
        """Un cliente no puede ajustar stock."""
        _, ing = self._setup_producto_con_ingrediente(session)
        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 0},
        )
        assert resp.status_code == 403

    def test_faltante_deshabilita_producto(self, client: TestClient, admin_headers, session: Session):
        """Al marcar un ingrediente como faltante (stock=0), el producto se deshabilita."""
        producto, ing = self._setup_producto_con_ingrediente(
            session, stock_inicial=10, es_removible=False
        )
        assert producto.disponible is True

        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["stock_cantidad"] == 0

        session.refresh(producto)
        assert producto.disponible is False

    def test_faltante_no_afecta_ingrediente_removible(
        self, client: TestClient, admin_headers, session: Session
    ):
        """Un ingrediente removible NO deshabilita el producto al faltar."""
        producto, ing = self._setup_producto_con_ingrediente(
            session, ingrediente_nombre="SalsaRemovible",
            es_removible=True, stock_inicial=10,
        )
        assert producto.disponible is True

        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 0},
        )
        assert resp.status_code == 200

        session.refresh(producto)
        assert producto.disponible is True

    def test_faltante_no_afecta_categoria_sin_requiere(
        self, client: TestClient, admin_headers, session: Session
    ):
        """Un ingrediente faltante NO deshabilita productos de categorías con requiere_ingredientes=False."""
        producto, ing = self._setup_producto_con_ingrediente(
            session, ingrediente_nombre="GaseosaBase",
            requiere_ingredientes=False, es_removible=False, stock_inicial=10,
        )
        assert producto.disponible is True

        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 0},
        )
        assert resp.status_code == 200

        session.refresh(producto)
        assert producto.disponible is True

    def test_reposicion_reactiva_producto(self, client: TestClient, admin_headers, session: Session):
        """Al reponer un ingrediente (stock > 0), el producto vuelve a estar disponible."""
        producto, ing = self._setup_producto_con_ingrediente(
            session, stock_inicial=10, es_removible=False
        )

        # Marcar faltante
        client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 0},
        )
        session.refresh(producto)
        assert producto.disponible is False

        # Reponer
        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 20},
        )
        assert resp.status_code == 200
        assert resp.json()["stock_cantidad"] == 20

        session.refresh(producto)
        assert producto.disponible is True

    def test_reposicion_no_reactiva_con_otro_faltante(
        self, client: TestClient, admin_headers, session: Session
    ):
        """Reponer un ingrediente NO reactiva el producto si otro ingrediente no-removible sigue en 0."""
        categoria = Categoria(
            nombre="Cat-Doble",
            descripcion="Categoría doble ingrediente",
            requiere_ingredientes=True,
        )
        session.add(categoria)
        session.flush()

        producto = Producto(
            nombre="Prod-Doble",
            descripcion="Producto con dos ingredientes obligatorios",
            precio_base=100,
            stock_cantidad=5,
            disponible=True,
        )
        session.add(producto)
        session.flush()

        session.add(ProductoCategoria(
            producto_id=producto.id,
            categoria_id=categoria.id,
            es_principal=True,
        ))

        ing1 = Ingrediente(nombre="Ing1-Doble", descripcion="Ing1", es_alergeno=False, stock_cantidad=10)
        ing2 = Ingrediente(nombre="Ing2-Doble", descripcion="Ing2", es_alergeno=False, stock_cantidad=10)
        session.add(ing1)
        session.add(ing2)
        session.flush()

        session.add(ProductoIngrediente(producto_id=producto.id, ingrediente_id=ing1.id, cantidad=1, es_removible=False))
        session.add(ProductoIngrediente(producto_id=producto.id, ingrediente_id=ing2.id, cantidad=1, es_removible=False))
        session.commit()
        session.refresh(ing1)
        session.refresh(ing2)

        # Marcar ambos como faltantes
        client.patch(f"{self.ENDPOINT}/{ing1.id}/stock", json={"stock_cantidad": 0})
        client.patch(f"{self.ENDPOINT}/{ing2.id}/stock", json={"stock_cantidad": 0})

        session.refresh(producto)
        assert producto.disponible is False

        # Reponer solo ing1 — el producto sigue deshabilitado por ing2
        resp = client.patch(f"{self.ENDPOINT}/{ing1.id}/stock", json={"stock_cantidad": 5})
        assert resp.status_code == 200

        session.refresh(producto)
        assert producto.disponible is False

    def test_reposicion_no_reactiva_producto_deshabilitado_manualmente(
        self, client: TestClient, admin_headers, session: Session
    ):
        """Reponer un ingrediente NO reactiva un producto deshabilitado manualmente
        (deshabilitado_por_stock=False), aunque ahora tenga todos los ingredientes en stock."""
        producto, ing = self._setup_producto_con_ingrediente(
            session, ingrediente_nombre="Carne-Manual", stock_inicial=10, es_removible=False
        )

        # Admin deshabilita manualmente (sin tocar el stock)
        producto.disponible = False
        producto.deshabilitado_por_stock = False
        session.add(producto)
        session.commit()
        session.refresh(producto)
        assert producto.disponible is False
        assert producto.deshabilitado_por_stock is False

        # Ajustar el stock del ingrediente (sigue > 0, así que es "reposición")
        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 20},
        )
        assert resp.status_code == 200

        session.refresh(producto)
        # El producto debe seguir deshabilitado — se deshabilitó manualmente
        assert producto.disponible is False
        assert producto.deshabilitado_por_stock is False

    def test_reposicion_reactiva_producto_auto_deshabilitado_y_limpia_flag(
        self, client: TestClient, admin_headers, session: Session
    ):
        """Reponer un ingrediente reactiva el producto auto-deshabilitado por stock
        y limpia el flag deshabilitado_por_stock."""
        producto, ing = self._setup_producto_con_ingrediente(
            session, ingrediente_nombre="Carne-Auto", stock_inicial=10, es_removible=False
        )

        # Marcar faltante → auto-deshabilita el producto y setea el flag
        client.patch(f"{self.ENDPOINT}/{ing.id}/stock", json={"stock_cantidad": 0})
        session.refresh(producto)
        assert producto.disponible is False
        assert producto.deshabilitado_por_stock is True

        # Reponer → debe reactivar y limpiar el flag
        resp = client.patch(f"{self.ENDPOINT}/{ing.id}/stock", json={"stock_cantidad": 15})
        assert resp.status_code == 200

        session.refresh(producto)
        assert producto.disponible is True
        assert producto.deshabilitado_por_stock is False

    def test_ajustar_stock_cocina(self, client: TestClient, session: Session):
        """COCINA puede ajustar el stock de un ingrediente."""
        from sqlmodel import select
        from app.modules.usuarios.model import Usuario
        from app.modules.rol.model import Rol, UsuarioRol
        from app.modules.rol.enums import RolEnum
        from app.core.security import create_access_token

        # Register a new user and assign COCINA role
        resp = client.post("/api/v1/auth/register", json={
            "username": "cocina_user",
            "email": "cocina@mail.com",
            "password": "Cocina1234!",
            "full_name": "Cocina User",
        })
        assert resp.status_code == 201, resp.text
        uid = resp.json()["id"]

        # Assign COCINA role via admin
        admin_user = session.exec(select(Usuario).where(Usuario.username == "admin")).first()
        admin_roles = session.exec(
            select(Rol.codigo)
            .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
            .where(UsuarioRol.usuario_id == admin_user.id)
        ).all()
        admin_token = create_access_token(
            {"sub": admin_user.username, "roles": list(admin_roles)},
            token_version=admin_user.token_version,
        )
        client.cookies.clear()
        client.cookies.set("access_token", admin_token)
        resp = client.post(f"/api/v1/admin/usuarios/{uid}/roles", json={"rol_codigo": "COCINA"})
        assert resp.status_code == 200, resp.text

        # Build COCINA token
        cocina_user = session.exec(select(Usuario).where(Usuario.username == "cocina_user")).first()
        cocina_roles = session.exec(
            select(Rol.codigo)
            .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
            .where(UsuarioRol.usuario_id == cocina_user.id)
        ).all()
        cocina_token = create_access_token(
            {"sub": cocina_user.username, "roles": list(cocina_roles)},
            token_version=cocina_user.token_version,
        )
        client.cookies.clear()
        client.cookies.set("access_token", cocina_token)

        _, ing = self._setup_producto_con_ingrediente(session, ingrediente_nombre="Carne-Cocina")
        resp = client.patch(
            f"{self.ENDPOINT}/{ing.id}/stock",
            json={"stock_cantidad": 3},
        )
        assert resp.status_code == 200
        assert resp.json()["stock_cantidad"] == 3
