from typing import Annotated, Self

from fastapi import Depends
from sqlmodel import Session

from app.core.database import get_session


class UnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.session = session    # ← guardás como _session (PRIVADO)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

