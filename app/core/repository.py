from typing import Generic, TypeVar, Type, Sequence

from sqlmodel import Session, select, col

from app.core.base_model import BaseEntity  # ← renombrado, si lo aplicás
from app.core.datetime_utils import utcnow

ModelT = TypeVar("ModelT", bound=BaseEntity)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: Session, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get_by_id(self, record_id: int) -> ModelT | None:
        instance = self.session.get(self.model, record_id)
        if instance is None or instance.deleted_at is not None:
            return None
        return instance

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        # ORDER BY id: sin orden explícito Postgres no garantiza el orden de
        # retorno, y al ACTUALIZAR una fila esta "salta" de posición — con
        # paginación eso hace que registros editados desaparezcan de la página.
        stmt = (
            select(self.model)
            .where(col(self.model.deleted_at).is_(None))
            .order_by(col(self.model.id))
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(stmt).all()

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def update(self, instance: ModelT) -> ModelT:
        instance.updated_at = utcnow()
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        instance.deleted_at = utcnow()
        self.session.add(instance)
        self.session.flush()
