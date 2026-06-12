from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.usuarios.schema import UserPublic

from .schema import PreferenciaResponse
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


@router_pago.post("/webhook")
def webhook_mercadopago(
    request: Request,
    session: Session = Depends(get_session),
):
    """Webhook IPN de MercadoPago — sin autenticación."""
    data = dict(request.query_params)
    if not data:
        data = request.state.body if hasattr(request, "state") else {}
    PagoService(session).procesar_webhook(data)
    return {"status": "ok"}
