from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from ..producto_categoria.model import ProductoCategoria
from app.core.base_model import BaseEntity

if TYPE_CHECKING:
    from app.modules.producto.model import Producto

class Categoria(BaseEntity, table=True):
    __tablename__ = "categoria" # type: ignore[assignment]

    parent_id: Optional[int] = Field(foreign_key="categoria.id", default=None)

    nombre: str
    descripcion: str
    imagen_url: Optional[str] = None
    requiere_ingredientes: bool = Field(default=True)

    productos: List["Producto"] = Relationship(
        back_populates="categorias",
        link_model=ProductoCategoria
    )
    