from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session

from app.modules.ingrediente.model import Ingrediente
from app.modules.ingrediente.schema import (
    IngredienteCreate,
    IngredienteUpdate,
    IngredienteResponse,
)
from app.modules.ingrediente.unit_of_work import IngredienteUnitOfWork
from datetime import datetime


class IngredienteService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(
        self, uow: IngredienteUnitOfWork, ingrediente_id: int
    ) -> Ingrediente:
        ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
        if not ingrediente:
            raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
        return ingrediente

    def create(self, data: IngredienteCreate) -> Ingrediente:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = Ingrediente.model_validate(data)
            uow.ingredientes.add(ingrediente)
            return ingrediente

    def list(
        self, skip: int = 0, limit: int = 20, es_alergeno: Optional[bool] = None
    ) -> list[Ingrediente]:
        with IngredienteUnitOfWork(self._session) as uow:
            ingredientes = list(uow.ingredientes.get_all())
            if es_alergeno is not None:
                ingredientes = [i for i in ingredientes if i.es_alergeno == es_alergeno]
            return ingredientes[skip : skip + limit]

    def get_by_id(self, ingrediente_id: int) -> Ingrediente:
        with IngredienteUnitOfWork(self._session) as uow:
            return self._get_or_404(uow, ingrediente_id)

    def update(self, ingrediente_id: int, data: IngredienteUpdate) -> Ingrediente:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(ingrediente, field, value)

            ingrediente.updated_at = datetime.now()
            uow.ingredientes.add(ingrediente)
            return ingrediente

    def delete(self, ingrediente_id: int) -> bool:
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            uow.ingredientes.delete(ingrediente)
            return True


def create_ingrediente(session: Session, data: IngredienteCreate) -> Ingrediente:
    service = IngredienteService(session)
    return service.create(data)


def list_ingredientes(
    session: Session,
    skip: int = 0,
    limit: int = 20,
    es_alergeno: Optional[bool] = None,
) -> list[Ingrediente]:
    service = IngredienteService(session)
    return service.list(skip=skip, limit=limit, es_alergeno=es_alergeno)


def get_ingrediente_by_id(session: Session, ingrediente_id: int) -> Ingrediente:
    service = IngredienteService(session)
    return service.get_by_id(ingrediente_id)


def update_ingrediente(
    session: Session, ingrediente_id: int, data: IngredienteUpdate
) -> Ingrediente:
    service = IngredienteService(session)
    return service.update(ingrediente_id, data)


def delete_ingrediente(session: Session, ingrediente_id: int) -> bool:
    service = IngredienteService(session)
    return service.delete(ingrediente_id)
