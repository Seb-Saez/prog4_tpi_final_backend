from app.core.base_model import Auditoria
from sqlmodel import ARRAY, Column, Field, Integer, Relationship
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint
from decimal import Decimal

if TYPE_CHECKING:
    from app.modules.pedido.model import Pedido
    from app.modules.producto.model import Producto

class DetallePedido(Auditoria, table=True):
    __tablename__ = "detalle_pedido" # type: ignore

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="check_cantidad_positiva"),
        CheckConstraint("precio_unit_snap >= 0", name="check_precio_unit_snap_no_negativo"),
    )
    pedido_id: int = Field(foreign_key="pedido.id", index=True, ondelete="CASCADE",primary_key=True)
    producto_id: int = Field(foreign_key="producto.id", index=True, ondelete="RESTRICT",primary_key=True)
    cantidad: int
    nombre_snap: str = Field(max_length=255)
    precio_unit_snap: Decimal = Field(max_digits=10, decimal_places=2)
    subtotal_snap: Decimal = Field(max_digits=10, decimal_places=2)
    personalizacion: list[int] = Field(
        sa_column=Column(ARRAY(Integer),nullable=False,server_default="{}")
    )
    pedido: "Pedido" = Relationship(back_populates="detalles")
    producto: "Producto" = Relationship(back_populates="detalles")

