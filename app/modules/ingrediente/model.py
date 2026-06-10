from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel,Field, Relationship
from datetime import datetime
from app.core.base_model import BaseEntity


if TYPE_CHECKING:
    from app.modules.producto_ingrediente.model import ProductoIngrediente

class Ingrediente(BaseEntity, table=True):

    nombre: str
    descripcion: str
    es_alergeno: bool

    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="ingrediente"
    )
