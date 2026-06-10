from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger
from datetime import datetime
from app.core.datetime_utils import utcnow


class Auditoria(SQLModel):
    created_at: datetime | None = Field(default_factory=utcnow)
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

class BaseEntity(Auditoria, SQLModel):
    id: int = Field(
        default=None, 
        primary_key=True, 
        sa_type=BigInteger
    )