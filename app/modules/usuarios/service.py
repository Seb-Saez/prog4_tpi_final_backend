from typing import Sequence
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token_pair, hash_token
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schema import UserCreate, Token, UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork
from app.modules.rol.model import UsuarioRol
from app.modules.rol.enums import RolEnum
from app.modules.rol.unit_of_work import RolUnitOfWork
from app.modules.refresh_token.model import RefreshToken


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

        rol_cliente = self.rol_uow.roles.get_by_codigo(RolEnum.CLIENT)
        if rol_cliente:
            self.rol_uow.usuarios_roles.add(UsuarioRol(usuario_id=nuevo.id, rol_id=rol_cliente.id))
            self.uow.usuarios.session.refresh(nuevo)

        return UserPublic.model_validate(nuevo)

    def authenticate(self, username: str, password: str) -> tuple[Token, str]:
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
        token = Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        # Genera y persiste el refresh token; expires_at en UTC naive para consistencia con el modelo
        refresh_plain, refresh_hash = create_refresh_token_pair()
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.uow.refresh_tokens.add(RefreshToken(
            usuario_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        ))

        return token, refresh_plain

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

    def revoke_refresh_tokens(self, user_id: int) -> None:
        """Revoca todos los refresh tokens activos del usuario."""
        self.uow.refresh_tokens.revoke_all_for_usuario(user_id)
