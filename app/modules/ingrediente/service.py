from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session

from app.modules.ingrediente.model import Ingrediente
from app.modules.ingrediente.schema import (
    AjustarStockRequest,
    IngredienteCreate,
    IngredienteUpdate,
    IngredienteResponse,
)
from app.modules.ingrediente.unit_of_work import IngredienteUnitOfWork
from app.modules.ingrediente.utils import (
    obtener_productos_afectados_por_ingrediente,
    producto_tiene_todos_ingredientes_en_stock,
)
from app.core.datetime_utils import utcnow
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

    def ajustar_stock(self, ingrediente_id: int, data: AjustarStockRequest) -> Ingrediente:
        """Ajusta el stock del ingrediente y actualiza la disponibilidad de
        los productos afectados dentro del mismo UoW.

        - Si stock_cantidad == 0 (faltante): pone disponible=False en los
          productos que usan este ingrediente como no-removible y cuya
          categoría requiere_ingredientes=True.
        - Si stock_cantidad > 0 (reposición): reactiva (disponible=True)
          los productos afectados que ya NO tienen otro ingrediente
          no-removible con stock == 0.
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ingrediente = self._get_or_404(uow, ingrediente_id)
            ingrediente.stock_cantidad = data.stock_cantidad
            ingrediente.updated_at = utcnow()
            uow.ingredientes.add(ingrediente)

            # Actualizar disponibilidad de productos afectados
            productos_afectados = obtener_productos_afectados_por_ingrediente(
                uow.session, ingrediente_id
            )

            for producto in productos_afectados:
                if data.stock_cantidad == 0:
                    # Marcar faltante → deshabilitar producto y registrar causa
                    if producto.disponible:
                        producto.disponible = False
                        producto.deshabilitado_por_stock = True
                        producto.updated_at = utcnow()
                        uow.session.add(producto)
                else:
                    # Reposición → reactivar solo si fue auto-deshabilitado por stock
                    # y ya no tiene otros ingredientes faltantes
                    if not producto.disponible and producto.deshabilitado_por_stock:
                        if producto_tiene_todos_ingredientes_en_stock(uow.session, producto.id):
                            producto.disponible = True
                            producto.deshabilitado_por_stock = False
                            producto.updated_at = utcnow()
                            uow.session.add(producto)

            return ingrediente


def ajustar_stock_ingrediente(
    session: Session, ingrediente_id: int, data: AjustarStockRequest
) -> Ingrediente:
    service = IngredienteService(session)
    return service.ajustar_stock(ingrediente_id, data)


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
