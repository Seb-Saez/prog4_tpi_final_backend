from typing import Any, Optional

from pydantic import EmailStr, model_validator
from sqlmodel import SQLModel, Field


class UserCreate(SQLModel):
    """Datos requeridos para registrar un usuario."""
    username:  str
    full_name: str
    email:     EmailStr
    password:  str = Field(min_length=8)
    celular:   Optional[str] = None


class UserUpdate(SQLModel):
    """Campos actualizables del usuario — todos opcionales."""
    full_name: Optional[str] = None
    celular:   Optional[str] = None


class UserPublic(SQLModel):
    """Vista pública del usuario — excluye hashed_password."""
    id:        int
    username:  str
    full_name: str
    email:     str
    roles:     list[str]
    disabled:  bool
    celular:   Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def extract_roles(cls, data: Any) -> Any:
        if hasattr(data, "roles"):
            # Si viene una instancia ORM con relación roles → extraemos códigos
            data = {
                "id": data.id,
                "username": data.username,
                "full_name": data.full_name,
                "email": data.email,
                "roles": [ur.rol.codigo for ur in data.roles if ur.rol],
                "disabled": data.disabled,
                "celular": getattr(data, "celular", None),
            }
        return data


class Token(SQLModel):
    """Respuesta del endpoint /token."""
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int
