from typing import Annotated
from fastapi import Depends
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.rol.repository import RolRepository, UsuarioRolRepository
from app.core.database import get_session


class RolUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.roles = RolRepository(session)
        self.usuarios_roles = UsuarioRolRepository(session)


def get_uow(session: Annotated[Session, Depends(get_session)]) -> RolUnitOfWork:
    return RolUnitOfWork(session)
