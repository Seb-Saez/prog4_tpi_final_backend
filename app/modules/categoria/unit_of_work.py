from sqlmodel import Session
from app.core.unit_of_work import UnitOfWork
from app.modules.categoria.repository import CategoriaRepository
from app.modules.producto.repository import ProductoRepository


class CategoriaUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.categorias = CategoriaRepository(session)
        self.productos = ProductoRepository(session)