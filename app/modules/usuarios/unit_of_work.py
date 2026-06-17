from typing import Annotated
from fastapi import Depends
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.refresh_token.repository import RefreshTokenRepository
from app.core.database import get_session


class UsuarioUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)


def get_uow(session: Annotated[Session, Depends(get_session)]) -> UsuarioUnitOfWork:
    return UsuarioUnitOfWork(session)