from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.usuarios.schema import UserPublic
from app.modules.direccion.schema import DireccionCreate, DireccionResponse, DireccionUpdate
from app.modules.direccion.service import create_direccion, list_direcciones, get_direccion, update_direccion, delete_direccion


router_direccion = APIRouter(prefix="/api/v1/direcciones", tags=["direcciones"])


@router_direccion.get("/", response_model=list[DireccionResponse])
def list_all(
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return list_direcciones(session, current_user.id, skip=skip, limit=limit)


@router_direccion.get("/{direccion_id}", response_model=DireccionResponse)
def get_by_id(
    direccion_id: Annotated[int, Path(ge=1)],
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    return get_direccion(session, direccion_id, current_user.id)


@router_direccion.post("/", response_model=DireccionResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: DireccionCreate,
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    return create_direccion(session, current_user.id, data)


@router_direccion.patch("/{direccion_id}", response_model=DireccionResponse)
def update(
    direccion_id: Annotated[int, Path(ge=1)],
    data: DireccionUpdate,
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    return update_direccion(session, direccion_id, current_user.id, data)


@router_direccion.delete("/{direccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    direccion_id: Annotated[int, Path(ge=1)],
    current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    return delete_direccion(session, direccion_id, current_user.id)