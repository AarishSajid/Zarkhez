from sqlalchemy import Column, Integer, String, ForeignKey, DateTime # type: ignore 
from sqlalchemy.orm import relationship, declarative_base # type: ignore
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    fields = relationship("Field", back_populates="owner")


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    north = Column(String, nullable=False)
    south = Column(String, nullable=False)
    east = Column(String, nullable=False)
    west = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="fields")
