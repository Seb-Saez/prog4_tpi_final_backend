from typing import Optional
from sqlmodel import SQLModel

from typing import Optional, List
from sqlmodel import SQLModel

class CategoriaBase(SQLModel):
    nombre: str
    descripcion: str
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None
    requiere_ingredientes: bool = True

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int

class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None
    requiere_ingredientes: Optional[bool] = None