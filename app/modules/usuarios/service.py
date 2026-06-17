from typing import Sequence
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token_pair, hash_token
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schema import AdminUserCreate, UserCreate, UserUpdate, Token, UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork
from app.modules.rol.model import UsuarioRol
from app.modules.rol.enums import RolEnum
from app.modules.rol.unit_of_work import RolUnitOfWork
from app.modules.refresh_token.model import RefreshToken


class UsuarioService:
    def __init__(self, uow: UsuarioUnitOfWork, rol_uow: RolUnitOfWork | None = None):
        self.uow = uow
        self.rol_uow = rol_uow

    # ── shared private helpers ────────────────────────────────────────────────

    def _check_unique(self, username: str, email: str) -> None:
        """Raise 409 if username or email is already taken."""
        if self.uow.usuarios.get_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de usuario ya está en uso",
            )
        if self.uow.usuarios.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado",
            )

    def _build_usuario(self, username: str, full_name: str, email: str, password: str) -> Usuario:
        return Usuario(
            username=username,
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
        )

    # ── public methods ────────────────────────────────────────────────────────

    def register(self, user_in: UserCreate) -> UserPublic:
        if not self.rol_uow:
            raise RuntimeError("RolUnitOfWork requerido para registro con asignación de rol")

        self._check_unique(user_in.username, user_in.email)

        usuario = self._build_usuario(
            user_in.username, user_in.full_name, user_in.email, user_in.password
        )
        nuevo = self.uow.usuarios.add(usuario)

        rol_cliente = self.rol_uow.roles.get_by_codigo(RolEnum.CLIENT)
        if rol_cliente:
            self.rol_uow.usuarios_roles.add(UsuarioRol(usuario_id=nuevo.id, rol_id=rol_cliente.id))
            self.uow.usuarios.session.refresh(nuevo)

        return UserPublic.model_validate(nuevo)

    def admin_create_user(self, user_in: AdminUserCreate) -> UserPublic:
        """Create a user with an explicit list of roles (admin-only operation)."""
        if not self.rol_uow:
            raise RuntimeError("RolUnitOfWork requerido para admin_create_user")

        self._check_unique(user_in.username, user_in.email)

        usuario = self._build_usuario(
            user_in.username, user_in.full_name, user_in.email, user_in.password
        )
        nuevo = self.uow.usuarios.add(usuario)

        for rol_codigo in user_in.roles:
            rol = self.rol_uow.roles.get_by_codigo(rol_codigo)
            if not rol:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Rol no encontrado: {rol_codigo}",
                )
            self.rol_uow.usuarios_roles.add(UsuarioRol(usuario_id=nuevo.id, rol_id=rol.id))

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

    def admin_update_user(self, user_id: int, data: UserUpdate) -> UserPublic:
        """Edita los campos de un usuario (operación de admin).

        Solo toca los campos presentes en el request. Valida unicidad del email
        si cambia. Si viene una nueva contraseña, la re-hashea e incrementa el
        token_version para invalidar las sesiones activas del usuario.
        """
        user = self.uow.usuarios.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        update_fields = data.model_dump(exclude_unset=True)

        nuevo_email = update_fields.get("email")
        if nuevo_email and nuevo_email != user.email:
            existente = self.uow.usuarios.get_by_email(nuevo_email)
            if existente and existente.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está registrado",
                )
            user.email = nuevo_email

        if "full_name" in update_fields:
            user.full_name = update_fields["full_name"]
        if "celular" in update_fields:
            user.celular = update_fields["celular"]

        nueva_password = update_fields.get("password")
        if nueva_password:
            user.hashed_password = hash_password(nueva_password)
            user.token_version += 1  # invalida sesiones activas tras cambiar la pass

        return UserPublic.model_validate(self.uow.usuarios.update(user))

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
