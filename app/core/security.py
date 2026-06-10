"""
Utilidades de seguridad centralizadas.

Responsabilidades:
- Hashing de contraseñas usando bcrypt (a través de passlib)
- Generación y validación de JWT (firma HS256 con python-jose)

Motivación:
- Evitar duplicación de lógica de seguridad
- Permitir reutilización (routers, seeds, tests, etc.)
- Mantener separación de capas (no mezclar con endpoints)
"""

# Manejo de fechas para expiración de tokens (timezone-aware → correcto)
from datetime import datetime, timedelta, timezone

# Librería para JWT (encode/decode + manejo de errores)
import jwt
from jwt.exceptions import PyJWTError
from app.core.config import settings

import bcrypt
import hashlib
import secrets


# ─────────────────────────────────────────────────────────────────────────────
# HASHING DE CONTRASEÑAS (bcrypt)
# ─────────────────────────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# JWT (JSON Web Tokens) // GENERACIÓN Y VALIDACIÓN // PyJWT
# ─────────────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, token_version: int, expires_delta: timedelta | None = None) -> str:
    """
    Genera un JWT firmado (HS256).

    Parámetros:
    - data: payload base (ej: {"sub": username, "role": role})
    - token_version: versión del token para manejo de invalidación
    - expires_delta: override opcional del tiempo de expiración

    Comportamiento:
    - Clona el payload (evita mutación externa)
    - Calcula expiración 
    - Agrega claims estándar:
        * "exp"  → expiración
        * "type" → tipo de token (acceso)

    Retorna:
    - Token JWT firmado (string)
    """

    # Copia defensiva del payload
    to_encode = data.copy()

    # Define expiración:
    # - usa valor custom si viene
    # - sino usa config global
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Agrega claims al payload
    to_encode.update({
        "type": "access",  # distingue access vs refresh (buena práctica)
        "exp": expire,      # claim estándar JWT
        "tv":token_version
    })

    # Firma el token:
    # - SECRET_KEY → clave simétrica
    # - ALGORITHM → HS256
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT.

    Validaciones implícitas de jwt.decode():
    - Firma válida
    - Algoritmo permitido
    - Expiración (exp)

    Validación adicional:
    - "type" == "access" (evita usar refresh token como access)

    Retorna:
    - dict → payload válido
    - None → token inválido (cualquier error)

    Nota de diseño:
    - Se encapsulan excepciones → el caller no maneja errores criptográficos
    """

    try:
        # Decodifica y valida firma + exp
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Validación de tipo de token (defensa extra)
        if payload.get("type") != "access":
            return None

        return payload

    except PyJWTError:
        # Cualquier problema (firma, expiración, formato, etc.)
        return None
    

def hash_token(token: str) -> str:
    """SHA-256 del token para almacenar en DB."""
    return hashlib.sha256(token.encode()).hexdigest()

def generate_refresh_token() -> str:
    """Genera un token aleatorio seguro de 32 bytes."""
    return secrets.token_urlsafe(32)

def create_refresh_token_pair() -> tuple[str, str]:
    """Genera par (token_plano, token_hash). El hash va a DB, el plano a la cookie."""
    token = generate_refresh_token()
    return token, hash_token(token)