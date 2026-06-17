"""
Middleware de logging de peticiones HTTP (logs + timing).

Registra por consola cada request entrante con método, ruta, código de estado
y duración en milisegundos. Cumple el requisito de "mostrar las peticiones
realizadas" y agrega timing para detectar endpoints lentos.

Sólo aplica a requests HTTP: BaseHTTPMiddleware opera sobre el scope http, así
que las conexiones WebSocket no se ven afectadas.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.core.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Loguea cada petición con su latencia. Si el endpoint lanza una excepción
    no controlada, también la registra y la re-propaga para que el exception
    handler global la convierta en una respuesta 500."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "%s %s → ERROR (%.1f ms)",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s → %d (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
