from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Annotated

from app.models import fields_model, db_model
from app.core.security import get_current_user,oauth2_scheme
from app.core.database import get_db

# ✅ Add this: tells Swagger that protected routes need Bearer token


router = APIRouter(
    prefix="/fields",
    tags=["fields"]
)

@router.post("/add", response_model=fields_model.FieldOut)
def add_field(
    field_data: fields_model.FieldCreate,
    db: Annotated[Session, Depends(get_db)],
    token: str = Depends(oauth2_scheme),  # ✅ tells OpenAPI: needs Bearer token
    current_user: db_model.User = Depends(get_current_user)
):
    print("Token received:", token)
    new_field = db_model.Field(
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
    db: Annotated[Session, Depends(get_db)],
    token: str = Depends(oauth2_scheme),  # ✅ same here
    current_user: db_model.User = Depends(get_current_user)
):
    print("Token received:", token)
    fields = db.query(db_model.Field).filter(db_model.Field.user_id == current_user.id).all()
    return fields
