from sqlmodel import create_engine, Session
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
