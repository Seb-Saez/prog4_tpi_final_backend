from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship
from app.core.base_model import BaseEntity

if TYPE_CHECKING:
    from app.modules.usuarios.model import Usuario


class Rol(BaseEntity, table=True):
    __tablename__ = "rol"  # type: ignore[assignment]

    codigo: str = Field(index=True, unique=True)
    descripcion: str

    usuarios: List["UsuarioRol"] = Relationship(back_populates="rol")


class UsuarioRol(BaseEntity, table=True):
    __tablename__ = "usuario_rol"  # type: ignore[assignment]

    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    rol_id: int = Field(foreign_key="rol.id", index=True)
    # Asignación de rol temporal opcional (v7). NULL = rol permanente.
    expires_at: Optional[datetime] = Field(default=None, index=True)

    usuario: "Usuario" = Relationship(back_populates="roles")
    rol: "Rol" = Relationship(back_populates="usuarios")
