from sqlmodel import Session, select,col
from app.core.repository import BaseRepository
from app.modules.direccion.model import DireccionEntrega

class DireccionRepository(BaseRepository[DireccionEntrega]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)

    def get_by_usuario(self, usuario_id: int, offset: int = 0, limit: int = 20) -> list[DireccionEntrega]:
        return list(self.session.exec(
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(col(DireccionEntrega.deleted_at).is_(None))
            .offset(offset).limit(limit)
        ).all())
    
    def get_principal(self, usuario_id: int) -> DireccionEntrega | None:
        return self.session.exec(
            select(DireccionEntrega)
            .where(DireccionEntrega.usuario_id == usuario_id)
            .where(DireccionEntrega.es_principal == True)
            .where(col(DireccionEntrega.deleted_at).is_(None))
        ).first()