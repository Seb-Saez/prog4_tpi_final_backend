"""Lógica de negocio para estadísticas y reportes agregados.

Todas las consultas son de solo lectura; no se modifica ningún modelo.
Las operaciones de agregación se realizan directamente en la base de datos
mediante sqlalchemy.func para eficiencia.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, case
from sqlmodel import Session, select

from app.modules.categoria.model import Categoria
from app.modules.detalle_pedido.model import DetallePedido
from app.modules.estado_pedido.model import EstadoPedido
from app.modules.forma_pago.model import FormaPago
from app.modules.pedido.model import Pedido
from app.modules.producto.model import Producto
from app.modules.producto_categoria.model import ProductoCategoria
from .schema import (
    IngresosPorFormaPago,
    PedidosPorEstado,
    PeriodoVentas,
    ProductoMasVendido,
    ResumenKPI,
    VentasPorCategoria,
)

# Código de estado a excluir de las métricas de ventas
_ESTADO_CANCELADO = "CANCELADO"
_ESTADO_PENDIENTE = "PENDIENTE"


def obtener_resumen(session: Session) -> ResumenKPI:
    """Devuelve los KPIs principales del negocio.

    Los pedidos en estado CANCELADO se excluyen de los totales de ventas
    y del ticket promedio. La DB vacía retorna ceros en lugar de None.
    ventas_hoy y ventas_mes usan filtros de rango datetime (UTC) para ser
    compatibles tanto con SQLite (tests) como con PostgreSQL (producción).
    """
    # Conteo y suma de pedidos no cancelados
    stmt_ventas = select(
        func.count(Pedido.id).label("total_pedidos"),
        func.coalesce(func.sum(Pedido.total), Decimal("0")).label("ventas_totales"),
        func.coalesce(func.avg(Pedido.total), Decimal("0")).label("ticket_promedio"),
    ).where(Pedido.estado_pedido_codigo != _ESTADO_CANCELADO)

    row_ventas = session.exec(stmt_ventas).one()

    # Conteo de pedidos pendientes
    stmt_pendientes = select(func.count(Pedido.id)).where(
        Pedido.estado_pedido_codigo == _ESTADO_PENDIENTE
    )
    pedidos_pendientes = session.exec(stmt_pendientes).one() or 0

    # Productos disponibles
    stmt_activos = select(func.count(Producto.id)).where(Producto.disponible == True)  # noqa: E712
    productos_activos = session.exec(stmt_activos).one() or 0

    # ventas_hoy: pedidos del día actual en UTC (rango datetime, compatible con SQLite y Postgres)
    now_utc = datetime.now(timezone.utc)
    inicio_hoy = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    inicio_manana = _siguiente_dia(now_utc)

    stmt_hoy = select(
        func.coalesce(func.sum(Pedido.total), Decimal("0")).label("total")
    ).where(
        Pedido.estado_pedido_codigo != _ESTADO_CANCELADO,
        Pedido.created_at >= inicio_hoy,
        Pedido.created_at < inicio_manana,
    )
    ventas_hoy = Decimal(str(session.exec(stmt_hoy).one() or 0))

    # ventas_mes: pedidos del mes actual en UTC
    inicio_mes = datetime(now_utc.year, now_utc.month, 1, tzinfo=timezone.utc)
    if now_utc.month == 12:
        inicio_mes_sig = datetime(now_utc.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        inicio_mes_sig = datetime(now_utc.year, now_utc.month + 1, 1, tzinfo=timezone.utc)

    stmt_mes = select(
        func.coalesce(func.sum(Pedido.total), Decimal("0")).label("total")
    ).where(
        Pedido.estado_pedido_codigo != _ESTADO_CANCELADO,
        Pedido.created_at >= inicio_mes,
        Pedido.created_at < inicio_mes_sig,
    )
    ventas_mes = Decimal(str(session.exec(stmt_mes).one() or 0))

    return ResumenKPI(
        total_pedidos=row_ventas.total_pedidos or 0,
        ventas_totales=Decimal(str(row_ventas.ventas_totales or 0)),
        ticket_promedio=Decimal(str(row_ventas.ticket_promedio or 0)),
        pedidos_pendientes=pedidos_pendientes,
        productos_activos=productos_activos,
        ventas_hoy=ventas_hoy,
        ventas_mes=ventas_mes,
    )


def _siguiente_dia(dt: datetime) -> datetime:
    """Retorna el inicio (00:00:00 UTC) del día siguiente a dt."""
    siguiente = date(dt.year, dt.month, dt.day) + timedelta(days=1)
    return datetime(siguiente.year, siguiente.month, siguiente.day, tzinfo=timezone.utc)


def obtener_ingresos_por_forma_pago(session: Session) -> list[IngresosPorFormaPago]:
    """Devuelve ingresos y cantidad de pedidos agrupados por forma de pago.

    Excluye pedidos en estado CANCELADO (EST-01).
    Agrupa por FormaPago.codigo/descripcion via JOIN Pedido→FormaPago.
    """
    stmt = (
        select(
            FormaPago.descripcion.label("forma_pago"),
            func.coalesce(func.sum(Pedido.total), Decimal("0")).label("total"),
            func.count(Pedido.id).label("cantidad"),
        )
        .join(FormaPago, Pedido.forma_pago_id == FormaPago.id)
        .where(Pedido.estado_pedido_codigo != _ESTADO_CANCELADO)
        .group_by(FormaPago.id, FormaPago.codigo, FormaPago.descripcion)
        .order_by(func.sum(Pedido.total).desc())
    )

    rows = session.exec(stmt).all()
    return [
        IngresosPorFormaPago(
            forma_pago=row.forma_pago,
            total=Decimal(str(row.total or 0)),
            cantidad=row.cantidad or 0,
        )
        for row in rows
    ]


def obtener_ventas_por_periodo(
    session: Session,
    desde: date,
    hasta: date,
    agrupacion: str,
) -> list[PeriodoVentas]:
    """Devuelve una serie temporal de ventas entre las fechas indicadas.

    Args:
        agrupacion: "dia" -> formato YYYY-MM-DD | "mes" -> formato YYYY-MM
    """
    desde_dt = datetime(desde.year, desde.month, desde.day, tzinfo=timezone.utc)
    hasta_dt = datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59, tzinfo=timezone.utc)

    if agrupacion == "mes":
        # Truncar al primer día del mes para agrupar
        periodo_col = func.to_char(Pedido.created_at, "YYYY-MM").label("periodo")
    else:
        periodo_col = func.to_char(Pedido.created_at, "YYYY-MM-DD").label("periodo")

    stmt = (
        select(
            periodo_col,
            func.coalesce(func.sum(Pedido.total), Decimal("0")).label("total"),
            func.count(Pedido.id).label("cantidad_pedidos"),
        )
        .where(
            Pedido.estado_pedido_codigo != _ESTADO_CANCELADO,
            Pedido.created_at >= desde_dt,
            Pedido.created_at <= hasta_dt,
        )
        .group_by("periodo")
        .order_by("periodo")
    )

    rows = session.exec(stmt).all()
    return [
        PeriodoVentas(
            periodo=row.periodo,
            total=Decimal(str(row.total or 0)),
            cantidad_pedidos=row.cantidad_pedidos or 0,
        )
        for row in rows
    ]


def obtener_productos_mas_vendidos(
    session: Session,
    limit: int = 10,
) -> list[ProductoMasVendido]:
    """Devuelve los N productos con mayor cantidad de unidades vendidas.

    Usa el campo nombre_snap del detalle para mantener el nombre histórico
    incluso si el producto fue modificado o eliminado.
    Excluye detalles de pedidos en estado CANCELADO.
    """
    stmt = (
        select(
            DetallePedido.producto_id,
            DetallePedido.nombre_snap.label("nombre"),
            func.sum(DetallePedido.cantidad).label("cantidad_vendida"),
            func.coalesce(
                func.sum(DetallePedido.subtotal_snap), Decimal("0")
            ).label("ingresos"),
        )
        .join(Pedido, DetallePedido.pedido_id == Pedido.id)
        .where(Pedido.estado_pedido_codigo != _ESTADO_CANCELADO)
        .group_by(DetallePedido.producto_id, DetallePedido.nombre_snap)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(limit)
    )

    rows = session.exec(stmt).all()
    return [
        ProductoMasVendido(
            producto_id=row.producto_id,
            nombre=row.nombre,
            cantidad_vendida=row.cantidad_vendida or 0,
            ingresos=Decimal(str(row.ingresos or 0)),
        )
        for row in rows
    ]


def obtener_ventas_por_categoria(session: Session) -> list[VentasPorCategoria]:
    """Devuelve ingresos y unidades vendidas agrupados por categoría.

    Decisión de diseño: cuando un producto pertenece a múltiples categorías,
    sus ventas se contabilizan bajo CADA una de ellas. Esto puede producir
    un total agregado mayor al total real de ventas, pero refleja con fidelidad
    la contribución de cada categoría al mix de productos.
    Si se prefiere evitar doble conteo, filtrar con es_principal=True en la
    condición de join de ProductoCategoria (comentado abajo como alternativa).
    """
    stmt = (
        select(
            Categoria.id.label("categoria_id"),
            Categoria.nombre.label("categoria"),
            func.coalesce(func.sum(DetallePedido.subtotal_snap), Decimal("0")).label("total"),
            func.coalesce(func.sum(DetallePedido.cantidad), 0).label("cantidad"),
        )
        .join(ProductoCategoria, Categoria.id == ProductoCategoria.categoria_id)
        .join(DetallePedido, ProductoCategoria.producto_id == DetallePedido.producto_id)
        # Alternativa sin doble conteo: añadir .where(ProductoCategoria.es_principal == True)
        .join(Pedido, DetallePedido.pedido_id == Pedido.id)
        .where(Pedido.estado_pedido_codigo != _ESTADO_CANCELADO)
        .group_by(Categoria.id, Categoria.nombre)
        .order_by(func.sum(DetallePedido.subtotal_snap).desc())
    )

    rows = session.exec(stmt).all()
    return [
        VentasPorCategoria(
            categoria_id=row.categoria_id,
            categoria=row.categoria,
            total=Decimal(str(row.total or 0)),
            cantidad=row.cantidad or 0,
        )
        for row in rows
    ]


def obtener_pedidos_por_estado(session: Session) -> list[PedidosPorEstado]:
    """Devuelve la distribución de pedidos por estado.

    Solo incluye los estados que tienen al menos un pedido asociado.
    Los estados sin pedidos no aparecen en el resultado (conteo = 0 se omite).
    Si se necesitan todos los estados con ceros, se puede hacer LEFT JOIN
    desde EstadoPedido hacia Pedido y usar coalesce(count, 0).
    """
    stmt = (
        select(
            Pedido.estado_pedido_codigo.label("estado"),
            func.count(Pedido.id).label("cantidad"),
        )
        .group_by(Pedido.estado_pedido_codigo)
        .order_by(func.count(Pedido.id).desc())
    )

    rows = session.exec(stmt).all()
    return [
        PedidosPorEstado(
            estado=row.estado,
            cantidad=row.cantidad or 0,
        )
        for row in rows
    ]
