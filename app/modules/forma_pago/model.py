from typing import TYPE_CHECKING, List, Optional
from app.core.base_model import BaseEntity
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from app.modules.pedido.model import Pedido

class FormaPago(BaseEntity, table=True):
    __tablename__ = "forma_pago" #type: ignore
    codigo: str = Field(max_length=20, unique=True)
    descripcion: str = Field(max_length=100)
    habilitado: bool = Field(default=True)

    pedidos: List["Pedido"] = Relationship(back_populates="forma_pago")