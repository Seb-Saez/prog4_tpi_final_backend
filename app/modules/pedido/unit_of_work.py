from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.detalle_pedido.repository import DetallePedidoRepository
from app.modules.estado_pedido.repository import EstadoPedidoRepository
from app.modules.forma_pago.repository import FormaPagoRepository
from app.modules.historial_pedido.repository import HistorialEstadoPedidoRepository
from app.modules.pago.repository import PagoRepository
from app.modules.pedido.repository import PedidoRepository
from app.modules.producto.repository import ProductoRepository


class PedidoUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos = PedidoRepository(session)
        self.detalles = DetallePedidoRepository(session)
        self.historiales = HistorialEstadoPedidoRepository(session)
        self.estados = EstadoPedidoRepository(session)
        self.formas_pago = FormaPagoRepository(session)
        self.productos = ProductoRepository(session)
        self.pagos = PagoRepository(session)
