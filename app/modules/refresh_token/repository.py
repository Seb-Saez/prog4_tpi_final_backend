from datetime import datetime, timezone
from sqlmodel import Session, select,col
from app.core.repository import BaseRepository
from app.modules.refresh_token.model import RefreshToken

class RefreshTokenRepository(BaseRepository[RefreshToken]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, RefreshToken)

    def get_valid_by_usuario(self, usuario_id: int) -> list[RefreshToken]:
        now = datetime.now(timezone.utc)
        return list(self.session.exec(
            select(RefreshToken)
            .where(RefreshToken.usuario_id == usuario_id)
            .where(col(RefreshToken.revoked_at).is_(None))
            .where(RefreshToken.expires_at > now)
        ).all())
    
    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()
    
    def revoke_all_for_usuario(self, usuario_id: int) -> None:
        now = datetime.now(timezone.utc)
        for rt in self.get_valid_by_usuario(usuario_id):
            rt.revoked_at = now
            self.session.add(rt)