"""Schemas de respuesta para el módulo de estadísticas."""
from decimal import Decimal
from typing import Optional
from sqlmodel import SQLModel


class ResumenKPI(SQLModel):
    """KPIs generales del negocio (excluye pedidos CANCELADO)."""
    total_pedidos: int
    ventas_totales: Decimal
    ticket_promedio: Decimal
    pedidos_pendientes: int
    productos_activos: int
    ventas_hoy: Decimal
    ventas_mes: Decimal


class IngresosPorFormaPago(SQLModel):
    """Ingresos agrupados por forma de pago (excluye pedidos CANCELADO)."""
    forma_pago: str
    total: Decimal
    cantidad: int


class PeriodoVentas(SQLModel):
    """Punto de la serie temporal de ventas."""
    periodo: str       # "YYYY-MM-DD" para día, "YYYY-MM" para mes
    total: Decimal
    cantidad_pedidos: int


class ProductoMasVendido(SQLModel):
    """Producto con mayor volumen de ventas (por cantidad de unidades)."""
    producto_id: Optional[int]   # None si el producto fue eliminado
    nombre: str
    cantidad_vendida: int
    ingresos: Decimal


class VentasPorCategoria(SQLModel):
    """Ingresos y unidades vendidas agrupados por categoría."""
    categoria_id: int
    categoria: str
    total: Decimal
    cantidad: int


class PedidosPorEstado(SQLModel):
    """Distribución de pedidos por estado."""
    estado: str
    cantidad: int
