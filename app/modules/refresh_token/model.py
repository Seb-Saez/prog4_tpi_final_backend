from datetime import datetime
from sqlmodel import Field, Relationship
from app.core.base_model import BaseEntity
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.usuarios.model import Usuario


class RefreshToken(BaseEntity, table=True):
    __tablename__ = "refresh_token" # type: ignore[assignment]

    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    token_hash: str = Field(max_length=64)
    expires_at: datetime
    revoked_at: datetime | None = None

    usuario: "Usuario" = Relationship(back_populates="refresh_tokens")