from pydantic import BaseModel # type: ignore

class FieldCreate(BaseModel):
    name: str
    north: float
    south: float
    east: float
    west: float

class FieldOut(BaseModel):
    id: int
    name: str
    north: float
    south: float
    east: float
    west: float

    class Config:
        from_attributes = True
