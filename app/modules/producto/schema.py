from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime


class ProductoIngredienteInput(SQLModel):
    ingrediente_id: int
    cantidad: float | None = None
    unidad_medida_id: int | None = None
    es_removible: bool = False


class ProductoIngredienteOut(SQLModel):
    ingrediente_id: int
    cantidad: float | None = None
    unidad_medida_id: int | None = None
    es_removible: bool = False
    nombre: str
    stock_cantidad: int


class ProductoBase(SQLModel):
    nombre: str
    descripcion: str
    precio_base: float = Field(ge=0)
    imagenes_url: Optional[List[str]] = None
    stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = True
    unidad_venta_id: Optional[int] = None
    categorias_ids: List[int] = []
    ingredientes_ids: List[int] = []
    ingredientes: List[ProductoIngredienteInput] = []


class ProductoCreate(ProductoBase):
    pass


class ProductoResponse(ProductoBase):
    id: int


class ProductoUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_base: Optional[float] = Field(default=None, ge=0)
    imagenes_url: Optional[List[str]] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None
    unidad_venta_id: Optional[int] = None
    categorias_ids: Optional[List[int]] = None
    ingredientes: Optional[List[ProductoIngredienteInput]] = None


class DisponibilidadUpdate(SQLModel):
    disponible: bool


class ImagenesUpdate(SQLModel):
    imagenes_url: Optional[List[str]] = None
