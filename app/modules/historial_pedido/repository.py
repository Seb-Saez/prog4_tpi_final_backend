from typing import Sequence

from sqlmodel import Session, col, select

from app.core.repository import BaseRepository
from app.modules.historial_pedido.model import HistorialEstadoPedido


class HistorialEstadoPedidoRepository(BaseRepository[HistorialEstadoPedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, HistorialEstadoPedido)

    def list_by_pedido(self, pedido_id: int) -> Sequence[HistorialEstadoPedido]:
        stmt = (
            select(HistorialEstadoPedido)
            .where(col(HistorialEstadoPedido.pedido_id) == pedido_id)
            .order_by(col(HistorialEstadoPedido.fecha_cambio).asc())
        )
        return self.session.exec(stmt).all()
