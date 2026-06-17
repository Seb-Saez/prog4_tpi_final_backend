from typing import Optional, Sequence

from sqlmodel import Session, col, select

from app.core.repository import BaseRepository
from app.modules.ingrediente.model import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def list_filtrado(
        self,
        skip: int = 0,
        limit: int = 20,
        es_alergeno: Optional[bool] = None,
    ) -> Sequence[Ingrediente]:
        """Listado con filtro, orden estable por id y paginación en la query."""
        stmt = select(Ingrediente).where(col(Ingrediente.deleted_at).is_(None))
        if es_alergeno is not None:
            stmt = stmt.where(Ingrediente.es_alergeno == es_alergeno)
        stmt = stmt.order_by(col(Ingrediente.id)).offset(skip).limit(limit)
        return self.session.exec(stmt).all()
