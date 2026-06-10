from typing import List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import  Field, Relationship
from app.core.base_model import BaseEntity

if TYPE_CHECKING:
    from app.modules.producto.model import Producto

class UnidadMedida(BaseEntity, table=True):
    __tablename__ = "unidad_medida" # type: ignore[assignment]

    nombre: str = Field(max_length=50)
    simbolo: str = Field(max_length=10)
    tipo: str = Field(max_length=20)

    productos: List["Producto"] = Relationship(back_populates="unidad_venta")
