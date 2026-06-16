from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship

from app.core.base_model import BaseEntity

if TYPE_CHECKING:
    from app.modules.direccion.model import DireccionEntrega
    from app.modules.refresh_token.model import RefreshToken
    from app.modules.historial_pedido.model import HistorialEstadoPedido
    from app.modules.pedido.model import Pedido


class Usuario(BaseEntity, table=True):
    __tablename__ = "usuario"  # type: ignore[assignment]

    username: str = Field(index=True, unique=True)
    full_name: str
    email: str = Field(index=True, unique=True)
    hashed_password: str
    disabled: bool = Field(default=False)
    token_version: int = Field(default=0)
    celular: Optional[str] = None

    direcciones: List["DireccionEntrega"] = Relationship(back_populates="usuario")

    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="usuario")

    historiales_estado_pedido: List["HistorialEstadoPedido"] = Relationship(back_populates="usuario")

    pedidos: List["Pedido"] = Relationship(back_populates="usuario")

    roles: List["UsuarioRol"] = Relationship(back_populates="usuario")