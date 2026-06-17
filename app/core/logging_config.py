"""
Configuración centralizada de logging para toda la aplicación.

Antes de esto, varios módulos creaban loggers con `getLogger(...)` pero nadie
configuraba handlers ni nivel, así que esos logs salían con el formato por
defecto de Python (o se perdían). Acá se define un único punto de setup
(`setup_logging`) que instala un handler de consola con formato uniforme.

Se configura SOLO el árbol de loggers "app" (no el root ni los de uvicorn),
para no duplicar líneas con el logger de acceso del propio servidor.

Se invoca una sola vez al arrancar la app (en main.py). Es idempotente: llamarlo
de nuevo (por ejemplo al reimportar en los tests) no apila handlers repetidos.
"""
import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False

# 2026-06-17 00:53:10 | INFO     | app.core.middleware | GET /api/v1/productos → 200 (12.4 ms)

def setup_logging(level: int = logging.INFO) -> None:
    """Instala un handler de consola sobre el logger `app` (idempotente)."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))

    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    app_logger.addHandler(handler)
    app_logger.propagate = False

    _configured = True
