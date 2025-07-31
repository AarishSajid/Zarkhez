from fastapi import APIRouter, UploadFile, File, Depends, HTTPException  # type: ignore
from app.services.disease_service import predict_disease
from app.core.security import get_current_user, oauth2_scheme
from app.models import db_model

router = APIRouter(
    prefix="/disease",
    tags=["disease"]
)

@router.post("/predict")
async def predict_crop_disease(
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    current_user: db_model.User = Depends(get_current_user)
):
    try:
        image_bytes = await file.read()
        label = predict_disease(image_bytes)
        return {"prediction": label}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
