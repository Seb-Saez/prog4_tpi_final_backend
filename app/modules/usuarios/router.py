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

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.deps import get_current_active_user, require_role
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork, get_uow
from app.modules.rol.enums import RolEnum
from app.modules.usuarios.schema import UserCreate, UserPublic
from app.modules.rol.unit_of_work import RolUnitOfWork, get_uow as get_rol_uow
from app.modules.usuarios.service import UsuarioService

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
        token = service.authenticate(form_data.username, form_data.password)

        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    return {"mensaje": "Sesión cerrada exitosamente"}


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


