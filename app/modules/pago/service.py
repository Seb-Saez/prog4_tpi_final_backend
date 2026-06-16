import logging
from decimal import Decimal

import mercadopago
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.websocket import broadcast_estado_cambiado
from app.modules.pago.model import Pago
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

    async def procesar_webhook(self, data: dict) -> None:
        try:
            await self._procesar_webhook_interno(data)
        except Exception as e:
            logger.error("Error inesperado en procesar_webhook: %s", e, exc_info=True)

    async def _procesar_webhook_interno(self, data: dict) -> None:
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

        # Clave de idempotencia: usa el header si viene, sino el payment_id
        idempotency_key = (
            data.get("idempotency_key")
            or data.get("x-idempotency-key")
            or str(payment_id)
        )

        estado_anterior: str | None = None
        should_advance = False

        with PedidoUnitOfWork(self._session) as uow:
            # Control de idempotencia — evitar reprocesar el mismo pago
            pago_existente = uow.pagos.get_by_idempotency_key(idempotency_key)
            if pago_existente is not None:
                logger.info(
                    "Webhook idempotente: pago %s ya procesado (id=%s)",
                    idempotency_key,
                    pago_existente.id,
                )
                return

            pedido = uow.pedidos.get_full(pedido_id)
            if pedido is None:
                logger.warning("Webhook: pedido %s no encontrado", pedido_id)
                return

            # Registrar fila de pago
            raw_amount = payment_data.get("transaction_amount")
            pago = Pago(
                pedido_id=pedido_id,
                mp_payment_id=str(payment_id),
                mp_status=status_mp,
                mp_status_detail=payment_data.get("status_detail"),
                transaction_amount=(
                    Decimal(str(raw_amount)) if raw_amount is not None else None
                ),
                payment_method_id=payment_data.get("payment_method_id"),
                idempotency_key=idempotency_key,
                external_reference=external_ref,
            )
            uow.pagos.add(pago)

            # Actualizar campos MP en el pedido
            pedido.mp_payment_id = str(payment_id)
            pedido.mp_payment_status = status_mp
            uow.pedidos.update(pedido)

            # Capturar estado antes de salir del UoW para el broadcast posterior
            estado_anterior = pedido.estado_pedido_codigo
            should_advance = (
                status_mp == "approved"
                and pedido.estado_pedido.orden == 1
            )
        # El UoW ya commitió aquí — pago y campos MP persisten

        # Avanzar el estado del pedido fuera del UoW de pago (evita contextos anidados)
        if should_advance:
            # Importación diferida para evitar ciclo circular en module-load
            from app.modules.pedido.service import PedidoService  # noqa: PLC0415

            try:
                pedido_avanzado = PedidoService(self._session).avanzar_estado_sistema(
                    pedido_id,
                    motivo="Pago aprobado (MercadoPago)",
                )
                await broadcast_estado_cambiado(
                    pedido_id=pedido_id,
                    estado_anterior=estado_anterior,
                    estado_nuevo=pedido_avanzado.estado_pedido_codigo,
                    motivo="Pago aprobado (MercadoPago)",
                )
            except Exception as e:
                logger.error(
                    "Error al avanzar estado del pedido %s tras pago aprobado: %s",
                    pedido_id,
                    e,
                    exc_info=True,
                )

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
