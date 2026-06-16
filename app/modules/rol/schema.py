from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class RolPublic(SQLModel):
    """Vista pública de un rol."""
    id:          int
    codigo:      str
    descripcion: str


class UserRolAssign(SQLModel):
    """Payload para que un admin asigne un rol a un usuario."""
    rol_codigo: str
    # Vencimiento opcional del rol (v7). NULL = rol permanente.
    expires_at: Optional[datetime] = None
