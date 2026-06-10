from typing import Sequence

from sqlmodel import Session, col, select

from app.modules.estado_pedido.model import EstadoPedido


class EstadoPedidoRepository:
    """Repositorio plano — EstadoPedido tiene PK string (codigo), no hereda de BaseEntity."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_codigo(self, codigo: str) -> EstadoPedido | None:
        return self.session.get(EstadoPedido, codigo)

    def get_inicial(self) -> EstadoPedido | None:
        """Estado con orden=1 — punto de entrada del flujo."""
        stmt = select(EstadoPedido).where(col(EstadoPedido.orden) == 1)
        return self.session.exec(stmt).first()

    def get_siguiente(
        self,
        orden_actual: int,
        codigos_excluidos: list[str] | None = None,
    ) -> EstadoPedido | None:
        """Próximo estado por orden ascendente, opcionalmente saltando códigos.

        Útil para flujos condicionales (ej: en RETIRO_LOCAL se salta ENVIADO).
        """
        stmt = (
            select(EstadoPedido)
            .where(col(EstadoPedido.orden) > orden_actual)
            .order_by(col(EstadoPedido.orden).asc())
        )
        if codigos_excluidos:
            stmt = stmt.where(~col(EstadoPedido.codigo).in_(codigos_excluidos))
        return self.session.exec(stmt).first()

    def list_all(self) -> Sequence[EstadoPedido]:
        stmt = select(EstadoPedido).order_by(col(EstadoPedido.orden).asc())
        return self.session.exec(stmt).all()
