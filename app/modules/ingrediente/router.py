from typing import Annotated, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Path, Query
from sqlmodel import Session
from app.modules.rol.enums import RolEnum

from app.core.database import get_session
from app.core.deps import require_role
from app.core.websocket import broadcast_stock_ingrediente
from .schema import AjustarStockRequest, IngredienteCreate, IngredienteResponse, IngredienteUpdate
from .service import (
    ajustar_stock_ingrediente,
    create_ingrediente,
    delete_ingrediente,
    list_ingredientes,
    update_ingrediente,
    get_ingrediente_by_id,
)

router_ingrediente = APIRouter(prefix="/api/v1/ingredientes", tags=["ingredientes"])


@router_ingrediente.post(
    "/",
    response_model=IngredienteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def create(ingrediente: IngredienteCreate, session: Session = Depends(get_session)):
    return create_ingrediente(session, ingrediente)


@router_ingrediente.get(
    "/",
    response_model=list[IngredienteResponse],
)
def list_all(
    session: Session = Depends(get_session),
    skip: Annotated[int, Query(ge=0, description="Número de registros a omitir")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Límite de registros a retornar")
    ] = 20,
    es_alergeno: Annotated[
        Optional[bool], Query(description="Filtrar por alérgenos")
    ] = None,
):
    return list_ingredientes(session, skip=skip, limit=limit, es_alergeno=es_alergeno)


@router_ingrediente.get(
    "/{ingrediente_id}",
    response_model=IngredienteResponse,
)
def get_by_id(
    ingrediente_id: Annotated[int, Path(ge=1, description="ID del ingrediente")],
    session: Session = Depends(get_session),
):
    try:
        return get_ingrediente_by_id(session, ingrediente_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_ingrediente.patch(
    "/{ingrediente_id}",
    response_model=IngredienteResponse,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def update(
    ingrediente_id: Annotated[int, Path(ge=1, description="ID del ingrediente")],
    ingrediente: IngredienteUpdate,
    session: Session = Depends(get_session),
):
    try:
        return update_ingrediente(session, ingrediente_id, ingrediente)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_ingrediente.patch(
    "/{ingrediente_id}/stock",
    response_model=IngredienteResponse,
    dependencies=[Depends(require_role([RolEnum.ADMIN, RolEnum.CAJA]))],
)
def ajustar_stock(
    ingrediente_id: Annotated[int, Path(ge=1, description="ID del ingrediente")],
    body: AjustarStockRequest,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Ajusta el stock de un ingrediente.

    stock_cantidad == 0 → marcar faltante (deshabilita productos afectados).
    stock_cantidad > 0  → reponer stock (reactiva productos cuando corresponde).

    Emite el evento WebSocket ``stock_ingrediente`` post-commit.
    """
    ingrediente = ajustar_stock_ingrediente(session, ingrediente_id, body)

    background_tasks.add_task(
        broadcast_stock_ingrediente,
        ingrediente_id=ingrediente.id,
        nombre=ingrediente.nombre,
        stock_cantidad=ingrediente.stock_cantidad,
    )

    return ingrediente


@router_ingrediente.delete(
    "/{ingrediente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def delete(
    ingrediente_id: Annotated[int, Path(ge=1, description="ID del ingrediente")],
    session: Session = Depends(get_session),
):
    try:
        delete_ingrediente(session, ingrediente_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
