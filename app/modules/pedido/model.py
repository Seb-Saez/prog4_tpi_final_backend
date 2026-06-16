from typing import Optional, List, TYPE_CHECKING
from sqlmodel import  Field, Relationship
from app.core.base_model import BaseEntity
from app.modules.pedido.enums import ModalidadEntrega
from decimal import Decimal

if TYPE_CHECKING:
    from app.modules.usuarios.model import Usuario
    from app.modules.direccion.model import DireccionEntrega
    from app.modules.estado_pedido.model import EstadoPedido
    from app.modules.historial_pedido.model import HistorialEstadoPedido
    from app.modules.detalle_pedido.model import DetallePedido
    from app.modules.forma_pago.model import FormaPago





class Pedido(BaseEntity, table=True):

    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    direccion_id: Optional[int] = Field(default=None, foreign_key="direccion_entrega.id", index=True)
    estado_pedido_codigo: str = Field(foreign_key="estado_pedido.codigo", index=True)
    forma_pago_id: int = Field(foreign_key="forma_pago.id", index=True)
    modalidad_entrega: ModalidadEntrega = Field(index=True)
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)
    descuento: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    total: Decimal = Field(max_digits=10, decimal_places=2)
    costo_envio: Decimal = Field(max_digits=10, decimal_places=2)
    notas : Optional[str] = Field(default=None, max_length=500)

    forma_pago_snap: Optional[str] = None
    direccion_snap: Optional[str] = None

    mp_preference_id: Optional[str] = None
    mp_payment_id: Optional[str] = None
    mp_payment_status: Optional[str] = None

    usuario: "Usuario" = Relationship(back_populates="pedidos")
    estado_pedido: "EstadoPedido" = Relationship(back_populates="pedidos")
    direccion: Optional["DireccionEntrega"] = Relationship(back_populates="pedidos")
    detalles: List["DetallePedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
        )
    forma_pago: "FormaPago" = Relationship(back_populates="pedidos")
    historial_estado_pedido: List["HistorialEstadoPedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"order_by": "HistorialEstadoPedido.fecha_cambio"},
    )


