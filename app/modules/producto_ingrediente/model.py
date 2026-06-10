from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from app.core.base_model import Auditoria

if TYPE_CHECKING:
    from app.modules.producto.model import Producto
    from app.modules.ingrediente.model import Ingrediente


class ProductoIngrediente(Auditoria, table=True):
    __tablename__ = "producto_ingrediente"  # type: ignore[assignment]

    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    ingrediente_id: int = Field(foreign_key="ingrediente.id", primary_key=True)

    cantidad: float | None = None
    unidad_medida_id: int | None = Field(foreign_key="unidad_medida.id", default=None)
    es_removible: bool = False

    producto: Optional["Producto"] = Relationship(
        back_populates="producto_ingredientes"
    )
    ingrediente: Optional["Ingrediente"] = Relationship(
        back_populates="producto_ingredientes"
    )
