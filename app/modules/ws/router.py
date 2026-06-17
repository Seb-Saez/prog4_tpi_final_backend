import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, WebSocket, WebSocketDisconnect, status
from sqlmodel import Session, select

from app.core import database as _db
from app.core.security import decode_access_token
from app.core.websocket import manager
from app.modules.pedido.model import Pedido
from app.modules.usuarios.model import Usuario
import asyncio

logger = logging.getLogger("app.modules.ws")

router_ws = APIRouter()


def _determinar_rol(roles: list[str]) -> str:
    if "ADMIN" in roles:
        return "admin"
    if "COCINA" in roles:
        return "cocina"
    if "CAJA" in roles:
        return "caja"
    return "user"


def _es_staff(rol: str) -> bool:
    return rol in ("admin", "cocina", "caja")


@router_ws.websocket("/ws/pedidos")
async def ws_pedidos(
    websocket: WebSocket,
    access_token: Annotated[str | None, Cookie()] = None,
):
    payload = decode_access_token(access_token) if access_token else None
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    username: str | None = payload.get("sub")
    roles: list[str] = payload.get("roles", [])

    if not username:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    rol = _determinar_rol(roles)
    is_staff = _es_staff(rol)

    with Session(_db.engine) as session:
        user = session.exec(
            select(Usuario).where(Usuario.username == username)
        ).first()

        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = user.id
        await manager.connect(websocket, rol, user_id)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "PING"})
                continue

            action = data.get("action")

            # NOTE: heartbeat implementado — cada 30s sin mensajes del cliente
            # se envía un PING para mantener la conexión viva y evitar que
            # navegadores/proxies cierren el socket por inactividad.
            if action == "subscribe-order":
                order_id = data.get("order_id")
                if not isinstance(order_id, int):
                    await websocket.send_json({
                        "event": "ERROR",
                        "data": {"detail": "order_id debe ser un entero"},
                    })
                    continue

                if not is_staff:
                    with Session(_db.engine) as session:
                        pedido = session.exec(
                            select(Pedido).where(Pedido.id == order_id)
                        ).first()
                        if pedido is None or pedido.usuario_id != user_id:
                            await websocket.send_json({
                                "event": "ERROR",
                                "data": {"detail": "No puedes suscribirte a este pedido"},
                            })
                            continue

                manager.join_order_room(websocket, order_id)
                await websocket.send_json({
                    "event": "SUBSCRIBED",
                    "data": {"order_id": order_id},
                })

            elif action == "unsubscribe-order":
                order_id = data.get("order_id")
                if isinstance(order_id, int):
                    manager.leave_order_room(websocket, order_id)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Error en WebSocket /ws/pedidos: {e}")
    finally:
        manager.disconnect(websocket)


@router_ws.websocket("/cocina/ws")
async def ws_cocina(
    websocket: WebSocket,
    access_token: Annotated[str | None, Cookie()] = None,
):
    payload = decode_access_token(access_token) if access_token else None
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    username: str | None = payload.get("sub")
    roles: list[str] = payload.get("roles", [])

    if not username:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    rol = _determinar_rol(roles)

    if not _es_staff(rol):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    with Session(_db.engine) as session:
        user = session.exec(
            select(Usuario).where(Usuario.username == username)
        ).first()

        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(websocket, rol, user.id)

    try:
        while True:
            # NOTE: heartbeat implementado — cada 30s sin mensajes del cliente
            # se envía un PING para mantener la conexión viva y evitar que
            # navegadores/proxies cierren el socket por inactividad.
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "PING"})
                continue
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Error en WebSocket /cocina/ws: {e}")
    finally:
        manager.disconnect(websocket)
