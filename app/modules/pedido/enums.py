from enum import StrEnum


class ModalidadEntrega(StrEnum):
    """Cómo recibe el cliente el pedido."""

    DELIVERY = "DELIVERY"
    RETIRO_LOCAL = "RETIRO_LOCAL"
