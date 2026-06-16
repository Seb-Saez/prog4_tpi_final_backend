"""
Utilidades reutilizables para la lógica de stock de ingredientes y
disponibilidad de productos.

Estas funciones son compartidas por B3 (ajuste de stock) y B5 (bloqueo
de avance por ingrediente faltante). Reciben una sesión ya abierta y
NO hacen commit — el UoW del llamador es responsable de persistir.
"""

from sqlmodel import Session, select

from app.modules.ingrediente.model import Ingrediente
from app.modules.producto.model import Producto
from app.modules.producto_ingrediente.model import ProductoIngrediente


def obtener_productos_afectados_por_ingrediente(
    session: Session,
    ingrediente_id: int,
) -> list[Producto]:
    """
    Retorna los productos que usan el ingrediente dado como no removible
    y cuya categoría principal tiene requiere_ingredientes=True.

    Un producto puede tener varias categorías. Se considera afectado si
    AL MENOS UNA categoría vinculada tiene requiere_ingredientes=True.
    Se hace la evaluación con un join explícito para no cargar en memoria
    más datos de los necesarios.
    """
    from app.modules.categoria.model import Categoria
    from app.modules.producto_categoria.model import ProductoCategoria

    # Productos que usan ese ingrediente como no-removible
    stmt_productos = (
        select(Producto)
        .join(ProductoIngrediente, ProductoIngrediente.producto_id == Producto.id)
        .where(ProductoIngrediente.ingrediente_id == ingrediente_id)
        .where(ProductoIngrediente.es_removible == False)  # noqa: E712
    )
    productos = list(session.exec(stmt_productos).all())

    # Filtrar solo los que tienen al menos una categoría con requiere_ingredientes=True
    resultado: list[Producto] = []
    for producto in productos:
        stmt_cat = (
            select(Categoria)
            .join(ProductoCategoria, ProductoCategoria.categoria_id == Categoria.id)
            .where(ProductoCategoria.producto_id == producto.id)
            .where(Categoria.requiere_ingredientes == True)  # noqa: E712
        )
        if session.exec(stmt_cat).first() is not None:
            resultado.append(producto)

    return resultado


def producto_tiene_todos_ingredientes_en_stock(
    session: Session,
    producto_id: int,
) -> bool:
    """
    Retorna True si todos los ingredientes no removibles del producto
    tienen stock_cantidad > 0. Retorna True también si el producto no
    tiene ingredientes no-removibles (sin restricciones de stock).

    Usado por B3 al reponer stock y por B5 para verificar bloqueo de avance.
    """
    stmt = (
        select(Ingrediente)
        .join(ProductoIngrediente, ProductoIngrediente.ingrediente_id == Ingrediente.id)
        .where(ProductoIngrediente.producto_id == producto_id)
        .where(ProductoIngrediente.es_removible == False)  # noqa: E712
        .where(Ingrediente.stock_cantidad == 0)
    )
    faltante = session.exec(stmt).first()
    return faltante is None


def obtener_ingredientes_faltantes_del_producto(
    session: Session,
    producto_id: int,
) -> list[Ingrediente]:
    """
    Retorna los ingredientes no removibles del producto que tienen
    stock_cantidad == 0. Utilizado por B5 para reportar el bloqueo.
    """
    stmt = (
        select(Ingrediente)
        .join(ProductoIngrediente, ProductoIngrediente.ingrediente_id == Ingrediente.id)
        .where(ProductoIngrediente.producto_id == producto_id)
        .where(ProductoIngrediente.es_removible == False)  # noqa: E712
        .where(Ingrediente.stock_cantidad == 0)
    )
    return list(session.exec(stmt).all())
