from typing import Sequence

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.core.repository import BaseRepository
from app.modules.pedido.model import Pedido


class PedidoRepository(BaseRepository[Pedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    def get_full(self, pedido_id: int) -> Pedido | None:
        """Pedido + detalles + estado + historial cargados eagerly."""
        stmt = (
            select(Pedido)
            .where(col(Pedido.id) == pedido_id)
            .where(col(Pedido.deleted_at).is_(None))
            .options(
                selectinload(Pedido.detalles),  # type: ignore[arg-type]
                selectinload(Pedido.estado_pedido),  # type: ignore[arg-type]
                selectinload(Pedido.historial_estado_pedido),  # type: ignore[arg-type]
            )
        )
        return self.session.exec(stmt).first()

    def list_by_usuario(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[Pedido]:
        stmt = (
            select(Pedido)
            .where(col(Pedido.usuario_id) == usuario_id)
            .where(col(Pedido.deleted_at).is_(None))
            .order_by(col(Pedido.created_at).desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Pedido.estado_pedido))  # type: ignore[arg-type]
        )
        return self.session.exec(stmt).all()

    def list_all(
        self,
        offset: int = 0,
        limit: int = 20,
        estado_codigo: str | None = None,
    ) -> Sequence[Pedido]:
        stmt = (
            select(Pedido)
            .where(col(Pedido.deleted_at).is_(None))
            .order_by(col(Pedido.created_at).desc())
            .options(selectinload(Pedido.estado_pedido))  # type: ignore[arg-type]
        )
        if estado_codigo:
            stmt = stmt.where(col(Pedido.estado_pedido_codigo) == estado_codigo)
        stmt = stmt.offset(offset).limit(limit)
        return self.session.exec(stmt).all()
