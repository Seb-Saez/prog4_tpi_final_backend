from typing import Sequence

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schema import UserCreate, Token, UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork
from app.modules.rol.model import UsuarioRol
from app.modules.rol.enums import RolEnum
from app.modules.rol.unit_of_work import RolUnitOfWork


class UsuarioService:
    def __init__(self, uow: UsuarioUnitOfWork, rol_uow: RolUnitOfWork | None = None):
        self.uow = uow
        self.rol_uow = rol_uow

    def register(self, user_in: UserCreate) -> UserPublic:
        if not self.rol_uow:
            raise RuntimeError("RolUnitOfWork requerido para registro con asignación de rol")

        if self.uow.usuarios.get_by_username(user_in.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de usuario ya está en uso",
            )

        if self.uow.usuarios.get_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado",
            )

        usuario = Usuario(
            username=user_in.username,
            full_name=user_in.full_name,
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
        )

        nuevo = self.uow.usuarios.add(usuario)

        rol_cliente = self.rol_uow.roles.get_by_codigo(RolEnum.CLIENTE)
        if rol_cliente:
            self.rol_uow.usuarios_roles.add(UsuarioRol(usuario_id=nuevo.id, rol_id=rol_cliente.id))
            self.uow.usuarios.session.refresh(nuevo)

        return UserPublic.model_validate(nuevo)

    def authenticate(self, username: str, password: str) -> Token:
        user = self.uow.usuarios.get_by_username(username)
        if not user:
            user = self.uow.usuarios.get_by_email(username)

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cuenta de usuario desactivada",
            )

        roles = [ur.rol.codigo for ur in user.roles if ur.rol]

        access_token = create_access_token(
            data={"sub": user.username, "roles": roles},
            token_version=user.token_version,
        )
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def list_all(self) -> Sequence[Usuario]:
        return self.uow.usuarios.get_all()

    def set_disabled(self, user_id: int, disabled: bool) -> Usuario:
        user = self.uow.usuarios.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        user.disabled = disabled
        return self.uow.usuarios.update(user)

    def logout(self, user_id: int) -> None:
        user = self.uow.usuarios.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        user.token_version += 1
        self.uow.usuarios.update(user)
