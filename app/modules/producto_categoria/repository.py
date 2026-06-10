from sqlmodel import Session, select
from app.core.repository_intermedias import BaseRepositoryIntermedias
from app.modules.producto_categoria.model import ProductoCategoria


class ProductoCategoriaRepository(BaseRepositoryIntermedias[ProductoCategoria]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ProductoCategoria)

    def get_by_producto(self, producto_id: int) -> list[ProductoCategoria]:
        return list(
            self.session.exec(
                select(ProductoCategoria).where(ProductoCategoria.producto_id == producto_id)
            ).all()
        )

    def get_by_categoria(self, categoria_id: int) -> list[ProductoCategoria]:
        return list(
            self.session.exec(
                select(ProductoCategoria).where(ProductoCategoria.categoria_id == categoria_id)
            ).all()
        )

    def get_principal_by_producto(self, producto_id: int) -> ProductoCategoria | None:
        return self.session.exec(
            select(ProductoCategoria)
            .where(ProductoCategoria.producto_id == producto_id)
            .where(ProductoCategoria.es_principal == True)
        ).first()
