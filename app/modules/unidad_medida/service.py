from typing import Sequence

from fastapi import HTTPException, status

from app.modules.unidad_medida.model import UnidadMedida
from app.modules.unidad_medida.schema import UnidadMedidaCreate, UnidadMedidaUpdate
from app.modules.unidad_medida.unit_of_work import UnidadMedidaUnitOfWork


class UnidadMedidaService:
    def __init__(self, session):
        self._session = session

    def _get_or_404(self, uow, unidad_id: int) -> UnidadMedida:
        unidad = uow.unidades.get_by_id(unidad_id)
        if not unidad:
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        return unidad

    def create(self, data: UnidadMedidaCreate) -> UnidadMedida:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            unidad = UnidadMedida.model_validate(data)
            uow.unidades.add(unidad)
            return unidad

    def list_all(self, skip: int = 0, limit: int = 20) -> Sequence[UnidadMedida]:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            return uow.unidades.get_all(offset=skip, limit=limit)

    def get_by_id(self, unidad_id: int) -> UnidadMedida:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            return self._get_or_404(uow, unidad_id)

    def update(self, unidad_id: int, data: UnidadMedidaUpdate) -> UnidadMedida:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            unidad = self._get_or_404(uow, unidad_id)
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(unidad, field, value)
            uow.unidades.add(unidad)
            return unidad

    def delete(self, unidad_id: int) -> None:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            unidad = self._get_or_404(uow, unidad_id)
            uow.unidades.delete(unidad)


def create_unidad(session, data: UnidadMedidaCreate) -> UnidadMedida:
    return UnidadMedidaService(session).create(data)

def list_unidades(session, skip: int = 0, limit: int = 20) -> Sequence[UnidadMedida]:
    return UnidadMedidaService(session).list_all(skip=skip, limit=limit)

def get_unidad(session, unidad_id: int) -> UnidadMedida:
    return UnidadMedidaService(session).get_by_id(unidad_id)

def update_unidad(session, unidad_id: int, data: UnidadMedidaUpdate) -> UnidadMedida:
    return UnidadMedidaService(session).update(unidad_id, data)

def delete_unidad(session, unidad_id: int) -> None:
    return UnidadMedidaService(session).delete(unidad_id)
