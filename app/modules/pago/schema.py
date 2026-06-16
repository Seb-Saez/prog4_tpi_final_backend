from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import SQLModel


class PreferenciaResponse(SQLModel):
    init_point: str
    preference_id: str


class PagoResponse(SQLModel):
    """Vista del pago asociado a un pedido."""
    id: int
    pedido_id: int
    mp_payment_id: Optional[str]
    mp_status: Optional[str]
    mp_status_detail: Optional[str]
    transaction_amount: Optional[Decimal]
    payment_method_id: Optional[str]
    external_reference: Optional[str]
    idempotency_key: Optional[str]
    created_at: Optional[datetime]
