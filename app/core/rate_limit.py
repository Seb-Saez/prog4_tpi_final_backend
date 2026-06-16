"""
Rate limiter global de la aplicación.

Usa slowapi con backend in-memory (default). Para producción multi-worker
o multi-server, configurar storage_uri="redis://..." en el Limiter.

Cómo se usa en un router:

    from fastapi import Request
    from app.core.rate_limit import limiter

    @router.post("/register")
    @limiter.limit("3/minute")
    def register(request: Request, ...):
        ...

NOTA: slowapi requiere que la función reciba `request: Request` como parámetro
para poder extraer la IP del cliente.
"""
from fastapi_throttle import RateLimiter

# Spec 4.3: máximo 5 intentos por IP en 15 minutos, tanto en login como register.
register_limiter = RateLimiter(times=5, seconds=900)  # 5 requests por 15 minutos (spec)

login_limiter = RateLimiter(times=5, seconds=900)  # 5 requests por 15 minutos (spec)