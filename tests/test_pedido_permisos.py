"""
Tests B6: permisos por transición (B4) y bloqueo por ingrediente faltante (B5).

Convenciones:
- _as(client, token): cambia el token activo en la cookie.
- _crear_usuario_con_rol: registra un usuario vía API y le asigna el rol dado.
- Se usan fixtures de conftest: client, session, admin_token, forma_pago_id.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import create_access_token
from app.modules.categoria.model import Categoria
from app.modules.ingrediente.model import Ingrediente
from app.modules.producto.model import Producto
from app.modules.producto_categoria.model import ProductoCategoria
from app.modules.producto_ingrediente.model import ProductoIngrediente
from app.modules.rol.model import Rol, UsuarioRol
from app.modules.usuarios.model import Usuario


def _as(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set("access_token", token)


def _crear_usuario_con_rol(
    client: TestClient,
    session: Session,
    admin_token: str,
    username: str,
    email: str,
    rol_codigo: str,
) -> str:
    """
    Registra un usuario y le asigna el rol indicado directamente en BD (vía session).
    Los usuarios reciben CLIENT automáticamente al registrarse; para roles adicionales
    (CAJA, COCINA) se inserta el vínculo usuario-rol directamente para evitar que
    una HTTPException 409 del endpoint deje la sesión en estado de rollback.
    Retorna el token de acceso del nuevo usuario con todos sus roles.
    """
    _as(client, admin_token)

    resp = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": "Secret1234!",
        "full_name": f"Usuario {rol_codigo}",
    })
    assert resp.status_code == 201, f"register failed: {resp.text}"
    uid = resp.json()["id"]

    # Asignar rol adicional directo en BD solo si no es CLIENT (ya fue asignado al registrar).
    # Usamos la session compartida para evitar que HTTPException 409 revierte la transacción.
    if rol_codigo != "CLIENT":
        rol = session.exec(select(Rol).where(Rol.codigo == rol_codigo)).first()
        assert rol is not None, f"Rol '{rol_codigo}' no encontrado en BD"
        existente = session.exec(
            select(UsuarioRol)
            .where(UsuarioRol.usuario_id == uid)
            .where(UsuarioRol.rol_id == rol.id)
        ).first()
        if existente is None:
            session.add(UsuarioRol(usuario_id=uid, rol_id=rol.id))
            session.commit()

    # Construir token con los roles actualizados desde BD.
    user = session.exec(select(Usuario).where(Usuario.id == uid)).first()
    assert user is not None, f"Usuario id={uid} no encontrado en BD"
    roles = session.exec(
        select(Rol.codigo)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .where(UsuarioRol.usuario_id == user.id)
    ).all()
    payload = {"sub": user.username, "roles": list(roles)}
    return create_access_token(payload, token_version=user.token_version)


def _crear_producto(client: TestClient, admin_token: str, nombre: str = "Producto Test") -> int:
    """Crea un producto simple y retorna su ID."""
    _as(client, admin_token)
    resp = client.post("/api/v1/productos", json={
        "nombre": nombre,
        "descripcion": "Producto de prueba",
        "precio_base": 100.00,
        "stock_cantidad": 10,
        "disponible": True,
    })
    assert resp.status_code == 201, f"crear producto failed: {resp.text}"
    return resp.json()["id"]


def _crear_pedido(
    client: TestClient,
    token: str,
    producto_id: int,
    forma_pago_id: int,
    modalidad: str = "RETIRO_LOCAL",
) -> int:
    """Crea un pedido y retorna su ID."""
    _as(client, token)
    resp = client.post("/api/v1/pedidos", json={
        "modalidad_entrega": modalidad,
        "forma_pago_id": forma_pago_id,
        "items": [{"producto_id": producto_id, "cantidad": 1}],
    })
    assert resp.status_code == 201, f"crear pedido failed: {resp.text}"
    return resp.json()["id"]


def _avanzar(client: TestClient, token: str, pedido_id: int) -> int:
    """Avanza el estado del pedido y retorna el status code HTTP."""
    _as(client, token)
    resp = client.patch(f"/api/v1/pedidos/{pedido_id}/avanzar")
    return resp.status_code


def _avanzar_n_veces(
    client: TestClient,
    admin_token: str,
    pedido_id: int,
    n: int,
) -> None:
    """Avanza el pedido N veces usando el token de admin (sin restricciones de rol)."""
    for _ in range(n):
        code = _avanzar(client, admin_token, pedido_id)
        assert code == 200, f"avanzar (admin) falló con {code}"


def _setup_producto_con_ingrediente_en_db(
    session: Session,
    ingrediente_nombre: str = "Carne",
    requiere_ingredientes: bool = True,
    es_removible: bool = False,
    stock_inicial: int = 10,
) -> tuple[Producto, Ingrediente]:
    """
    Crea directamente en BD un producto, categoría e ingrediente vinculados.
    Retorna (producto, ingrediente).
    Patrón reutilizado de TestAjustarStock en test_ingrediente.py.
    """
    categoria = Categoria(
        nombre=f"Cat-B5-{ingrediente_nombre}",
        descripcion="Categoría de prueba B5",
        requiere_ingredientes=requiere_ingredientes,
    )
    session.add(categoria)
    session.flush()

    producto = Producto(
        nombre=f"Prod-B5-{ingrediente_nombre}",
        descripcion="Producto de prueba B5",
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


# ============================================================
# B4 — Tests de permisos por transición
# ============================================================

class TestPermisosTransicion:
    """
    Verifica que cada transición exige los roles correctos según el mapa
    definido en app/modules/pedido/utils.py.
    """

    ENDPOINT = "/api/v1/pedidos"

    def test_caja_puede_confirmar(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """CAJA puede confirmar: PENDIENTE → CONFIRMADO."""
        caja_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "caja_confirmar", "caja_confirmar@mail.com", "CAJA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Caja-Confirmar")

        # El cliente crea el pedido
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_caja_conf", "cli_caja_conf@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # CAJA avanza PENDIENTE → CONFIRMADO
        assert _avanzar(client, caja_token, pedido_id) == 200

    def test_cocina_no_puede_confirmar(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """COCINA NO puede confirmar: PENDIENTE → CONFIRMADO devuelve 403."""
        cocina_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cocina_confirmar", "cocina_confirmar@mail.com", "COCINA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Cocina-Confirmar")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_cocina_conf", "cli_cocina_conf@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        assert _avanzar(client, cocina_token, pedido_id) == 403

    def test_caja_puede_pasar_a_preparacion(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """CAJA puede pasar de CONFIRMADO a EN_PREPARACION."""
        caja_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "caja_prep", "caja_prep@mail.com", "CAJA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Caja-Prep")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_caja_prep", "cli_caja_prep@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # PENDIENTE → CONFIRMADO (CAJA puede)
        assert _avanzar(client, caja_token, pedido_id) == 200
        # CONFIRMADO → EN_PREPARACION (CAJA puede)
        assert _avanzar(client, caja_token, pedido_id) == 200

    def test_cocina_puede_pasar_a_preparacion_desde_confirmado(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """COCINA puede pasar de CONFIRMADO a EN_PREPARACION."""
        cocina_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cocina_prep", "cocina_prep@mail.com", "COCINA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Cocina-Prep")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_coc_prep", "cli_coc_prep@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin confirma primero (COCINA no puede confirmar)
        _avanzar_n_veces(client, admin_token, pedido_id, 1)

        # CONFIRMADO → EN_PREPARACION (COCINA puede)
        assert _avanzar(client, cocina_token, pedido_id) == 200

    def test_cocina_puede_marcar_listo(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """COCINA puede marcar un pedido RETIRO_LOCAL como LISTO_PARA_RETIRAR."""
        cocina_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cocina_listo", "cocina_listo@mail.com", "COCINA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Cocina-Listo")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_coc_listo", "cli_coc_listo@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        # EN_PREPARACION → LISTO_PARA_RETIRAR (COCINA puede)
        assert _avanzar(client, cocina_token, pedido_id) == 200

    def test_caja_no_puede_marcar_listo(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """CAJA NO puede marcar listo: EN_PREPARACION → LISTO_PARA_RETIRAR devuelve 403."""
        caja_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "caja_listo", "caja_listo@mail.com", "CAJA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Caja-Listo")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_caja_listo", "cli_caja_listo@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        # EN_PREPARACION → LISTO_PARA_RETIRAR (CAJA NO puede)
        assert _avanzar(client, caja_token, pedido_id) == 403

    def test_cocina_no_puede_entregar(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """COCINA NO puede marcar como entregado (LISTO_PARA_RETIRAR → ENTREGADO es solo ADMIN)."""
        cocina_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cocina_entregar", "cocina_entregar@mail.com", "COCINA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Cocina-Entregar")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_coc_ent", "cli_coc_ent@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta LISTO_PARA_RETIRAR
        _avanzar_n_veces(client, admin_token, pedido_id, 3)

        # LISTO_PARA_RETIRAR → ENTREGADO (COCINA NO puede)
        assert _avanzar(client, cocina_token, pedido_id) == 403

    def test_admin_puede_todas_las_transiciones(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """ADMIN puede ejecutar todas las transiciones del flujo RETIRO_LOCAL."""
        producto_id = _crear_producto(client, admin_token, "Prod-Admin-Todo")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_admin_todo", "cli_admin_todo@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # PENDIENTE → CONFIRMADO → EN_PREPARACION → LISTO_PARA_RETIRAR → ENTREGADO
        estados_esperados = ["CONFIRMADO", "EN_PREPARACION", "LISTO_PARA_RETIRAR", "ENTREGADO"]
        for estado in estados_esperados:
            _as(client, admin_token)
            resp = client.patch(f"/api/v1/pedidos/{pedido_id}/avanzar")
            assert resp.status_code == 200, f"Admin no pudo avanzar a {estado}: {resp.text}"
            assert resp.json()["estado_pedido"]["codigo"] == estado

    def test_caja_no_puede_entregar(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """CAJA NO puede marcar como entregado."""
        caja_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "caja_entregar", "caja_entregar@mail.com", "CAJA",
        )
        producto_id = _crear_producto(client, admin_token, "Prod-Caja-Entregar")
        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_caja_ent", "cli_caja_ent@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta LISTO_PARA_RETIRAR
        _avanzar_n_veces(client, admin_token, pedido_id, 3)

        # LISTO_PARA_RETIRAR → ENTREGADO (CAJA NO puede)
        assert _avanzar(client, caja_token, pedido_id) == 403


# ============================================================
# B5 — Tests de bloqueo por ingrediente faltante
# ============================================================

class TestBloqueoIngredienteFaltante:
    """
    Verifica que la transición EN_PREPARACION → LISTO_PARA_RETIRAR|ENVIADO
    se rechaza con 409 cuando hay ingredientes no-removibles sin stock,
    y que se desbloquea al reponer.
    """

    ENDPOINT = "/api/v1/pedidos"
    INGREDIENTES_ENDPOINT = "/api/v1/ingredientes"

    def test_avance_bloqueado_por_ingrediente_faltante(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """
        Pedido en EN_PREPARACION con producto que tiene un ingrediente
        no-removible en stock=0 → avanzar devuelve 409.
        """
        producto, ingrediente = _setup_producto_con_ingrediente_en_db(
            session,
            ingrediente_nombre="Carne-B5-Bloqueo",
            requiere_ingredientes=True,
            es_removible=False,
            stock_inicial=10,
        )
        # Capturar IDs antes de cualquier commit que expire los objetos.
        producto_id = producto.id
        ingrediente_id = ingrediente.id

        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_b5_bloqueo", "cli_b5_bloqueo@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        # Marcar ingrediente como faltante
        _as(client, admin_token)
        resp = client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 0},
        )
        assert resp.status_code == 200

        # EN_PREPARACION → LISTO_PARA_RETIRAR debe ser rechazado con 409
        _as(client, admin_token)
        resp = client.patch(f"{self.ENDPOINT}/{pedido_id}/avanzar")
        assert resp.status_code == 409
        assert "Carne-B5-Bloqueo" in resp.json()["detail"]

    def test_avance_desbloqueado_al_reponer(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """
        Una vez repuesto el ingrediente faltante, el avance debe completarse
        con éxito (200).
        """
        producto, ingrediente = _setup_producto_con_ingrediente_en_db(
            session,
            ingrediente_nombre="Carne-B5-Reponer",
            requiere_ingredientes=True,
            es_removible=False,
            stock_inicial=10,
        )
        # Capturar IDs antes de cualquier commit que expire los objetos.
        producto_id = producto.id
        ingrediente_id = ingrediente.id

        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_b5_reponer", "cli_b5_reponer@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        # Marcar ingrediente como faltante
        _as(client, admin_token)
        client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 0},
        )

        # Confirmar bloqueo
        resp = client.patch(f"{self.ENDPOINT}/{pedido_id}/avanzar")
        assert resp.status_code == 409

        # Reponer el ingrediente
        _as(client, admin_token)
        client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 5},
        )

        # Ahora debe avanzar sin problemas
        _as(client, admin_token)
        resp = client.patch(f"{self.ENDPOINT}/{pedido_id}/avanzar")
        assert resp.status_code == 200
        assert resp.json()["estado_pedido"]["codigo"] == "LISTO_PARA_RETIRAR"

    def test_avance_no_bloqueado_por_ingrediente_removible(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """
        Un ingrediente removible en stock=0 NO bloquea el avance del pedido.
        """
        producto, ingrediente = _setup_producto_con_ingrediente_en_db(
            session,
            ingrediente_nombre="SalsaRemovible-B5",
            requiere_ingredientes=True,
            es_removible=True,  # removible → no bloquea
            stock_inicial=10,
        )
        producto_id = producto.id
        ingrediente_id = ingrediente.id

        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_b5_removible", "cli_b5_removible@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        # Marcar ingrediente removible como faltante
        _as(client, admin_token)
        client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 0},
        )

        # El avance no debe ser bloqueado
        resp = client.patch(f"{self.ENDPOINT}/{pedido_id}/avanzar")
        assert resp.status_code == 200

    def test_avance_no_bloqueado_categoria_sin_requiere_ingredientes(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """
        Productos de categorías con requiere_ingredientes=False (ej. bebidas)
        no son bloqueados aunque el ingrediente esté en stock=0.
        """
        producto, ingrediente = _setup_producto_con_ingrediente_en_db(
            session,
            ingrediente_nombre="GaseosaBase-B5",
            requiere_ingredientes=False,  # categoría sin requisito de ingredientes
            es_removible=False,
            stock_inicial=10,
        )
        producto_id = producto.id
        ingrediente_id = ingrediente.id

        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_b5_bebida", "cli_b5_bebida@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        # Marcar ingrediente como faltante
        _as(client, admin_token)
        client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 0},
        )

        # No debe bloquear porque requiere_ingredientes=False
        resp = client.patch(f"{self.ENDPOINT}/{pedido_id}/avanzar")
        assert resp.status_code == 200

    def test_mensaje_409_incluye_nombre_ingrediente(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """El mensaje de error 409 debe nombrar el ingrediente faltante."""
        producto, ingrediente = _setup_producto_con_ingrediente_en_db(
            session,
            ingrediente_nombre="QuesitoFaltante",
            requiere_ingredientes=True,
            es_removible=False,
            stock_inicial=5,
        )
        producto_id = producto.id
        ingrediente_id = ingrediente.id

        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_b5_msg", "cli_b5_msg@mail.com", "CLIENT",
        )
        pedido_id = _crear_pedido(client, client_token, producto_id, forma_pago_id)

        _avanzar_n_veces(client, admin_token, pedido_id, 2)

        _as(client, admin_token)
        client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 0},
        )

        resp = client.patch(f"{self.ENDPOINT}/{pedido_id}/avanzar")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "QuesitoFaltante" in detail

    def test_avance_bloqueado_delivery_enviado(
        self, client: TestClient, session: Session, admin_token: str, forma_pago_id: int
    ):
        """
        El bloqueo aplica también para la transición
        EN_PREPARACION → ENVIADO (pedidos delivery).
        """
        producto, ingrediente = _setup_producto_con_ingrediente_en_db(
            session,
            ingrediente_nombre="Carne-B5-Delivery",
            requiere_ingredientes=True,
            es_removible=False,
            stock_inicial=10,
        )
        producto_id = producto.id
        ingrediente_id = ingrediente.id

        client_token = _crear_usuario_con_rol(
            client, session, admin_token,
            "cli_b5_delivery", "cli_b5_delivery@mail.com", "CLIENT",
        )

        # Crear dirección para delivery
        _as(client, client_token)
        resp_dir = client.post("/api/v1/direcciones", json={
            "alias": "Casa",
            "linea1": "Av. Test 123",
            "ciudad": "Buenos Aires",
            "provincia": "Buenos Aires",
            "codigo_postal": "1000",
            "es_principal": True,
        })
        assert resp_dir.status_code == 201, resp_dir.text
        dir_id = resp_dir.json()["id"]

        # Crear pedido delivery con dirección
        _as(client, client_token)
        resp = client.post("/api/v1/pedidos", json={
            "modalidad_entrega": "DELIVERY",
            "forma_pago_id": forma_pago_id,
            "direccion_id": dir_id,
            "items": [{"producto_id": producto_id, "cantidad": 1}],
        })
        assert resp.status_code == 201, resp.text
        pedido_delivery_id = resp.json()["id"]

        # Admin lleva hasta EN_PREPARACION
        _avanzar_n_veces(client, admin_token, pedido_delivery_id, 2)

        # Marcar ingrediente faltante
        _as(client, admin_token)
        client.patch(
            f"{self.INGREDIENTES_ENDPOINT}/{ingrediente_id}/stock",
            json={"stock_cantidad": 0},
        )

        # EN_PREPARACION → ENVIADO (delivery) debe ser bloqueado
        resp = client.patch(f"{self.ENDPOINT}/{pedido_delivery_id}/avanzar")
        assert resp.status_code == 409
        assert "Carne-B5-Delivery" in resp.json()["detail"]
