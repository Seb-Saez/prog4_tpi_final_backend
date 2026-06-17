"""Router para el módulo de estadísticas y reportes agregados.

Todos los endpoints requieren rol ADMIN.
Las consultas son de solo lectura; no producen efectos secundarios.
"""
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.rol.enums import RolEnum

from .schema import (
    IngresosPorFormaPago,
    PedidosPorEstado,
    PeriodoVentas,
    ProductoMasVendido,
    ResumenKPI,
    VentasPorCategoria,
)
from .service import (
    obtener_ingresos_por_forma_pago,
    obtener_pedidos_por_estado,
    obtener_productos_mas_vendidos,
    obtener_resumen,
    obtener_ventas_por_categoria,
    obtener_ventas_por_periodo,
)

router_estadisticas = APIRouter(
    prefix="/api/v1/estadisticas",
    tags=["estadisticas"],
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)


@router_estadisticas.get("/resumen", response_model=ResumenKPI)
def resumen(session: Session = Depends(get_session)) -> ResumenKPI:
    """KPIs principales: totales de ventas, ticket promedio y conteos clave."""
    return obtener_resumen(session)


@router_estadisticas.get("/ventas-por-periodo", response_model=list[PeriodoVentas])
def ventas_por_periodo(
    session: Session = Depends(get_session),
    desde: Annotated[
        date,
        Query(description="Fecha de inicio del período (YYYY-MM-DD)"),
    ] = None,
    hasta: Annotated[
        date,
        Query(description="Fecha de fin del período (YYYY-MM-DD)"),
    ] = None,
    agrupacion: Annotated[
        Literal["dia", "mes"],
        Query(description="Granularidad de la agrupación temporal"),
    ] = "dia",
) -> list[PeriodoVentas]:
    """Serie temporal de ventas dentro del rango indicado.

    Por defecto devuelve los últimos 30 días agrupados por día.
    Excluye pedidos en estado CANCELADO.
    """
    hoy = date.today()
    if hasta is None:
        hasta = hoy
    if desde is None:
        desde = hoy - timedelta(days=30)

    return obtener_ventas_por_periodo(session, desde, hasta, agrupacion)


@router_estadisticas.get("/productos-mas-vendidos", response_model=list[ProductoMasVendido])
def productos_mas_vendidos(
    session: Session = Depends(get_session),
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Cantidad máxima de productos a retornar"),
    ] = 10,
) -> list[ProductoMasVendido]:
    """Top N productos ordenados por unidades vendidas (excluye pedidos CANCELADO)."""
    return obtener_productos_mas_vendidos(session, limit=limit)


@router_estadisticas.get("/ventas-por-categoria", response_model=list[VentasPorCategoria])
def ventas_por_categoria(
    session: Session = Depends(get_session),
) -> list[VentasPorCategoria]:
    """Ingresos y unidades vendidas agrupados por categoría de producto.

    Un producto con múltiples categorías se contabiliza en cada una de ellas.
    """
    return obtener_ventas_por_categoria(session)


@router_estadisticas.get("/pedidos-por-estado", response_model=list[PedidosPorEstado])
def pedidos_por_estado(
    session: Session = Depends(get_session),
) -> list[PedidosPorEstado]:
    """Distribución de pedidos agrupados por estado (incluye todos los estados con pedidos)."""
    return obtener_pedidos_por_estado(session)


@router_estadisticas.get("/ingresos-por-forma-pago", response_model=list[IngresosPorFormaPago])
def ingresos_por_forma_pago(
    session: Session = Depends(get_session),
) -> list[IngresosPorFormaPago]:
    """Ingresos y cantidad de pedidos agrupados por forma de pago.

    Excluye pedidos en estado CANCELADO (EST-01).
    """
    return obtener_ingresos_por_forma_pago(session)
