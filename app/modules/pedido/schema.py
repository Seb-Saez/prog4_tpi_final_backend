from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from app.modules.pedido.enums import ModalidadEntrega


# ============================================================
# INPUTS — lo que envía el cliente
# ============================================================

class DetallePedidoInput(SQLModel):
    """Item del carrito enviado por el cliente."""
    producto_id: int = Field(ge=1)
    cantidad: int = Field(ge=1)
    personalizacion: List[int] = []


class PedidoCreate(SQLModel):
    """Payload para crear un pedido desde el carrito.

    NO viene: usuario_id (sale del token), precios, subtotal, total,
    estado, snapshots. Todo eso lo resuelve el servidor.
    """
    modalidad_entrega: ModalidadEntrega
    forma_pago_id: int = Field(ge=1)
    direccion_id: Optional[int] = Field(default=None, ge=1)
    items: List[DetallePedidoInput] = Field(min_length=1)
    notas: Optional[str] = None

    @model_validator(mode="after")
    def _validar_direccion_segun_modalidad(self) -> "PedidoCreate":
        if (
            self.modalidad_entrega == ModalidadEntrega.DELIVERY
            and self.direccion_id is None
        ):
            raise ValueError(
                "direccion_id es obligatorio cuando modalidad_entrega es DELIVERY"
            )
        return self


# ============================================================
# OUTPUTS — lo que devuelve el servidor
# ============================================================

class DetallePedidoOut(SQLModel):
    producto_id: int
    cantidad: int
    nombre_snap: str
    precio_unit_snap: Decimal
    subtotal_snap: Decimal
    personalizacion: List[int]


class EstadoPedidoOut(SQLModel):
    codigo: str
    nombre: str
    orden: int
    es_terminal: bool
    permite_cancelar: bool


class HistorialEstadoOut(SQLModel):
    estado_anterior: Optional[str]
    estado_nuevo: str
    usuario_id: int
    fecha_cambio: datetime


class PedidoResumen(SQLModel):
    """Vista de cabecera para listados — sin detalles ni historial."""
    id: int
    usuario_id: int
    modalidad_entrega: ModalidadEntrega
    estado_pedido: EstadoPedidoOut
    subtotal: Decimal
    costo_envio: Decimal
    total: Decimal
    created_at: datetime


class PedidoResponse(SQLModel):
    """Vista completa del pedido — para el detalle individual."""
    id: int
    usuario_id: int
    modalidad_entrega: ModalidadEntrega
    direccion_id: Optional[int]
    forma_pago_id: int
    estado_pedido: EstadoPedidoOut
    subtotal: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: Optional[str]
    forma_pago_snap: Optional[str]
    direccion_snap: Optional[str]
    detalles: List[DetallePedidoOut]
    historial_estado_pedido: List[HistorialEstadoOut]
    created_at: datetime
