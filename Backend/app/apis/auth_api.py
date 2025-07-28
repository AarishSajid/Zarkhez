from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm

from app.models import auth_model, db_model
from app.services import auth_service
from app.core.database import get_db


router = APIRouter(
    tags=["auth"]
)

@router.post("/register", response_model=auth_model.Token)
def register(
    user_data: auth_model.UserCreate,
    db: Annotated[Session, Depends(get_db)]
):
    existing = db.query(db_model.User).filter(db_model.User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = auth_service.hash_password(user_data.password)
    new_user = db_model.User(email=user_data.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = auth_service.create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=auth_model.Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    # Note: form_data.username is actually the email
    user = db.query(db_model.User).filter(db_model.User.email == form_data.username).first()
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
