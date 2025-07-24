from fastapi import APIRouter, Depends, HTTPException, status # type: ignore
from sqlalchemy.orm import Session # type: ignore
from datetime import timedelta

from models import auth_model, db_models
from services import auth_service

# You will need to implement get_db to get your SQLAlchemy session
from core.database import get_db

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/register", response_model=auth_model.Token)
def register(user_data: auth_model.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(db_models.User).filter(db_models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = auth_service.hash_password(user_data.password)
    new_user = db_models.User(email=user_data.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Issue token immediately
    access_token = auth_service.create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=auth_model.Token)
def login(user_data: auth_model.UserCreate, db: Session = Depends(get_db)):
    user = db.query(db_models.User).filter(db_models.User.email == user_data.email).first()
    if not user or not auth_service.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = auth_service.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}
