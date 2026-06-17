from typing import Optional
from sqlmodel import Field, SQLModel

class IngredienteBase(SQLModel):

    nombre: str
    descripcion: str
    es_alergeno: bool
    stock_cantidad: int = Field(default=0, ge=0)

class IngredienteCreate(IngredienteBase):
    pass

class IngredienteResponse(IngredienteBase):
    id: int

class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)

class AjustarStockRequest(SQLModel):
    """Payload para ajustar el stock de un ingrediente.

    stock_cantidad == 0  → marcar como faltante (deshabilita productos afectados).
    stock_cantidad > 0   → reponer stock (reactiva productos cuando corresponde).
    """
    stock_cantidad: int = Field(ge=0, description="Nueva cantidad de stock del ingrediente")