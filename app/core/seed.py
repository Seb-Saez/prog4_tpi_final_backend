"""
Seeds idempotentes que corren al arrancar la app.

Idempotencia = correr la función N veces produce el mismo resultado que correrla 1 vez.
Si el admin ya existe → no hace nada. Si no existe → lo crea.
"""

from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.estado_pedido.model import EstadoPedido
from app.modules.forma_pago.model import FormaPago
from app.modules.rol.enums import RolEnum
from app.modules.rol.model import Rol, UsuarioRol
from app.modules.rol.unit_of_work import RolUnitOfWork
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


# Catálogo de roles del sistema.
ROLES_SEED: list[dict] = [
    {
        "codigo": "ADMIN",
        "descripcion": "Acceso total sin restricciones",
    },
    {
        "codigo": "COCINA",
        "descripcion": "Avanzar estados de pedidos",
    },
    {
        "codigo": "CAJA",
        "descripcion": "Actualizar stock, gestionar productos, confirmar pedidos",
    },
    {
        "codigo": "CLIENTE",
        "descripcion": "Operar solo con sus propios datos",
    },
]


def seed_roles(session: Session) -> None:
    """Crea los roles que falten. Idempotente: matchea por código."""
    existentes_codigos = {r.codigo for r in session.exec(select(Rol)).all()}

    nuevos = [
        Rol(**data)
        for data in ROLES_SEED
        if data["codigo"] not in existentes_codigos
    ]
    if not nuevos:
        return

    for rol in nuevos:
        session.add(rol)
    session.commit()


def seed_admin_user(session: Session) -> None:
    """Crea el usuario admin inicial si no hay ningún usuario con rol ADMIN."""
    with UsuarioUnitOfWork(session) as user_uow, RolUnitOfWork(session) as rol_uow:
        existentes = user_uow.usuarios.get_by_rol(RolEnum.ADMIN)
        if existentes:
            return

        admin = Usuario(
            username=settings.ADMIN_INITIAL_USERNAME,
            full_name=settings.ADMIN_INITIAL_FULLNAME,
            email=settings.ADMIN_INITIAL_EMAIL,
            hashed_password=hash_password(settings.ADMIN_INITIAL_PASSWORD),
            disabled=False,
        )
        user_uow.usuarios.add(admin)

        rol_admin = rol_uow.roles.get_by_codigo("ADMIN")
        if rol_admin:
            rol_uow.usuarios_roles.add(UsuarioRol(usuario_id=admin.id, rol_id=rol_admin.id))


# Catálogo de estados del flujo de pedidos.
# Reglas: debe existir uno con orden=1 (entrada) y uno con codigo="CANCELADO".
ESTADOS_PEDIDO_SEED: list[dict] = [
    {
        "codigo": "PENDIENTE",
        "nombre": "Pendiente",
        "orden": 1,
        "descripcion": "Pedido recibido, esperando confirmación",
        "es_terminal": False,
        "permite_cancelar": True,
    },
    {
        "codigo": "CONFIRMADO",
        "nombre": "Confirmado",
        "orden": 2,
        "descripcion": "Pedido confirmado por la cocina",
        "es_terminal": False,
        "permite_cancelar": True,
    },
    {
        "codigo": "EN_PREPARACION",
        "nombre": "En preparación",
        "orden": 3,
        "descripcion": "Cocina trabajando en el pedido",
        "es_terminal": False,
        "permite_cancelar": False,
    },
    {
        "codigo": "LISTO_PARA_RETIRAR",
        "nombre": "Listo para retirar",
        "orden": 4,
        "descripcion": "El pedido está listo, esperando que el cliente lo retire",
        "es_terminal": False,
        "permite_cancelar": False,
    },
    {
        "codigo": "ENVIADO",
        "nombre": "Enviado",
        "orden": 5,
        "descripcion": "Pedido despachado al cliente",
        "es_terminal": False,
        "permite_cancelar": False,
    },
    {
        "codigo": "ENTREGADO",
        "nombre": "Entregado",
        "orden": 6,
        "descripcion": "Pedido entregado al cliente",
        "es_terminal": True,
        "permite_cancelar": False,
    },
    {
        "codigo": "CANCELADO",
        "nombre": "Cancelado",
        "orden": 99,
        "descripcion": "Pedido cancelado",
        "es_terminal": True,
        "permite_cancelar": False,
    },
]


def seed_estados_pedido(session: Session) -> None:
    """Crea los estados de pedido que falten. Idempotente: matchea por código."""
    existentes_codigos = {
        e.codigo for e in session.exec(select(EstadoPedido)).all()
    }

    nuevos = [
        EstadoPedido(**data)
        for data in ESTADOS_PEDIDO_SEED
        if data["codigo"] not in existentes_codigos
    ]
    if not nuevos:
        return

    for estado in nuevos:
        session.add(estado)
    session.commit()


# Formas de pago habilitadas por defecto.
FORMAS_PAGO_SEED: list[dict] = [
    {"codigo": "EFECTIVO", "descripcion": "Efectivo", "habilitado": True},
    {"codigo": "TRANSFERENCIA", "descripcion": "Transferencia bancaria", "habilitado": True},
    {"codigo": "MERCADOPAGO", "descripcion": "MercadoPago", "habilitado": True},
]


def seed_formas_pago(session: Session) -> None:
    """Crea las formas de pago que falten. Idempotente: matchea por código."""
    existentes_codigos = {
        f.codigo for f in session.exec(select(FormaPago)).all()
    }

    nuevas = [
        FormaPago(**data)
        for data in FORMAS_PAGO_SEED
        if data["codigo"] not in existentes_codigos
    ]
    if not nuevas:
        return

    for forma in nuevas:
        session.add(forma)
    session.commit()
