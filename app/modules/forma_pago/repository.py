from typing import Sequence

from sqlmodel import Session, col, select

from app.core.repository import BaseRepository
from app.modules.forma_pago.model import FormaPago


class FormaPagoRepository(BaseRepository[FormaPago]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, FormaPago)

    def list_habilitadas(self) -> Sequence[FormaPago]:
        stmt = (
            select(FormaPago)
            .where(col(FormaPago.habilitado).is_(True))
            .where(col(FormaPago.deleted_at).is_(None))
        )
        return self.session.exec(stmt).all()

    def get_habilitada_by_id(self, forma_pago_id: int) -> FormaPago | None:
        forma = self.get_by_id(forma_pago_id)
        if forma is None or not forma.habilitado:
            return None
        return forma
