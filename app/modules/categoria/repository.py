from sqlmodel import Session
from app.core.repository import BaseRepository
from app.modules.categoria.model import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)