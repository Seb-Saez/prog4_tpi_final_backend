from sqlmodel import Session
from app.core.repository import BaseRepository
from app.modules.unidad_medida.model import UnidadMedida


class UnidadMedidaRepository(BaseRepository[UnidadMedida]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UnidadMedida)
