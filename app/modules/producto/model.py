from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY

from ..producto_categoria.model import ProductoCategoria
from app.core.base_model import BaseEntity
from decimal import Decimal
if TYPE_CHECKING:
    from app.modules.categoria.model import Categoria
    from app.modules.unidad_medida.model import UnidadMedida
    from app.modules.producto_ingrediente.model import ProductoIngrediente
    from app.modules.detalle_pedido.model import DetallePedido

class Producto(BaseEntity, table=True):

    nombre: str
    descripcion: str
    precio_base: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    imagenes_url: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = True
    unidad_venta_id: Optional[int] = Field(foreign_key="unidad_medida.id", default=None)

    categorias: List["Categoria"] = Relationship(
        back_populates="productos",
        link_model=ProductoCategoria
    )

    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="producto"
    )

    unidad_venta: Optional["UnidadMedida"] = Relationship(back_populates="productos")

    detalles : List["DetallePedido"] = Relationship(back_populates="producto")


    @property
    def categorias_ids(self) -> list[int]:
        return [cat.id for cat in self.categorias] if self.categorias else []

    @property
    def ingredientes(self) -> list[dict]:
        if not self.producto_ingredientes:
            return []
        return [
            {
                "ingrediente_id": pi.ingrediente_id,
                "cantidad": pi.cantidad,
                "unidad_medida_id": pi.unidad_medida_id,
                "es_removible": pi.es_removible,
            }
            for pi in self.producto_ingredientes
        ]

    @property
    def ingredientes_ids(self) -> List[int]:
        return [pi.ingrediente_id for pi in self.producto_ingredientes] if self.producto_ingredientes else []
