"""
Router de administración de roles.

Responsabilidad:
- Listar roles del sistema
- Asignar y quitar roles a usuarios (RBAC: solo ADMIN)

HTTP puro: parsear request, validar schema Pydantic, delegar al Service,
serializar response con response_model. No contiene lógica de negocio.

Capa: Router
Conoce a: Service (vía UoW)
NO conoce a: Repository, Model (solo esquemas Pydantic para response_model)
"""

from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.deps import get_current_active_user, require_role
from app.modules.rol.enums import RolEnum
from app.modules.rol.schema import RolPublic, UserRolAssign
from app.modules.rol.service import RolService
from app.modules.rol.unit_of_work import RolUnitOfWork, get_uow as get_rol_uow
from app.modules.usuarios.schema import UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork, get_uow as get_user_uow

admin = APIRouter(prefix="/api/v1", tags=["admin"])


@admin.get("/admin/roles", response_model=list[RolPublic])
def list_roles(
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    rol_uow: Annotated[RolUnitOfWork, Depends(get_rol_uow)],
):
    with rol_uow:
        return list(rol_uow.roles.get_all())


@admin.post("/admin/usuarios/{user_id}/roles", response_model=UserPublic)
def assign_user_rol(
    user_id: int,
    payload: UserRolAssign,
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    rol_uow: Annotated[RolUnitOfWork, Depends(get_rol_uow)],
    user_uow: Annotated[UsuarioUnitOfWork, Depends(get_user_uow)],
):
    with rol_uow, user_uow:
        service = RolService(rol_uow, user_uow)
        return service.assign_rol(user_id, payload.rol_codigo)


@admin.delete("/admin/usuarios/{user_id}/roles/{rol_codigo}", response_model=UserPublic)
def remove_user_rol(
    user_id: int,
    rol_codigo: str,
    _admin: Annotated[UserPublic, Depends(require_role([RolEnum.ADMIN]))],
    rol_uow: Annotated[RolUnitOfWork, Depends(get_rol_uow)],
    user_uow: Annotated[UsuarioUnitOfWork, Depends(get_user_uow)],
):
    with rol_uow, user_uow:
        service = RolService(rol_uow, user_uow)
        return service.remove_rol(user_id, rol_codigo)
