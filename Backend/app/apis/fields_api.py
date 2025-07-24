from fastapi import APIRouter, Depends, HTTPException # type: ignore
from sqlalchemy.orm import Session # type: ignore
from typing import List

from models import fields_model, db_models
from core.security import get_current_user
from core.database import get_db

router = APIRouter(
    prefix="/fields",
    tags=["fields"]
)

@router.post("/add", response_model=fields_model.FieldOut)
def add_field(
    field_data: fields_model.FieldCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    new_field = db_models.Field(
        user_id=current_user.id,
        name=field_data.name,
        north=field_data.north,
        south=field_data.south,
        east=field_data.east,
        west=field_data.west
    )
    db.add(new_field)
    db.commit()
    db.refresh(new_field)
    return new_field

@router.get("/list", response_model=List[fields_model.FieldOut])
def list_fields(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    fields = db.query(db_models.Field).filter(db_models.Field.user_id == current_user.id).all()
    return fields
