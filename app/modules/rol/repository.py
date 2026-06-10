from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, col
from app.core.repository import BaseRepository
from app.modules.rol.model import Rol, UsuarioRol


class RolRepository(BaseRepository[Rol]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Rol)

    def get_by_codigo(self, codigo: str) -> Rol | None:
        return self.session.exec(
            select(Rol)
            .where(Rol.codigo == codigo)
            .where(col(Rol.deleted_at).is_(None))
        ).first()


class UsuarioRolRepository(BaseRepository[UsuarioRol]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UsuarioRol)

    def get_by_usuario_and_rol(self, usuario_id: int, rol_id: int) -> UsuarioRol | None:
        return self.session.exec(
            select(UsuarioRol)
            .where(UsuarioRol.usuario_id == usuario_id)
            .where(UsuarioRol.rol_id == rol_id)
        ).first()

    def hard_delete(self, instance: UsuarioRol) -> None:
        """Eliminación física de la fila de la tabla intermedia."""
        self.session.delete(instance)
        self.session.flush()
