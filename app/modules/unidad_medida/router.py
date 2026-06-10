from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.unidad_medida.schema import UnidadMedidaCreate, UnidadMedidaResponse, UnidadMedidaUpdate
from app.modules.unidad_medida.service import create_unidad, list_unidades, get_unidad, update_unidad, delete_unidad

router_unidad_medida = APIRouter(prefix="/api/v1/unidades-medida", tags=["unidades-medida"])


@router_unidad_medida.get("/", response_model=list[UnidadMedidaResponse])
def list_all(
    session: Session = Depends(get_session),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return list_unidades(session, skip=skip, limit=limit)


@router_unidad_medida.get("/{unidad_id}", response_model=UnidadMedidaResponse)
def get_by_id(
    unidad_id: Annotated[int, Path(ge=1)],
    session: Session = Depends(get_session),
):
    return get_unidad(session, unidad_id)


@router_unidad_medida.post("/", response_model=UnidadMedidaResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: UnidadMedidaCreate,
    session: Session = Depends(get_session),
):
    return create_unidad(session, data)


@router_unidad_medida.patch("/{unidad_id}", response_model=UnidadMedidaResponse)
def update(
    unidad_id: Annotated[int, Path(ge=1)],
    data: UnidadMedidaUpdate,
    session: Session = Depends(get_session),
):
    return update_unidad(session, unidad_id, data)


@router_unidad_medida.delete("/{unidad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    unidad_id: Annotated[int, Path(ge=1)],
    session: Session = Depends(get_session),
):
    return delete_unidad(session, unidad_id)
