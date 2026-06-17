"""
Router de autenticación y gestión de usuarios.

HTTP puro: parsear request, validar schema Pydantic, delegar al Service,
serializar response con response_model. No contiene lógica de negocio.

Capa: Router
Conoce a: Service (vía UoW)
NO conoce a: Repository, Model (solo esquemas Pydantic para response_model)

Regla de imports:
    Router → Service → UoW → Repository → Model
"""

from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.deps import get_current_active_user, require_role
from app.core.security import hash_token, create_access_token, create_refresh_token_pair
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork, get_uow
from app.modules.rol.enums import RolEnum
from app.modules.usuarios.schema import AdminUserCreate, UserCreate, UserUpdate, UserPublic
from app.modules.rol.unit_of_work import RolUnitOfWork, get_uow as get_rol_uow
from app.modules.usuarios.service import UsuarioService
from app.modules.refresh_token.model import RefreshToken

from app.core.rate_limit import register_limiter, login_limiter

auth = APIRouter(prefix="/api/v1/auth", tags=["auth"])
admin = APIRouter(prefix="/api/v1", tags=["admin"])

# ─── Registro ─────────────────────────────────────────────────────────────────


@auth.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
)
def register(
    user_in: UserCreate,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
    rol_uow: Annotated[RolUnitOfWork, Depends(get_rol_uow)],
):
    with uow, rol_uow:
        service = UsuarioService(uow, rol_uow)
        return service.register(user_in)


# ─── Login (OAuth2 Password Flow) ────────────────────────────────────────────


@auth.post("/token", dependencies=[Depends(login_limiter)])
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
    response: Response,
):
    with uow:
        service = UsuarioService(uow)
        token, refresh_plain = service.authenticate(form_data.username, form_data.password)

        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.COOKIE_SECURE,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_plain,
            httponly=True,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.COOKIE_SECURE,
        )
        return {"mensaje": "Login exitoso. Sesión iniciada."}


@auth.post("/logout")
def logout(
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    response: Response,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
):
    with uow:
        service = UsuarioService(uow)
        service.logout(current_user.id)
        service.revoke_refresh_tokens(current_user.id)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    return {"mensaje": "Sesión cerrada exitosamente"}


# ─── Refresh Token Rotation ──────────────────────────────────────────────────


@auth.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
):
    """
    Rota el refresh token: valida el token actual, lo revoca y emite
    un nuevo par (access token + refresh token).
    No requiere access token válido — es el mecanismo de renovación de sesión.
    """
    refresh_plain = request.cookies.get("refresh_token")
    if not refresh_plain:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado",
        )

    with uow:
        token_hash = hash_token(refresh_plain)
        rt = uow.refresh_tokens.get_by_token_hash(token_hash)

        ahora = datetime.now(timezone.utc)
        # La DB almacena datetimes naive (sin tzinfo); se compara contra UTC naive
        ahora_naive = datetime.utcnow()

        # Valida existencia, no revocado y no expirado
        if (
            not rt
            or rt.revoked_at is not None
            or rt.expires_at < ahora_naive
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado",
            )

        # Verifica que el usuario esté activo
        user = uow.usuarios.get_by_id(rt.usuario_id)
        if not user or user.disabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo o no encontrado",
            )

        # Revoca el token usado (rotación); revoked_at en UTC naive para consistencia con el modelo
        rt.revoked_at = ahora_naive
        uow.refresh_tokens.update(rt)

        # Emite nuevo access token
        roles = [ur.rol.codigo for ur in user.roles if ur.rol]
        new_access_token = create_access_token(
            data={"sub": user.username, "roles": roles},
            token_version=user.token_version,
        )

        # Emite nuevo refresh token
        new_refresh_plain, new_refresh_hash = create_refresh_token_pair()
        expires_at = ahora_naive + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        uow.refresh_tokens.add(RefreshToken(
            usuario_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=expires_at,
        ))

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_plain,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    return {"mensaje": "Token renovado exitosamente"}


# ─── Rutas protegidas ────────────────────────────────────────────────────────


@auth.get("/me", response_model=UserPublic)
def read_me(
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
):
    return current_user


@auth.get("/privado")
def ruta_privada(
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
):
    return {
        "mensaje": f"¡Hola, {current_user.full_name}! Accediste a una ruta privada.",
        "roles": current_user.roles,
    }


# ─── Rutas de administración (RBAC) ──────────────────────────────────────────


@admin.post(
    "/admin/usuarios",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_user(
    user_in: AdminUserCreate,
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
    rol_uow: Annotated[RolUnitOfWork, Depends(get_rol_uow)],
):
    with uow, rol_uow:
        service = UsuarioService(uow, rol_uow)
        return service.admin_create_user(user_in)


@admin.get("/admin/usuarios", response_model=list[UserPublic])
def list_users(
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.list_all()


@admin.post("/admin/usuarios/{user_id}/desactivar", response_model=UserPublic)
def deactivate_user(
    user_id: int,
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.set_disabled(user_id, disabled=True)


@admin.post("/admin/usuarios/{user_id}/activar", response_model=UserPublic)
def activate_user(
    user_id: int,
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
):
    with uow:
        service = UsuarioService(uow)
        return service.set_disabled(user_id, disabled=False)


