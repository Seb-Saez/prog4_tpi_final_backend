"""
Manejo centralizado de excepciones.

Define una excepción base de dominio (`AppException`) y registra handlers
globales en la app para devolver respuestas JSON uniformes:

- AppException → usa su propio status_code y expone un `detail` seguro.
- Exception    → 500 genérico, sin filtrar detalles internos al cliente,
                 logueando el stacktrace completo en el servidor.

Las HTTPException de FastAPI siguen manejándose con el comportamiento por
defecto del framework (NO se sobreescriben), así que los endpoints actuales no
cambian su respuesta. El handler de `Exception` sólo entra en juego para errores
que hoy ya terminan en un 500 sin formato.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.core.exceptions")


class AppException(Exception):
    """Excepción base de dominio.

    Permite lanzar errores con un status_code y un mensaje pensado para exponer
    al cliente, sin acoplar los services a `HTTPException` de FastAPI.
    """

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los handlers globales en la app. Llamar una vez desde main.py."""

    @app.exception_handler(AppException)
    async def _handle_app_exception(request: Request, exc: AppException):
        logger.warning(
            "AppException en %s %s: %s",
            request.method,
            request.url.path,
            exc.detail,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception):
        logger.exception(
            "Error no controlado en %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor."},
        )
