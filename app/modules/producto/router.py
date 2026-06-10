from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlmodel import Session
from app.modules.rol.enums import RolEnum
from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role

from .schema import ProductoCreate, ProductoResponse, ProductoUpdate
from .service import (
    create_producto,
    delete_producto,
    list_productos,
    update_producto,
    get_producto_by_id,
)

router_producto = APIRouter(prefix="/api/v1/productos", tags=["productos"])


@router_producto.post(
    "/",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def create(producto: ProductoCreate, session: Session = Depends(get_session)):
    return create_producto(session, producto)


@router_producto.get(
    "/",
    response_model=list[ProductoResponse],
    dependencies=[Depends(get_current_active_user)],
)
def list_all(
    session: Session = Depends(get_session),
    skip: Annotated[int, Query(ge=0, description="Número de registros a omitir")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Límite de registros a retornar")
    ] = 20,
    disponible: Annotated[
        Optional[bool], Query(description="Filtrar por disponibilidad")
    ] = None,
):
    return list_productos(session, skip=skip, limit=limit, disponible=disponible)


@router_producto.get(
    "/{producto_id}",
    response_model=ProductoResponse,
    dependencies=[Depends(get_current_active_user)],
)
def get_by_id(
    producto_id: Annotated[int, Path(ge=1, description="ID del producto")],
    session: Session = Depends(get_session),
):
    try:
        return get_producto_by_id(session, producto_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_producto.patch(
    "/{producto_id}",
    response_model=ProductoResponse,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def update(
    producto_id: Annotated[int, Path(ge=1, description="ID del producto")],
    producto: ProductoUpdate,
    session: Session = Depends(get_session),
):
    try:
        return update_producto(session, producto_id, producto)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_producto.delete(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role([RolEnum.ADMIN]))],
)
def delete(
    producto_id: Annotated[int, Path(ge=1, description="ID del producto")],
    session: Session = Depends(get_session),
):
    try:
        delete_producto(session, producto_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
