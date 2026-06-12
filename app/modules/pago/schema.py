from sqlmodel import SQLModel


class PreferenciaResponse(SQLModel):
    init_point: str
    preference_id: str
