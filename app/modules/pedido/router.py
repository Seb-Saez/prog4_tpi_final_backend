from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.core.websocket import broadcast_estado_cambiado
from app.modules.rol.enums import RolEnum
from app.modules.usuarios.schema import UserPublic

from .schema import PedidoCreate, PedidoResponse, PedidoResumen
from .service import PedidoService


router_pedido = APIRouter(prefix="/api/v1/pedidos", tags=["pedidos"])


# ============================================================
# Cliente — crear / ver lo propio
# ============================================================

@router_pedido.post(
    "/",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido(
    data: PedidoCreate,
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Crea un pedido a partir del carrito del cliente logueado."""
    pedido = PedidoService(session).crear_desde_carrito(data, usuario)

    background_tasks.add_task(
        broadcast_estado_cambiado,
        pedido_id=pedido.id,
        estado_anterior=None,
        estado_nuevo=pedido.estado_pedido_codigo,
        usuario_id=usuario.id,
    )

    return pedido


@router_pedido.get(
    "/mios",
    response_model=list[PedidoResumen],
)
def listar_mis_pedidos(
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Lista los pedidos del usuario logueado, paginado."""
    return PedidoService(session).list_mis_pedidos(usuario, offset, limit)


# ============================================================
# Cliente o Admin/Cocina — detalle y cancelación
# ============================================================

@router_pedido.get(
    "/{pedido_id}",
    response_model=PedidoResponse,
)
def obtener_pedido(
    pedido_id: Annotated[int, Path(ge=1)],
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    """Detalle de un pedido. El cliente solo ve los suyos; admin/cocina ven cualquiera."""
    return PedidoService(session).get_pedido(pedido_id, usuario)


@router_pedido.patch(
    "/{pedido_id}/cancelar",
    response_model=PedidoResponse,
)
def cancelar_pedido(
    pedido_id: Annotated[int, Path(ge=1)],
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Cancela un pedido si el estado actual lo permite. Dueño o admin/cocina."""
    service = PedidoService(session)
    current = service.get_pedido(pedido_id, usuario)
    estado_anterior: str | None = current.estado_pedido.codigo

    pedido = service.cancelar(pedido_id, usuario)

    background_tasks.add_task(
        broadcast_estado_cambiado,
        pedido_id=pedido.id,
        estado_anterior=estado_anterior,
        estado_nuevo=pedido.estado_pedido_codigo,
        usuario_id=usuario.id,
    )

    return pedido


# ============================================================
# Admin / Cocina — listado total y avance de estado
# ============================================================

@router_pedido.get(
    "/",
    response_model=list[PedidoResumen],
    dependencies=[Depends(require_role([RolEnum.ADMIN, RolEnum.COCINA]))],
)
def listar_todos(
    session: Session = Depends(get_session),
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    estado_codigo: Annotated[
        Optional[str], Query(description="Filtrar por código de estado")
    ] = None,
):
    """Vista operativa — admin/cocina ven todos los pedidos con filtro opcional por estado."""
    return PedidoService(session).list_todos(offset, limit, estado_codigo)


@router_pedido.patch(
    "/{pedido_id}/avanzar",
    response_model=PedidoResponse,
)
def avanzar_estado(
    pedido_id: Annotated[int, Path(ge=1)],
    usuario: Annotated[
        UserPublic,
        Depends(require_role([RolEnum.ADMIN, RolEnum.COCINA])),
    ],
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Avanza el pedido al siguiente estado por orden ascendente."""
    service = PedidoService(session)
    current = service.get_pedido(pedido_id, usuario)
    estado_anterior: str | None = current.estado_pedido.codigo

    pedido = service.avanzar_estado(pedido_id, usuario)

    background_tasks.add_task(
        broadcast_estado_cambiado,
        pedido_id=pedido.id,
        estado_anterior=estado_anterior,
        estado_nuevo=pedido.estado_pedido_codigo,
        usuario_id=usuario.id,
    )

    return pedido
