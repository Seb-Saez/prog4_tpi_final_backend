from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlmodel import Field, Relationship

from app.core.base_model import BaseEntity

if TYPE_CHECKING:
    from app.modules.pedido.model import Pedido


class Pago(BaseEntity, table=True):
    __tablename__ = "pago"  # type: ignore[assignment]

    pedido_id: int = Field(foreign_key="pedido.id", index=True)

    mp_payment_id: Optional[str] = None
    mp_status: Optional[str] = None
    mp_status_detail: Optional[str] = None
    transaction_amount: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    payment_method_id: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, index=True)
    external_reference: Optional[str] = None

    pedido: "Pedido" = Relationship()
