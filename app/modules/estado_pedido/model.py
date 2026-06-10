from typing import List, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.historial_pedido.model import HistorialEstadoPedido
    from app.modules.pedido.model import Pedido


class EstadoPedido(SQLModel, table=True):
    __tablename__ = "estado_pedido" # type: ignore

    codigo: str = Field(max_length=20, unique=True, primary_key=True)
    nombre: str = Field(max_length=50, unique=True)
    orden: int = Field(unique=True)
    descripcion: str = Field(max_length=255, nullable=True)
    es_terminal: bool = Field(default=False)
    permite_cancelar: bool = Field(default=False)

    pedidos: List["Pedido"] = Relationship(back_populates="estado_pedido")

    historiales_estado_pedido_anterior: List["HistorialEstadoPedido"] = Relationship(
        back_populates="estado_anterior_rel",
        sa_relationship_kwargs={
            "foreign_keys": "[HistorialEstadoPedido.estado_anterior]",
        },
    )
    historiales_estado_pedido_nuevo: List["HistorialEstadoPedido"] = Relationship(
        back_populates="estado_nuevo_rel",
        sa_relationship_kwargs={
            "foreign_keys": "[HistorialEstadoPedido.estado_nuevo]",
        },
    )
