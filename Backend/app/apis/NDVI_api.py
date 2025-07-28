from fastapi import APIRouter, HTTPException, Query, Depends  # type: ignore
from sqlalchemy.orm import Session 
from datetime import datetime, timedelta
from typing import Annotated

from app.services.NDVI_service import NDVIService
from app.models.NDVI_model import NDVIRequest, NDVIResponse
from app.core.security import get_current_user, oauth2_scheme
from app.core.database import get_db
from app.models import db_model

router = APIRouter(prefix="/ndvi", tags=["NDVI"])
ndvi_service = NDVIService()

@router.post("/analyze", response_model=NDVIResponse)
async def analyze_ndvi_for_field(
    field_id: int,
    start_date: str,
    end_date: str,
    db: Annotated[Session, Depends(get_db)],
    token: str = Depends(oauth2_scheme),
    current_user: db_model.User = Depends(get_current_user)
):
    print("Token received:", token)
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        if end > datetime.now():
            raise HTTPException(status_code=400, detail="End date cannot be in the future")

        field = db.query(db_model.Field).filter(
            db_model.Field.id == field_id,
            db_model.Field.user_id == current_user.id
        ).first()
        if not field:
            raise HTTPException(status_code=404, detail="Field not found or does not belong to user")

        request = NDVIRequest(
            north=field.north, south=field.south, east=field.east, west=field.west,
            start_date=start_date, end_date=end_date
        )
        result = ndvi_service.calculate_ndvi(request)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/history")
async def get_ndvi_history_for_field(
    field_id: int,
    db: Annotated[Session, Depends(get_db)],
    token: str = Depends(oauth2_scheme),
    current_user: db_model.User = Depends(get_current_user),
    days: int = Query(30, description="Total days to look back", ge=1, le=365),
    step_days: int = Query(7, description="Interval in days between measurements", ge=1, le=30)
):
    print("Token received:", token)
    try:
        if days < step_days:
            raise HTTPException(status_code=400, detail="`days` must be >= `step_days`")

        field = db.query(db_model.Field).filter(
            db_model.Field.id == field_id,
            db_model.Field.user_id == current_user.id
        ).first()
        if not field:
            raise HTTPException(status_code=404, detail="Field not found or does not belong to user")

        center_lat = (field.north + field.south) / 2
        center_lon = (field.east + field.west) / 2

        history = ndvi_service.get_ndvi_history(center_lat, center_lon, days, step_days)
        trend = ndvi_service.analyze_trend(history)

        return {
            "field_id": field_id,
            "field_name": field.name,
            "latitude": center_lat,
            "longitude": center_lon,
            "history": history,
            "trend_analysis": trend
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health-status")
async def get_vegetation_health(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    token: str = Depends(oauth2_scheme),
    current_user: db_model.User = Depends(get_current_user)
):
    print("Token received:", token)
    try:
        today = datetime.now()
        request = NDVIRequest(
            latitude=latitude,
            longitude=longitude,
            start_date=(today - timedelta(days=1)).strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d")
        )
        result = ndvi_service.calculate_ndvi(request)
        return {
            "latitude": latitude,
            "longitude": longitude,
            "current_ndvi": result.ndvi_value,
            "vegetation_health": result.vegetation_health,
            "date": result.date,
            "recommendations": _get_recommendations(result.vegetation_health)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/image")
async def get_satellite_image(
    request: NDVIRequest,
    token: str = Depends(oauth2_scheme),
    current_user: db_model.User = Depends(get_current_user)
):
    print("Token received:", token)
    return ndvi_service.get_true_color_image(request)

@router.post("/heatmap")
async def get_ndvi_heatmap_image(
    request: NDVIRequest,
    token: str = Depends(oauth2_scheme),
    current_user: db_model.User = Depends(get_current_user)
):
    print("Token received:", token)
    return ndvi_service.get_heatmap_image(request)

def _get_recommendations(health_status: str) -> list:
    recommendations = {
        "Poor": [
            "Consider irrigation if water is available",
            "Check for pest or disease issues",
            "Soil testing recommended",
            "Consider fertilization"
        ],
        "Fair": [
            "Monitor closely for improvement",
            "Ensure adequate water supply",
            "Check for early signs of stress"
        ],
        "Good": [
            "Maintain current management practices",
            "Continue regular monitoring",
            "Prepare for potential seasonal changes"
        ],
        "Excellent": [
            "Vegetation is healthy",
            "Continue current management",
            "Good time for planning future crops"
        ]
    }
    return recommendations.get(health_status, ["Continue monitoring"])
