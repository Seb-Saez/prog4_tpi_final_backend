from fastapi import HTTPException, status
from datetime import datetime
from app.modules.direccion.model import DireccionEntrega
from app.modules.direccion.schema import DireccionCreate, DireccionUpdate
from app.modules.direccion.unit_of_work import DireccionUnitOfWork

class DireccionService:
    def __init__(self, session):
        self._session = session

    def _get_or_404(self, uow, direccion_id: int, usuario_id: int) -> DireccionEntrega:
        direccion = uow.direcciones.get_by_id(direccion_id)
        if not direccion or direccion.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Dirección no encontrada")
        return direccion
    
    def create(self, usuario_id: int, data: DireccionCreate) -> DireccionEntrega:
        with DireccionUnitOfWork(self._session) as uow:
            if data.es_principal:
                self._quitar_principal(uow, usuario_id)
            direccion = DireccionEntrega.model_validate(data, update={"usuario_id": usuario_id})
            uow.direcciones.add(direccion)
            return direccion
        
    def list_by_usuario(self, usuario_id: int, skip: int = 0, limit: int = 20) -> list[DireccionEntrega]:
        with DireccionUnitOfWork(self._session) as uow:
            return uow.direcciones.get_by_usuario(usuario_id, offset=skip, limit=limit)
        
    def get_by_id(self, direccion_id: int, usuario_id: int) -> DireccionEntrega:
        with DireccionUnitOfWork(self._session) as uow:
            return self._get_or_404(uow, direccion_id, usuario_id)
        
    def update(self, direccion_id: int, usuario_id: int, data: DireccionUpdate) -> DireccionEntrega:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id, usuario_id)
            if data.es_principal:
                self._quitar_principal(uow, usuario_id)
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(direccion, field, value)
            direccion.updated_at = datetime.now()
            uow.direcciones.add(direccion)
            return direccion
        
    def delete(self, direccion_id: int, usuario_id: int) -> None:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id, usuario_id)
            uow.direcciones.delete(direccion)

    def set_principal(self, direccion_id: int, usuario_id: int) -> DireccionEntrega:
        with DireccionUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id, usuario_id)
            self._quitar_principal(uow, usuario_id)
            direccion.es_principal = True
            uow.direcciones.add(direccion)
            return direccion

    def _quitar_principal(self, uow, usuario_id: int) -> None:
        actual = uow.direcciones.get_principal(usuario_id)
        if actual:
            actual.es_principal = False
            uow.direcciones.add(actual)

def create_direccion(session, usuario_id: int, data: DireccionCreate) -> DireccionEntrega:
    return DireccionService(session).create(usuario_id, data)

def list_direcciones(session, usuario_id: int, skip: int = 0, limit: int = 20) -> list[DireccionEntrega]:
    return DireccionService(session).list_by_usuario(usuario_id, skip=skip, limit=limit)

def get_direccion(session, direccion_id: int, usuario_id: int) -> DireccionEntrega:
    return DireccionService(session).get_by_id(direccion_id, usuario_id)

def update_direccion(session, direccion_id: int, usuario_id: int, data: DireccionUpdate) -> DireccionEntrega:
    return DireccionService(session).update(direccion_id, usuario_id, data)

def delete_direccion(session, direccion_id: int, usuario_id: int) -> None:
    return DireccionService(session).delete(direccion_id, usuario_id)

def set_principal_direccion(session, direccion_id: int, usuario_id: int) -> DireccionEntrega:
    return DireccionService(session).set_principal(direccion_id, usuario_id)