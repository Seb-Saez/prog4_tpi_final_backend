"""
Seeds idempotentes que corren al arrancar la app.

Idempotencia = correr la función N veces produce el mismo resultado que correrla 1 vez.
Si el admin ya existe → no hace nada. Si no existe → lo crea.
"""

from decimal import Decimal

from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.categoria.model import Categoria
from app.modules.estado_pedido.model import EstadoPedido
from app.modules.forma_pago.model import FormaPago
from app.modules.producto.model import Producto
from app.modules.producto_categoria.model import ProductoCategoria
from app.modules.rol.enums import RolEnum
from app.modules.rol.model import Rol, UsuarioRol
from app.modules.rol.unit_of_work import RolUnitOfWork
from app.modules.unidad_medida.model import UnidadMedida
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


# Catálogo de roles del sistema.
ROLES_SEED: list[dict] = [
    {
        "codigo": "ADMIN",
        "descripcion": "Acceso total sin restricciones",
    },
    {
        "codigo": "PEDIDOS",
        "descripcion": "Avanzar estados de pedidos",
    },
    {
        "codigo": "STOCK",
        "descripcion": "Actualizar stock, gestionar productos, confirmar pedidos",
    },
    {
        "codigo": "CLIENT",
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


# Unidades de medida habilitadas por defecto.
UNIDADES_MEDIDA_SEED: list[dict] = [
    {"nombre": "Kilogramo",  "simbolo": "kg",        "tipo": "peso"},
    {"nombre": "Gramo",      "simbolo": "g",         "tipo": "peso"},
    {"nombre": "Litro",      "simbolo": "L",         "tipo": "volumen"},
    {"nombre": "Mililitro",  "simbolo": "ml",        "tipo": "volumen"},
    {"nombre": "Unidad",     "simbolo": "ud",        "tipo": "unidad"},
    {"nombre": "Porción",    "simbolo": "porciones", "tipo": "unidad"},
]


def seed_unidades_medida(session: Session) -> None:
    """Crea las unidades de medida que falten. Idempotente: matchea por símbolo."""
    existentes_simbolos = {
        u.simbolo for u in session.exec(select(UnidadMedida)).all()
    }

    nuevas = [
        UnidadMedida(**data)
        for data in UNIDADES_MEDIDA_SEED
        if data["simbolo"] not in existentes_simbolos
    ]
    if not nuevas:
        return

    for unidad in nuevas:
        session.add(unidad)
    session.commit()


# Catálogo de categorías del menú. Imágenes vía Unsplash (URLs estables).
CATEGORIAS_SEED: list[dict] = [
    {
        "nombre": "Hamburguesas",
        "descripcion": "Hamburguesas artesanales a la parrilla",
        "imagen_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&q=80",
    },
    {
        "nombre": "Pizzas",
        "descripcion": "Pizzas a la piedra con masa madre",
        "imagen_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&q=80",
    },
    {
        "nombre": "Empanadas",
        "descripcion": "Empanadas caseras horneadas",
        "imagen_url": "https://images.unsplash.com/photo-1601924582970-9238bcb495d9?w=800&q=80",
    },
    {
        "nombre": "Bebidas",
        "descripcion": "Gaseosas, aguas y jugos naturales",
        "imagen_url": "https://images.unsplash.com/photo-1437418747212-8d9709afab22?w=800&q=80",
    },
    {
        "nombre": "Postres",
        "descripcion": "Postres y dulces para cerrar la comida",
        "imagen_url": "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=800&q=80",
    },
    {
        "nombre": "Ensaladas",
        "descripcion": "Ensaladas frescas y opciones saludables",
        "imagen_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&q=80",
    },
]


def seed_categorias(session: Session) -> None:
    """Crea las categorías que falten. Idempotente: matchea por nombre."""
    existentes_nombres = {c.nombre for c in session.exec(select(Categoria)).all()}

    nuevas = [
        Categoria(**data)
        for data in CATEGORIAS_SEED
        if data["nombre"] not in existentes_nombres
    ]
    if not nuevas:
        return

    for categoria in nuevas:
        session.add(categoria)
    session.commit()


# Catálogo de productos. Cada uno declara su categoría (por nombre) y la unidad
# de venta (por símbolo). El seed resuelve esos IDs por lookup al insertar.
PRODUCTOS_SEED: list[dict] = [
    # ─── Hamburguesas ───────────────────────────────────────────────────────
    {
        "nombre": "Hamburguesa Clásica",
        "descripcion": "Carne, lechuge, tomate, cheddar y pan de papa",
        "precio_base": "5500.00",
        "stock_cantidad": 50,
        "categoria": "Hamburguesas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&q=80",
            "https://images.unsplash.com/photo-1550547660-d9450f859349?w=800&q=80",
        ],
    },
    {
        "nombre": "Hamburguesa Doble Bacon",
        "descripcion": "Doble carne, doble cheddar, bacon crocante y barbacoa",
        "precio_base": "7800.00",
        "stock_cantidad": 40,
        "categoria": "Hamburguesas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1553979459-d2229ba7433b?w=800&q=80",
        ],
    },
    {
        "nombre": "Hamburguesa Veggie",
        "descripcion": "Medallón de garbanzos, palta, rúcula y alioli",
        "precio_base": "6200.00",
        "stock_cantidad": 30,
        "categoria": "Hamburguesas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1520072959219-c595dc870360?w=800&q=80",
        ],
    },
    # ─── Pizzas ─────────────────────────────────────────────────────────────
    {
        "nombre": "Pizza Muzzarella",
        "descripcion": "Salsa de tomate, muzzarella y aceitunas",
        "precio_base": "6900.00",
        "stock_cantidad": 35,
        "categoria": "Pizzas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&q=80",
        ],
    },
    {
        "nombre": "Pizza Napolitana",
        "descripcion": "Muzzarella, tomate en rodajas, ajo y albahaca",
        "precio_base": "7600.00",
        "stock_cantidad": 30,
        "categoria": "Pizzas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80",
        ],
    },
    {
        "nombre": "Pizza Pepperoni",
        "descripcion": "Muzzarella y abundante pepperoni",
        "precio_base": "8200.00",
        "stock_cantidad": 28,
        "categoria": "Pizzas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=800&q=80",
        ],
    },
    # ─── Empanadas ──────────────────────────────────────────────────────────
    {
        "nombre": "Empanada de Carne",
        "descripcion": "Carne cortada a cuchillo, cebolla y huevo",
        "precio_base": "1200.00",
        "stock_cantidad": 120,
        "categoria": "Empanadas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1601924582970-9238bcb495d9?w=800&q=80",
        ],
    },
    {
        "nombre": "Empanada de Jamón y Queso",
        "descripcion": "Jamón cocido y muzzarella",
        "precio_base": "1200.00",
        "stock_cantidad": 120,
        "categoria": "Empanadas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1626200419199-391ae4be7a41?w=800&q=80",
        ],
    },
    # ─── Bebidas ────────────────────────────────────────────────────────────
    {
        "nombre": "Coca-Cola 500ml",
        "descripcion": "Gaseosa línea Coca-Cola, botella 500ml",
        "precio_base": "1800.00",
        "stock_cantidad": 200,
        "categoria": "Bebidas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1554866585-cd94860890b7?w=800&q=80",
        ],
    },
    {
        "nombre": "Agua Mineral 500ml",
        "descripcion": "Agua sin gas, botella 500ml",
        "precio_base": "1200.00",
        "stock_cantidad": 200,
        "categoria": "Bebidas",
        "unidad": "ud",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1560023907-5f339617ea30?w=800&q=80",
        ],
    },
    # ─── Postres ────────────────────────────────────────────────────────────
    {
        "nombre": "Brownie con Helado",
        "descripcion": "Brownie tibio de chocolate con helado de crema",
        "precio_base": "3500.00",
        "stock_cantidad": 25,
        "categoria": "Postres",
        "unidad": "porciones",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=800&q=80",
        ],
    },
    {
        "nombre": "Flan Casero",
        "descripcion": "Flan con dulce de leche y crema",
        "precio_base": "2800.00",
        "stock_cantidad": 30,
        "categoria": "Postres",
        "unidad": "porciones",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=800&q=80",
        ],
    },
    # ─── Ensaladas ──────────────────────────────────────────────────────────
    {
        "nombre": "Ensalada César",
        "descripcion": "Lechuga, pollo grillado, croutons, parmesano y aderezo césar",
        "precio_base": "5200.00",
        "stock_cantidad": 25,
        "categoria": "Ensaladas",
        "unidad": "porciones",
        "imagenes_url": [
            "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&q=80",
        ],
    },
]


def seed_productos(session: Session) -> None:
    """
    Crea los productos que falten. Idempotente: matchea por nombre.

    Depende de seed_categorias y seed_unidades_medida: resuelve categoria_id
    y unidad_venta_id por lookup. Si la categoría o la unidad declarada no
    existe, saltea ese producto (no rompe el arranque).
    """
    existentes_nombres = {p.nombre for p in session.exec(select(Producto)).all()}
    categorias_por_nombre = {c.nombre: c for c in session.exec(select(Categoria)).all()}
    unidades_por_simbolo = {u.simbolo: u for u in session.exec(select(UnidadMedida)).all()}

    creados = False
    for data in PRODUCTOS_SEED:
        if data["nombre"] in existentes_nombres:
            continue

        categoria = categorias_por_nombre.get(data["categoria"])
        if categoria is None:
            continue

        unidad = unidades_por_simbolo.get(data["unidad"])

        producto = Producto(
            nombre=data["nombre"],
            descripcion=data["descripcion"],
            precio_base=Decimal(data["precio_base"]),
            imagenes_url=data["imagenes_url"],
            stock_cantidad=data["stock_cantidad"],
            disponible=True,
            unidad_venta_id=unidad.id if unidad else None,
        )
        session.add(producto)
        session.flush()  # obtener producto.id para el vínculo

        session.add(
            ProductoCategoria(
                producto_id=producto.id,
                categoria_id=categoria.id,
                es_principal=True,
            )
        )
        creados = True

    if creados:
        session.commit()
