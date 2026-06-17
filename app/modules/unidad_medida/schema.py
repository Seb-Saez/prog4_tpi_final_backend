from typing import Optional
from sqlmodel import Field, SQLModel


class UnidadMedidaBase(SQLModel):
    nombre: str = Field(max_length=50)
    simbolo: str = Field(max_length=10)
    tipo: str = Field(max_length=20)


class UnidadMedidaCreate(UnidadMedidaBase):
    pass


class UnidadMedidaResponse(UnidadMedidaBase):
    id: int


class UnidadMedidaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, max_length=50)
    simbolo: Optional[str] = Field(default=None, max_length=10)
    tipo: Optional[str] = Field(default=None, max_length=20)
