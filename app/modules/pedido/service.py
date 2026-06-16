from decimal import Decimal
from typing import Sequence

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.detalle_pedido.model import DetallePedido
from app.modules.direccion.model import DireccionEntrega
from app.modules.estado_pedido.model import EstadoPedido
from app.modules.forma_pago.model import FormaPago
from app.modules.historial_pedido.model import HistorialEstadoPedido
from app.modules.pedido.enums import ModalidadEntrega
from app.modules.pedido.model import Pedido
from app.modules.pedido.schema import PedidoCreate
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.rol.enums import RolEnum
from app.modules.usuarios.schema import UserPublic


COSTO_ENVIO_DELIVERY = Decimal("0.00")
COSTO_ENVIO_RETIRO = Decimal("0.00")
CODIGO_ESTADO_CANCELADO = "CANCELADO"

# Estados que NO aplican según la modalidad de entrega.
# El service los pasa como `codigos_excluidos` al repo cuando avanza.
ESTADOS_A_SALTAR_POR_MODALIDAD: dict[ModalidadEntrega, list[str]] = {
    ModalidadEntrega.DELIVERY: ["LISTO_PARA_RETIRAR"],
    ModalidadEntrega.RETIRO_LOCAL: ["ENVIADO"],
}


class PedidoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ============================================================
    # Acciones públicas
    # ============================================================

    def crear_desde_carrito(self, data: PedidoCreate, usuario: UserPublic) -> Pedido:
        with PedidoUnitOfWork(self._session) as uow:
            estado_inicial = self._estado_inicial(uow)
            forma_pago = self._forma_pago_habilitada(uow, data.forma_pago_id)

            direccion = self._direccion_segun_modalidad(
                uow, data.modalidad_entrega, data.direccion_id, usuario.id
            )

            detalles, subtotal = self._construir_detalles(uow, data)

            costo_envio = self._costo_envio(data.modalidad_entrega)
            total = subtotal + costo_envio

            pedido = Pedido(
                usuario_id=usuario.id,
                direccion_id=direccion.id if direccion else None,
                forma_pago_id=forma_pago.id,
                modalidad_entrega=data.modalidad_entrega,
                estado_pedido_codigo=estado_inicial.codigo,
                subtotal=subtotal,
                total=total,
                costo_envio=costo_envio,
                notas=data.notas,
                forma_pago_snap=forma_pago.descripcion,
                direccion_snap=self._snapshot_direccion(direccion) if direccion else None,
            )
            uow.pedidos.add(pedido)

            for det in detalles:
                det.pedido_id = pedido.id
            uow.detalles.add_many(detalles)

            uow.historiales.add(
                HistorialEstadoPedido(
                    usuario_id=usuario.id,
                    pedido_id=pedido.id,
                    estado_anterior=None,
                    estado_nuevo=estado_inicial.codigo,
                )
            )

            pedido_completo = uow.pedidos.get_full(pedido.id)
            assert pedido_completo is not None
            return pedido_completo

    def avanzar_estado(
        self,
        pedido_id: int,
        usuario: UserPublic,
        nuevo_estado: str | None = None,
        motivo: str | None = None,
    ) -> Pedido:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            estado_actual = pedido.estado_pedido

            if estado_actual.es_terminal:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El pedido ya está en un estado terminal",
                )

            excluidos = ESTADOS_A_SALTAR_POR_MODALIDAD.get(
                pedido.modalidad_entrega, []
            )
            estado_siguiente = uow.estados.get_siguiente(
                estado_actual.orden, codigos_excluidos=excluidos
            )
            if estado_siguiente is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No hay estado siguiente configurado para esta modalidad",
                )

            # Valida que el estado solicitado coincida con el siguiente esperado
            if nuevo_estado is not None and nuevo_estado != estado_siguiente.codigo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"El estado solicitado '{nuevo_estado}' no coincide con "
                        f"el siguiente estado esperado '{estado_siguiente.codigo}'"
                    ),
                )

            pedido.estado_pedido_codigo = estado_siguiente.codigo
            uow.pedidos.update(pedido)

            uow.historiales.add(
                HistorialEstadoPedido(
                    usuario_id=usuario.id,
                    pedido_id=pedido.id,
                    estado_anterior=estado_actual.codigo,
                    estado_nuevo=estado_siguiente.codigo,
                    motivo=motivo,
                )
            )

            pedido_completo = uow.pedidos.get_full(pedido.id)
            assert pedido_completo is not None
            return pedido_completo

    def avanzar_estado_sistema(
        self,
        pedido_id: int,
        motivo: str | None = None,
    ) -> Pedido:
        """Avanza el estado usando el usuario_id del propio pedido como actor.

        Diseñado para disparadores del sistema (webhooks, crons) donde no hay
        un usuario autenticado. Reutiliza la lógica de avanzar_estado.
        """
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            estado_actual = pedido.estado_pedido

            if estado_actual.es_terminal:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El pedido ya está en un estado terminal",
                )

            excluidos = ESTADOS_A_SALTAR_POR_MODALIDAD.get(
                pedido.modalidad_entrega, []
            )
            estado_siguiente = uow.estados.get_siguiente(
                estado_actual.orden, codigos_excluidos=excluidos
            )
            if estado_siguiente is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No hay estado siguiente configurado para esta modalidad",
                )

            pedido.estado_pedido_codigo = estado_siguiente.codigo
            uow.pedidos.update(pedido)

            uow.historiales.add(
                HistorialEstadoPedido(
                    usuario_id=pedido.usuario_id,
                    pedido_id=pedido.id,
                    estado_anterior=estado_actual.codigo,
                    estado_nuevo=estado_siguiente.codigo,
                    motivo=motivo,
                )
            )

            pedido_completo = uow.pedidos.get_full(pedido.id)
            assert pedido_completo is not None
            return pedido_completo

    def cancelar(self, pedido_id: int, usuario: UserPublic) -> Pedido:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            self._asegurar_acceso(pedido, usuario)

            estado_actual = pedido.estado_pedido
            if not estado_actual.permite_cancelar:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El pedido en estado '{estado_actual.codigo}' no se puede cancelar",
                )

            estado_cancelado = uow.estados.get_by_codigo(CODIGO_ESTADO_CANCELADO)
            if estado_cancelado is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"No hay estado de cancelación configurado (codigo='{CODIGO_ESTADO_CANCELADO}')",
                )

            pedido.estado_pedido_codigo = estado_cancelado.codigo
            uow.pedidos.update(pedido)

            uow.historiales.add(
                HistorialEstadoPedido(
                    usuario_id=usuario.id,
                    pedido_id=pedido.id,
                    estado_anterior=estado_actual.codigo,
                    estado_nuevo=estado_cancelado.codigo,
                )
            )

            pedido_completo = uow.pedidos.get_full(pedido.id)
            assert pedido_completo is not None
            return pedido_completo

    def get_pedido(self, pedido_id: int, usuario: UserPublic) -> Pedido:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            self._asegurar_acceso(pedido, usuario)
            return pedido

    def list_mis_pedidos(
        self, usuario: UserPublic, offset: int = 0, limit: int = 20
    ) -> Sequence[Pedido]:
        with PedidoUnitOfWork(self._session) as uow:
            return uow.pedidos.list_by_usuario(usuario.id, offset, limit)

    def list_todos(
        self,
        offset: int = 0,
        limit: int = 20,
        estado_codigo: str | None = None,
    ) -> Sequence[Pedido]:
        """Vista admin/cocina — el control de rol se hace en el router."""
        with PedidoUnitOfWork(self._session) as uow:
            return uow.pedidos.list_all(offset, limit, estado_codigo)

    # ============================================================
    # Helpers privados
    # ============================================================

    def _get_or_404(self, uow: PedidoUnitOfWork, pedido_id: int) -> Pedido:
        pedido = uow.pedidos.get_full(pedido_id)
        if pedido is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        return pedido

    def _asegurar_acceso(self, pedido: Pedido, usuario: UserPublic) -> None:
        if pedido.usuario_id == usuario.id:
            return
        allowed_roles = {RolEnum.ADMIN, RolEnum.PEDIDOS}
        if set(usuario.roles) & allowed_roles:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés acceso a este pedido",
        )

    def _estado_inicial(self, uow: PedidoUnitOfWork) -> EstadoPedido:
        estado = uow.estados.get_inicial()
        if estado is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No hay estado inicial configurado (orden=1)",
            )
        return estado

    def _direccion_segun_modalidad(
        self,
        uow: PedidoUnitOfWork,
        modalidad: ModalidadEntrega,
        direccion_id: int | None,
        usuario_id: int,
    ) -> DireccionEntrega | None:
        if modalidad == ModalidadEntrega.RETIRO_LOCAL:
            return None
        if direccion_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="direccion_id es obligatorio para delivery",
            )
        return self._direccion_del_usuario(uow, direccion_id, usuario_id)

    def _direccion_del_usuario(
        self, uow: PedidoUnitOfWork, direccion_id: int, usuario_id: int
    ) -> DireccionEntrega:
        direccion = uow.session.get(DireccionEntrega, direccion_id)
        if direccion is None or direccion.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dirección no encontrada",
            )
        if direccion.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La dirección no te pertenece",
            )
        return direccion

    def _forma_pago_habilitada(
        self, uow: PedidoUnitOfWork, forma_pago_id: int
    ) -> FormaPago:
        forma = uow.formas_pago.get_habilitada_by_id(forma_pago_id)
        if forma is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Forma de pago inexistente o deshabilitada",
            )
        return forma

    def _costo_envio(self, modalidad: ModalidadEntrega) -> Decimal:
        if modalidad == ModalidadEntrega.RETIRO_LOCAL:
            return COSTO_ENVIO_RETIRO
        return COSTO_ENVIO_DELIVERY

    def _construir_detalles(
        self, uow: PedidoUnitOfWork, data: PedidoCreate
    ) -> tuple[list[DetallePedido], Decimal]:
        productos_ids = [item.producto_id for item in data.items]
        if len(productos_ids) != len(set(productos_ids)):
            duplicados = sorted(
                {pid for pid in productos_ids if productos_ids.count(pid) > 1}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El carrito tiene productos duplicados: {duplicados}. "
                    "Mergeá las cantidades en un solo item antes de enviar."
                ),
            )

        detalles: list[DetallePedido] = []
        subtotal = Decimal("0.00")

        for item in data.items:
            producto = uow.productos.get_by_id(item.producto_id)
            if producto is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto {item.producto_id} no encontrado",
                )
            if not producto.disponible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Producto '{producto.nombre}' no está disponible",
                )

            precio_snap = Decimal(str(producto.precio_base))
            subtotal_linea = precio_snap * item.cantidad

            detalles.append(
                DetallePedido(
                    producto_id=producto.id,
                    cantidad=item.cantidad,
                    nombre_snap=producto.nombre,
                    precio_unit_snap=precio_snap,
                    subtotal_snap=subtotal_linea,
                    personalizacion=item.personalizacion,
                )
            )
            subtotal += subtotal_linea

        return detalles, subtotal

    def _snapshot_direccion(self, direccion: DireccionEntrega) -> str:
        partes = [direccion.linea1]
        if direccion.linea2:
            partes.append(direccion.linea2)
        partes.extend(
            [direccion.ciudad, direccion.provincia, direccion.codigo_postal]
        )
        return ", ".join(partes)
