from typing import Sequence
from fastapi import HTTPException, status
from app.modules.rol.model import Rol, UsuarioRol
from app.modules.rol.unit_of_work import RolUnitOfWork
from app.modules.usuarios.model import Usuario
from app.modules.usuarios.schema import UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


class RolService:
    """Servicio de gestión de roles y asignaciones a usuarios."""

    def __init__(self, rol_uow: RolUnitOfWork, usuario_uow: UsuarioUnitOfWork):
        self.rol_uow = rol_uow
        self.usuario_uow = usuario_uow

    def get_all(self) -> Sequence[Rol]:
        return self.rol_uow.roles.get_all()

    def get_by_codigo(self, codigo: str) -> Rol | None:
        return self.rol_uow.roles.get_by_codigo(codigo)

    def assign_rol(self, user_id: int, rol_codigo: str) -> UserPublic:
        user = self.usuario_uow.usuarios.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        rol = self.rol_uow.roles.get_by_codigo(rol_codigo)
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado",
            )

        if any(ur.rol_id == rol.id for ur in user.roles):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya tiene ese rol",
            )

        self.rol_uow.usuarios_roles.add(UsuarioRol(usuario_id=user.id, rol_id=rol.id))
        self.usuario_uow.session.refresh(user)
        return UserPublic.model_validate(user)

    def remove_rol(self, user_id: int, rol_codigo: str) -> UserPublic:
        user = self.usuario_uow.usuarios.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        rol = self.rol_uow.roles.get_by_codigo(rol_codigo)
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado",
            )

        usuario_rol = next((ur for ur in user.roles if ur.rol_id == rol.id), None)
        if not usuario_rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El usuario no tiene ese rol",
            )

        self.rol_uow.usuarios_roles.hard_delete(usuario_rol)
        self.usuario_uow.session.refresh(user)
        return UserPublic.model_validate(user)
