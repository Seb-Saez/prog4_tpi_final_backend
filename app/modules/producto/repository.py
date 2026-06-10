from sqlmodel import Session, select,col
from sqlalchemy.orm import selectinload
from app.core.repository import BaseRepository
from app.modules.producto.model import Producto
from app.modules.producto_ingrediente.model import ProductoIngrediente


class ProductoRepository(BaseRepository[Producto]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    def get_all_ingredientes(self) -> list[Producto]:
        stmt = (
            select(Producto)
            .where(col(Producto.deleted_at).is_(None))
            .options(selectinload(Producto.producto_ingredientes))  # type: ignore[arg-type]
        )
        return list(self.session.exec(stmt).all())

    def get_by_id_ingredientes(self, id: int) -> Producto | None:
        stmt = (
            select(Producto)
            .where(col(Producto.id) == id)
            .options(selectinload(Producto.producto_ingredientes)) # type: ignore[arg-type]
        )
        return self.session.exec(stmt).first()
