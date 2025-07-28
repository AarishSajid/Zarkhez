from sqlalchemy import create_engine # type: ignore
from sqlalchemy.orm import sessionmaker 
from app.models.db_model import Base # type: ignore
from sqlalchemy.orm import Session 
from typing import Generator
import os
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
