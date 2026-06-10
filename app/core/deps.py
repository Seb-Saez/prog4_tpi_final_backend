from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork, get_uow
from app.modules.usuarios.schema import UserPublic


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")

        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    uow: Annotated[UsuarioUnitOfWork, Depends(get_uow)],
) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    token_version_claim: int | None = payload.get("tv")
    if token_version_claim is None:
        raise credentials_exception

    roles_claim: list[str] | None = payload.get("roles")
    if roles_claim is None:
        # Token del sistema anterior (claim "rol" en vez de "roles")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token obsoleto: cerrá sesión y volvé a iniciar",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with uow:
        user = uow.usuarios.get_by_username(username)
        if user is None:
            raise credentials_exception
        if user.token_version != token_version_claim:
            raise credentials_exception

        return UserPublic.model_validate(user)


async def get_current_active_user(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        )

    return current_user


def require_role(allowed_roles: list[str]):
    async def role_checker(
        current_user: Annotated[UserPublic, Depends(get_current_active_user)],
    ) -> UserPublic:
        user_roles = set(current_user.roles)
        allowed = set(allowed_roles)
        if not (user_roles & allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes",
            )
        return current_user

    return role_checker
