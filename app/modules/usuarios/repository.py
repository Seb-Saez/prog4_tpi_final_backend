from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.usuarios.model import Usuario
from app.modules.rol.model import UsuarioRol, Rol
from app.modules.rol.enums import RolEnum


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    def get_by_username(self, username: str) -> Usuario | None:
        return self.session.exec(
            select(Usuario)
            .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
            .where(Usuario.username == username)
            .where(col(Usuario.deleted_at).is_(None))
        ).first()

    def get_by_email(self, email: str) -> Usuario | None:
        return self.session.exec(
            select(Usuario)
            .options(selectinload(Usuario.roles).selectinload(UsuarioRol.rol))
            .where(Usuario.email == email)
            .where(col(Usuario.deleted_at).is_(None))
        ).first()

    def get_by_id(self, record_id: int) -> Usuario | None:
        instance = self.session.get(
            Usuario,
            record_id,
            options=[selectinload(Usuario.roles).selectinload(UsuarioRol.rol)],
        )
        if instance is None or instance.deleted_at is not None:
            return None
        return instance

    def get_by_rol(self, rol: RolEnum) -> list[Usuario]:
        return list(
            self.session.exec(
                select(Usuario)
                .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
                .join(Rol, UsuarioRol.rol_id == Rol.id)
                .where(Rol.codigo == rol.value)
                .where(col(Usuario.deleted_at).is_(None))
            ).all()
        )



