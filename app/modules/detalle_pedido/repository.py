from typing import Sequence

from sqlmodel import Session, col, select

from app.modules.detalle_pedido.model import DetallePedido


class DetallePedidoRepository:
    """Repositorio plano — DetallePedido tiene PK compuesta, no hereda de BaseEntity."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance: DetallePedido) -> DetallePedido:
        self.session.add(instance)
        self.session.flush()
        return instance

    def add_many(self, instances: list[DetallePedido]) -> list[DetallePedido]:
        for det in instances:
            self.session.add(det)
        self.session.flush()
        return instances

    def list_by_pedido(self, pedido_id: int) -> Sequence[DetallePedido]:
        stmt = select(DetallePedido).where(
            col(DetallePedido.pedido_id) == pedido_id
        )
        return self.session.exec(stmt).all()
