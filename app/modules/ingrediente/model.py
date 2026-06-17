from typing import List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from sqlalchemy import CheckConstraint
from app.core.base_model import BaseEntity


if TYPE_CHECKING:
    from app.modules.producto_ingrediente.model import ProductoIngrediente

class Ingrediente(BaseEntity, table=True):
    __table_args__ = (
        CheckConstraint("stock_cantidad >= 0", name="ck_ingrediente_stock_no_negativo"),
    )

    nombre: str
    descripcion: str
    es_alergeno: bool
    stock_cantidad: int = Field(default=0, ge=0)

    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="ingrediente"
    )
