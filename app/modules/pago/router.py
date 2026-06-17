from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.usuarios.schema import UserPublic

from .schema import PagoResponse, PreferenciaResponse
from .service import PagoService

router_pago = APIRouter(prefix="/api/v1/pagos", tags=["pagos"])


@router_pago.post(
    "/preferencia/{pedido_id}",
    response_model=PreferenciaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_preferencia(
    pedido_id: Annotated[int, Path(ge=1)],
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    """Crea una preferencia de pago en MercadoPago para el pedido."""
    return PagoService(session).crear_preferencia(pedido_id, usuario)


@router_pago.get(
    "/{pedido_id}",
    response_model=PagoResponse,
)
def obtener_pago(
    pedido_id: Annotated[int, Path(ge=1)],
    usuario: Annotated[UserPublic, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    """Consulta el pago asociado a un pedido. Dueño o admin/cocina."""
    return PagoService(session).get_pago_por_pedido(pedido_id, usuario)


@router_pago.post("/webhook")
async def webhook_mercadopago(
    request: Request,
    session: Session = Depends(get_session),
):
    """Webhook IPN de MercadoPago — sin autenticación.

    MercadoPago envía la notificación como query params (?topic=payment&id=...)
    o como JSON body ({"type": "payment", "data": {"id": "..."}}). Se contemplan
    ambos formatos: primero query params, y si vienen vacíos se lee el body.
    """
    data = dict(request.query_params)
    if not data:
        try:
            data = await request.json()
        except Exception:
            data = {}
    await PagoService(session).procesar_webhook(data)
    return {"status": "ok"}
