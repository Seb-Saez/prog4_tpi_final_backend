from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from .schema import CategoriaCreate, CategoriaResponse, CategoriaUpdate
from .service import create_categoria, delete_categoria, list_categorias, update_categoria, get_categoria_by_id
from app.modules.rol.enums import RolEnum

router_categoria = APIRouter(prefix="/api/v1/categorias", tags=["categorias"])


@router_categoria.post(
    "/",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def create(categoria: CategoriaCreate, session: Session = Depends(get_session)):
    return create_categoria(session, categoria)


@router_categoria.get(
    "/",
    response_model=list[CategoriaResponse],
    dependencies=[Depends(get_current_active_user)],
)
def list_all(
    session: Session = Depends(get_session),
    skip: Annotated[int, Query(ge=0, description="Número de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, descripción="Límite de registros a retornar")] = 20,
):
    return list_categorias(session, skip=skip, limit=limit)


@router_categoria.get(
    "/{categoria_id}",
    response_model=CategoriaResponse,
    dependencies=[Depends(get_current_active_user)],
)
def get_by_id(
    categoria_id: Annotated[int, Path(ge=1, description="ID de la categoría")],
    session: Session = Depends(get_session),
):
    try:
        return get_categoria_by_id(session, categoria_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_categoria.patch(
    "/{categoria_id}",
    response_model=CategoriaResponse,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def update(
    categoria_id: Annotated[int, Path(ge=1, description="ID de la categoría")],
    categoria: CategoriaUpdate,
    session: Session = Depends(get_session),
):
    try:
        return update_categoria(session, categoria_id, categoria)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_categoria.delete(
    "/{categoria_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def delete(
    categoria_id: Annotated[int, Path(ge=1, description="ID de la categoría")],
    session: Session = Depends(get_session),
):
    try:
        delete_categoria(session, categoria_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


