from app.core.base_model import BaseEntity
from sqlmodel import Field, Relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from app.core.datetime_utils import utcnow
if TYPE_CHECKING:
    from app.modules.usuarios.model import Usuario
    from app.modules.pedido.model import Pedido
    from app.modules.estado_pedido.model import EstadoPedido




class HistorialEstadoPedido(BaseEntity, table=True):
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    pedido_id: int = Field(foreign_key="pedido.id", index=True)
    estado_anterior: str | None = Field(foreign_key="estado_pedido.codigo", index=True, default=None)
    estado_nuevo: str = Field(foreign_key="estado_pedido.codigo", index=True)

    fecha_cambio: datetime = Field(default_factory=utcnow)
    motivo: Optional[str] = None

    usuario: "Usuario" = Relationship(back_populates="historiales_estado_pedido")
    pedido: "Pedido" = Relationship(back_populates="historial_estado_pedido")
    estado_anterior_rel: Optional["EstadoPedido"] = Relationship(
        back_populates="historiales_estado_pedido_anterior",
        sa_relationship_kwargs={
            "lazy": "joined",
            "foreign_keys": "[HistorialEstadoPedido.estado_anterior]",
        },
    )
    estado_nuevo_rel: "EstadoPedido" = Relationship(
        back_populates="historiales_estado_pedido_nuevo",
        sa_relationship_kwargs={
            "lazy": "joined",
            "foreign_keys": "[HistorialEstadoPedido.estado_nuevo]",
        },
    )