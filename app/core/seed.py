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
from app.modules.ingrediente.model import Ingrediente
from app.modules.producto.model import Producto
from app.modules.producto_categoria.model import ProductoCategoria
from app.modules.producto_ingrediente.model import ProductoIngrediente
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
        "codigo": "COCINA",
        "descripcion": "Gestionar y avanzar estados de pedidos en preparación",
    },
    {
        "codigo": "CAJA",
        "descripcion": "Confirmar pedidos, actualizar stock e ingredientes",
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


# Catálogo de ingredientes. es_alergeno marca los de declaración obligatoria
# (gluten, lácteos, huevo).
INGREDIENTES_SEED: list[dict] = [
    {"nombre": "Carne",            "descripcion": "Carne vacuna picada",        "es_alergeno": False},
    {"nombre": "Pan",             "descripcion": "Pan de papa para hamburguesa", "es_alergeno": True},
    {"nombre": "Lechuga",          "descripcion": "Lechuga fresca",             "es_alergeno": False},
    {"nombre": "Tomate",           "descripcion": "Tomate fresco",              "es_alergeno": False},
    {"nombre": "Cheddar",          "descripcion": "Queso cheddar",              "es_alergeno": True},
    {"nombre": "Bacon",            "descripcion": "Panceta ahumada",            "es_alergeno": False},
    {"nombre": "Cebolla",          "descripcion": "Cebolla",                    "es_alergeno": False},
    {"nombre": "Huevo",            "descripcion": "Huevo",                      "es_alergeno": True},
    {"nombre": "Palta",            "descripcion": "Palta",                      "es_alergeno": False},
    {"nombre": "Rúcula",           "descripcion": "Rúcula fresca",              "es_alergeno": False},
    {"nombre": "Garbanzos",        "descripcion": "Garbanzos para medallón veggie", "es_alergeno": False},
    {"nombre": "Muzzarella",       "descripcion": "Queso muzzarella",           "es_alergeno": True},
    {"nombre": "Salsa de tomate",  "descripcion": "Salsa de tomate",            "es_alergeno": False},
    {"nombre": "Aceitunas",        "descripcion": "Aceitunas verdes",           "es_alergeno": False},
    {"nombre": "Albahaca",         "descripcion": "Albahaca fresca",            "es_alergeno": False},
    {"nombre": "Ajo",              "descripcion": "Ajo",                        "es_alergeno": False},
    {"nombre": "Pepperoni",        "descripcion": "Pepperoni",                  "es_alergeno": False},
    {"nombre": "Jamón",            "descripcion": "Jamón cocido",               "es_alergeno": False},
    {"nombre": "Pollo",            "descripcion": "Pechuga de pollo grillada",  "es_alergeno": False},
    {"nombre": "Croutons",         "descripcion": "Croutons de pan",            "es_alergeno": True},
    {"nombre": "Parmesano",        "descripcion": "Queso parmesano",            "es_alergeno": True},
    {"nombre": "Chocolate",        "descripcion": "Chocolate semiamargo",       "es_alergeno": True},
    {"nombre": "Dulce de leche",   "descripcion": "Dulce de leche",             "es_alergeno": True},
]


def seed_ingredientes(session: Session) -> None:
    """Crea los ingredientes que falten. Idempotente: matchea por nombre."""
    existentes_nombres = {i.nombre for i in session.exec(select(Ingrediente)).all()}

    nuevos = [
        Ingrediente(**data)
        for data in INGREDIENTES_SEED
        if data["nombre"] not in existentes_nombres
    ]
    if not nuevos:
        return

    for ingrediente in nuevos:
        session.add(ingrediente)
    session.commit()


# Composición de cada producto. Declara producto e ingrediente por nombre, la
# unidad por símbolo, la cantidad y si el cliente puede quitarlo del pedido.
PRODUCTO_INGREDIENTES_SEED: list[dict] = [
    # Hamburguesa Clásica
    {"producto": "Hamburguesa Clásica", "ingrediente": "Carne",   "cantidad": 150, "unidad": "g",  "es_removible": False},
    {"producto": "Hamburguesa Clásica", "ingrediente": "Pan",     "cantidad": 1,   "unidad": "ud", "es_removible": False},
    {"producto": "Hamburguesa Clásica", "ingrediente": "Lechuga", "cantidad": 20,  "unidad": "g",  "es_removible": True},
    {"producto": "Hamburguesa Clásica", "ingrediente": "Tomate",  "cantidad": 30,  "unidad": "g",  "es_removible": True},
    {"producto": "Hamburguesa Clásica", "ingrediente": "Cheddar", "cantidad": 1,   "unidad": "ud", "es_removible": True},
    # Hamburguesa Doble Bacon
    {"producto": "Hamburguesa Doble Bacon", "ingrediente": "Carne",   "cantidad": 300, "unidad": "g",  "es_removible": False},
    {"producto": "Hamburguesa Doble Bacon", "ingrediente": "Pan",     "cantidad": 1,   "unidad": "ud", "es_removible": False},
    {"producto": "Hamburguesa Doble Bacon", "ingrediente": "Cheddar", "cantidad": 2,   "unidad": "ud", "es_removible": False},
    {"producto": "Hamburguesa Doble Bacon", "ingrediente": "Bacon",   "cantidad": 40,  "unidad": "g",  "es_removible": True},
    # Hamburguesa Veggie
    {"producto": "Hamburguesa Veggie", "ingrediente": "Garbanzos", "cantidad": 150, "unidad": "g",  "es_removible": False},
    {"producto": "Hamburguesa Veggie", "ingrediente": "Pan",       "cantidad": 1,   "unidad": "ud", "es_removible": False},
    {"producto": "Hamburguesa Veggie", "ingrediente": "Palta",     "cantidad": 50,  "unidad": "g",  "es_removible": True},
    {"producto": "Hamburguesa Veggie", "ingrediente": "Rúcula",    "cantidad": 20,  "unidad": "g",  "es_removible": True},
    # Pizza Muzzarella
    {"producto": "Pizza Muzzarella", "ingrediente": "Salsa de tomate", "cantidad": 100, "unidad": "g", "es_removible": False},
    {"producto": "Pizza Muzzarella", "ingrediente": "Muzzarella",      "cantidad": 200, "unidad": "g", "es_removible": False},
    {"producto": "Pizza Muzzarella", "ingrediente": "Aceitunas",       "cantidad": 30,  "unidad": "g", "es_removible": True},
    # Pizza Napolitana
    {"producto": "Pizza Napolitana", "ingrediente": "Muzzarella", "cantidad": 200, "unidad": "g", "es_removible": False},
    {"producto": "Pizza Napolitana", "ingrediente": "Tomate",     "cantidad": 80,  "unidad": "g", "es_removible": False},
    {"producto": "Pizza Napolitana", "ingrediente": "Ajo",        "cantidad": 5,   "unidad": "g", "es_removible": True},
    {"producto": "Pizza Napolitana", "ingrediente": "Albahaca",   "cantidad": 5,   "unidad": "g", "es_removible": True},
    # Pizza Pepperoni
    {"producto": "Pizza Pepperoni", "ingrediente": "Muzzarella", "cantidad": 200, "unidad": "g", "es_removible": False},
    {"producto": "Pizza Pepperoni", "ingrediente": "Pepperoni",  "cantidad": 80,  "unidad": "g", "es_removible": False},
    # Empanada de Carne
    {"producto": "Empanada de Carne", "ingrediente": "Carne",   "cantidad": 60, "unidad": "g", "es_removible": False},
    {"producto": "Empanada de Carne", "ingrediente": "Cebolla", "cantidad": 20, "unidad": "g", "es_removible": False},
    {"producto": "Empanada de Carne", "ingrediente": "Huevo",   "cantidad": 10, "unidad": "g", "es_removible": True},
    # Empanada de Jamón y Queso
    {"producto": "Empanada de Jamón y Queso", "ingrediente": "Jamón",      "cantidad": 30, "unidad": "g", "es_removible": False},
    {"producto": "Empanada de Jamón y Queso", "ingrediente": "Muzzarella", "cantidad": 30, "unidad": "g", "es_removible": False},
    # Brownie con Helado
    {"producto": "Brownie con Helado", "ingrediente": "Chocolate", "cantidad": 80, "unidad": "g", "es_removible": False},
    # Flan Casero
    {"producto": "Flan Casero", "ingrediente": "Huevo",          "cantidad": 50, "unidad": "g", "es_removible": False},
    {"producto": "Flan Casero", "ingrediente": "Dulce de leche", "cantidad": 40, "unidad": "g", "es_removible": True},
    # Ensalada César
    {"producto": "Ensalada César", "ingrediente": "Lechuga",   "cantidad": 80,  "unidad": "g", "es_removible": False},
    {"producto": "Ensalada César", "ingrediente": "Pollo",     "cantidad": 100, "unidad": "g", "es_removible": False},
    {"producto": "Ensalada César", "ingrediente": "Croutons",  "cantidad": 20,  "unidad": "g", "es_removible": True},
    {"producto": "Ensalada César", "ingrediente": "Parmesano", "cantidad": 15,  "unidad": "g", "es_removible": True},
]


def seed_producto_ingredientes(session: Session) -> None:
    """
    Vincula productos con sus ingredientes. Idempotente: matchea por el par
    (producto_id, ingrediente_id).

    Depende de seed_productos, seed_ingredientes y seed_unidades_medida:
    resuelve los tres IDs por lookup. Saltea cualquier fila cuyo producto o
    ingrediente no exista (no rompe el arranque).
    """
    productos_por_nombre = {p.nombre: p for p in session.exec(select(Producto)).all()}
    ingredientes_por_nombre = {i.nombre: i for i in session.exec(select(Ingrediente)).all()}
    unidades_por_simbolo = {u.simbolo: u for u in session.exec(select(UnidadMedida)).all()}
    existentes_pares = {
        (pi.producto_id, pi.ingrediente_id)
        for pi in session.exec(select(ProductoIngrediente)).all()
    }

    creados = False
    for data in PRODUCTO_INGREDIENTES_SEED:
        producto = productos_por_nombre.get(data["producto"])
        ingrediente = ingredientes_por_nombre.get(data["ingrediente"])
        if producto is None or ingrediente is None:
            continue
        if (producto.id, ingrediente.id) in existentes_pares:
            continue

        unidad = unidades_por_simbolo.get(data["unidad"])

        session.add(
            ProductoIngrediente(
                producto_id=producto.id,
                ingrediente_id=ingrediente.id,
                cantidad=data["cantidad"],
                unidad_medida_id=unidad.id if unidad else None,
                es_removible=data["es_removible"],
            )
        )
        creados = True

    if creados:
        session.commit()
