from pydantic import BaseModel# type: ignore

class UserCreate(BaseModel):
    name: str
    phone: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
