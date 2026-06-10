from typing import Optional
from sqlmodel import SQLModel


class UnidadMedidaBase(SQLModel):
    nombre: str
    simbolo: str
    tipo: str


class UnidadMedidaCreate(UnidadMedidaBase):
    pass


class UnidadMedidaResponse(UnidadMedidaBase):
    id: int


class UnidadMedidaUpdate(SQLModel):
    nombre: Optional[str] = None
    simbolo: Optional[str] = None
    tipo: Optional[str] = None
