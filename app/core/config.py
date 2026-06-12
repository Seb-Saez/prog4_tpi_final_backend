"""
Configuración centralizada leída desde variables de entorno.

Adopta el patrón de u_05_v2: variables individuales de PostgreSQL
con @computed_field para construir DATABASE_URL automáticamente.
Los valores sensibles (SECRET_KEY, POSTGRES_PASSWORD) viven en .env.
"""

from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Base de datos (PostgreSQL — patrón u_05_v2) ──────────────────────────
    postgres_user:     str = "postgres"
    postgres_password: str = "password"
    postgres_db:       str = "foodstore"
    postgres_host:     str = "localhost"
    postgres_port:     int = 5432


# @computed_field:
# Decorador de Pydantic v2 que indica que este atributo calculado
# debe incluirse en la serialización del modelo (model_dump / JSON),
# aunque no sea un campo persistido.

# @property:
# Convierte el método en una propiedad de solo lectura.
# Permite acceder como atributo (obj.algo) en lugar de método (obj.algo()).
# El valor se calcula dinámicamente en cada acceso.
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        Construye la URL de conexión a PostgreSQL.
        Para tests se sobreescribe con SQLite en memoria desde conftest.py.
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ─── JWT ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(..., min_length=32, description="Mínimo 32 caracteres (HS256 = 256 bits)")                    # Obligatorio — sin default. Mínimo 32 chars.
    ALGORITHM:  str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False  # True en producción (HTTPS), False en desarrollo (HTTP)
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"  # "none" para front/back en dominios distintos (ngrok). Exige COOKIE_SECURE=True.

    # ─── Admin inicial (seed) ─────────────────────────────────────────────────
    ADMIN_INITIAL_USERNAME: str = "admin"
    ADMIN_INITIAL_EMAIL:    str = "admin@foodstore.local"
    ADMIN_INITIAL_FULLNAME: str = "Administrador"
    ADMIN_INITIAL_PASSWORD: str = Field(..., min_length=8, description="Password del admin seedeado al primer arranque")

    # ─── MercadoPago ──────────────────────────────────────────────
    MP_ACCESS_TOKEN: str = "APP_USR-8955219029601277-061207-951192531c5d0416c3ef30af71b5de02-3468655924"
    MP_NOTIFICATION_URL: str = "https://aa96-191-81-176-225.ngrok-free.app"  # URL pública para webhooks (ej: ngrok)
    MP_FRONTEND_URL: str = "http://localhost:5173"  # URL del frontend para back_urls

    # ─── Cloudinary ───────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    model_config = {
        "env_file":          ".env",
        "env_file_encoding": "utf-8",
        "extra":             "ignore",   # ignora vars extra del .env (ej. DATABASE_URL literal)
    }


# Instancia global — importar desde aquí en toda la app
settings = Settings()   # type: ignore[call-arg]
