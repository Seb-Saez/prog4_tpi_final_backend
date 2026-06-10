from typing import Optional
from sqlmodel import SQLModel, Field

class DireccionBase(SQLModel):
    alias: str
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: str
    codigo_postal: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    es_principal: bool = False

class DireccionCreate(DireccionBase):
    pass

class DireccionResponse(DireccionBase):
    id: int
    usuario_id: int
    
class DireccionUpdate(SQLModel):
    alias: Optional[str] = None
    linea1: Optional[str] = None
    linea2: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    es_principal: Optional[bool] = None