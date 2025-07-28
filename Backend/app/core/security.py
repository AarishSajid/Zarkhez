from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional, Annotated
import os

from app.core.database import get_db
from app.models import db_model
from app.core.config import Settings

settings = Settings()

# Load secret & algorithm
SECRET_KEY = settings.jwt_secret
ALGORITHM = "HS256"

# ✅ SINGLE, global declaration of oauth2_scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: str = Depends(oauth2_scheme)
) -> db_model.User:
    """
    Decode JWT token, find user in DB, return user.
    Raises 401 if token invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # user_id is string → cast to int
    user = db.query(db_model.User).filter(db_model.User.id == int(user_id)).first()
    print("DECODE SECRET_KEY:", SECRET_KEY)
    if user is None:
        raise credentials_exception
    return user
