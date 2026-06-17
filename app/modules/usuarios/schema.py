from typing import Any, Optional

from pydantic import EmailStr, field_validator, model_validator
from sqlmodel import SQLModel, Field


class UserCreate(SQLModel):
    """Datos requeridos para registrar un usuario."""
    username:  str
    full_name: str
    email:     EmailStr
    password:  str = Field(min_length=8)
    celular:   Optional[str] = None


class AdminUserCreate(SQLModel):
    """Datos para crear un usuario desde el panel de administración."""
    username:  str
    full_name: str
    email:     EmailStr
    password:  str = Field(min_length=8)
    roles:     list[str] = Field(default_factory=lambda: ["CLIENT"])

    @field_validator("roles")
    @classmethod
    def default_client_if_empty(cls, v: list[str]) -> list[str]:
        return v if v else ["CLIENT"]


class UserUpdate(SQLModel):
    """Campos actualizables de un usuario desde administración.

    Todos opcionales: solo se modifican los que vengan en el request. El username
    no es editable (es el identificador de login). Si `password` viene, se
    re-hashea e invalida las sesiones activas del usuario.
    """
    full_name: Optional[str]      = None
    email:     Optional[EmailStr] = None
    celular:   Optional[str]      = None
    password:  Optional[str]      = Field(default=None, min_length=8)


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
