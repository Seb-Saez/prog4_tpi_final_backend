from sqlmodel import Session, col, select

from app.core.repository import BaseRepository
from app.modules.pago.model import Pago


class PagoRepository(BaseRepository[Pago]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pago)

    def get_by_idempotency_key(self, key: str) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.idempotency_key == key)
        ).first()

    def get_latest_by_pedido(self, pedido_id: int) -> Pago | None:
        """Último pago registrado para un pedido (el más reciente)."""
        return self.session.exec(
            select(Pago)
            .where(Pago.pedido_id == pedido_id)
            .order_by(col(Pago.created_at).desc(), col(Pago.id).desc())
        ).first()

    def get_by_mp_payment_id(self, mp_payment_id: str) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.mp_payment_id == mp_payment_id)
        ).first()
