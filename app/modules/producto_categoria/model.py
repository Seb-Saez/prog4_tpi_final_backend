from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from app.core.base_model import Auditoria


class ProductoCategoria(Auditoria, table=True):
    
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    categoria_id: int = Field(foreign_key="categoria.id", primary_key=True)

    es_principal: bool = False
