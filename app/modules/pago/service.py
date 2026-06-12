import logging

import mercadopago
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.modules.pedido.model import Pedido
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.usuarios.schema import UserPublic

logger = logging.getLogger(__name__)


class PagoService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    def crear_preferencia(
        self,
        pedido_id: int,
        usuario: UserPublic,
    ) -> dict:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_full(pedido_id)
            if pedido is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado",
                )

            self._asegurar_propietario(pedido, usuario)

            if pedido.mp_preference_id is not None:
                return self._devolver_preferencia_existente(pedido)

            preference_data = self._armar_preferencia(pedido)

            result = self._sdk.preference().create(preference_data)

            if result["status"] not in (200, 201):
                logger.error(
                    "Error creando preferencia MP: %s", result["response"]
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Error al crear la preferencia de pago en MercadoPago",
                )

            response = result["response"]
            pedido.mp_preference_id = response["id"]
            uow.pedidos.update(pedido)

            return {
                "init_point": response["init_point"],
                "preference_id": response["id"],
            }

    def procesar_webhook(self, data: dict) -> None:
        topic = data.get("topic") or data.get("type")
        if topic not in ("payment", "merchant_order"):
            return

        payment_id = None
        if topic == "payment":
            payment_id = data.get("id") or data.get("data", {}).get("id")
        elif topic == "merchant_order":
            merchant_order_id = data.get("id") or data.get("data", {}).get("id")
            merchant_order = self._sdk.merchant_order().get(merchant_order_id)
            if merchant_order["status"] == 200:
                payments = merchant_order["response"].get("payments", [])
                if payments:
                    payment_id = payments[0].get("id")

        if payment_id is None:
            return

        payment = self._sdk.payment().get(int(payment_id))
        if payment["status"] != 200:
            logger.error("Error obteniendo payment %s: %s", payment_id, payment)
            return

        payment_data = payment["response"]
        external_ref = payment_data.get("external_reference")
        if external_ref is None:
            return

        pedido_id = int(external_ref)
        status_mp = payment_data.get("status")

        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_full(pedido_id)
            if pedido is None:
                logger.warning("Webhook: pedido %s no encontrado", pedido_id)
                return

            pedido.mp_payment_id = str(payment_id)
            pedido.mp_payment_status = status_mp
            uow.pedidos.update(pedido)

    @staticmethod
    def _asegurar_propietario(pedido: Pedido, usuario: UserPublic) -> None:
        if pedido.usuario_id != usuario.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El pedido no te pertenece",
            )

    @staticmethod
    def _devolver_preferencia_existente(pedido: Pedido) -> dict:
        result = mercadopago.SDK(settings.MP_ACCESS_TOKEN).preference().get(pedido.mp_preference_id)
        if result["status"] == 200:
            return {
                "init_point": result["response"]["init_point"],
                "preference_id": pedido.mp_preference_id,
            }
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al recuperar la preferencia existente",
        )

    def _armar_preferencia(self, pedido: Pedido) -> dict:
        items = []
        for detalle in pedido.detalles:
            items.append({
                "title": detalle.nombre_snap,
                "quantity": detalle.cantidad,
                "unit_price": float(detalle.precio_unit_snap),
                "currency_id": "ARS",
            })

        preference = {
            "items": items,
            "external_reference": str(pedido.id),
            "back_urls": {
                "success": f"{settings.MP_FRONTEND_URL}/pago/resultado?status=success&pedido_id={pedido.id}",
                "failure": f"{settings.MP_FRONTEND_URL}/pago/resultado?status=failure&pedido_id={pedido.id}",
                "pending": f"{settings.MP_FRONTEND_URL}/pago/resultado?status=pending&pedido_id={pedido.id}",
            },
            "auto_return": "approved",
        }

        if settings.MP_NOTIFICATION_URL:
            preference["notification_url"] = (
                f"{settings.MP_NOTIFICATION_URL}/api/v1/pagos/webhook"
            )

        return preference
