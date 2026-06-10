from fastapi import HTTPException
from sqlmodel import Session

from app.modules.categoria.model import Categoria
from app.modules.categoria.schema import CategoriaCreate, CategoriaUpdate, CategoriaResponse
from app.modules.categoria.unit_of_work import CategoriaUnitOfWork
from datetime import datetime


class CategoriaService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        categoria = uow.categorias.get_by_id(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria no encontrada")
        return categoria

    def create(self, data: CategoriaCreate) -> Categoria:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = Categoria.model_validate(data)
            uow.categorias.add(categoria)
            return categoria

    def list(self, skip: int = 0, limit: int = 20) -> list[Categoria]:
        with CategoriaUnitOfWork(self._session) as uow:
            return list(uow.categorias.get_all())[skip : skip + limit]

    def get_by_id(self, categoria_id: int) -> Categoria:
        with CategoriaUnitOfWork(self._session) as uow:
            return self._get_or_404(uow, categoria_id)

    def update(self, categoria_id: int, data: CategoriaUpdate) -> Categoria:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(categoria, field, value)

            categoria.updated_at = datetime.now()
            uow.categorias.add(categoria)
            return categoria

    def delete(self, categoria_id: int) -> bool:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            uow.categorias.delete(categoria)
            return True


def create_categoria(session: Session, data: CategoriaCreate) -> Categoria:
    service = CategoriaService(session)
    return service.create(data)


def list_categorias(session: Session, skip: int = 0, limit: int = 20) -> list[Categoria]:
    service = CategoriaService(session)
    return service.list(skip=skip, limit=limit)


def get_categoria_by_id(session: Session, categoria_id: int) -> Categoria:
    service = CategoriaService(session)
    return service.get_by_id(categoria_id)


def update_categoria(session: Session, categoria_id: int, data: CategoriaUpdate) -> Categoria:
    service = CategoriaService(session)
    return service.update(categoria_id, data)


def delete_categoria(session: Session, categoria_id: int) -> bool:
    service = CategoriaService(session)
    return service.delete(categoria_id)