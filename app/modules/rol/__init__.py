"""
Módulo de Roles del sistema.

Entidades:
- Rol: catálogo de roles (ADMIN, CLIENT, PEDIDOS, STOCK)
- UsuarioRol: tabla intermedia many-to-many entre Usuario y Rol

Responsabilidad:
- Gestión del catálogo de roles
- Asignación y remoción de roles a usuarios (solo ADMIN)
- Consulta de roles por usuario

Regla de imports:
    Router → Service → UoW → Repository → Model
"""

from app.modules.rol.model import Rol, UsuarioRol
from app.modules.rol.enums import RolEnum
from app.modules.rol.repository import RolRepository, UsuarioRolRepository
from app.modules.rol.schema import RolPublic, UserRolAssign
from app.modules.rol.unit_of_work import RolUnitOfWork, get_uow

__all__ = [
    "Rol",
    "UsuarioRol",
    "RolEnum",
    "RolRepository",
    "UsuarioRolRepository",
    "RolPublic",
    "UserRolAssign",
    "RolUnitOfWork",
    "get_uow",
]
