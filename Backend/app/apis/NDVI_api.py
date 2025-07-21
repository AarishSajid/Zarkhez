from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from fastapi.responses import Response

from app.services.NDVI_service import NDVIService
from app.models.NDVI_model import NDVIRequest, NDVIResponse

router = APIRouter(prefix="/ndvi", tags=["NDVI"])
ndvi_service = NDVIService()

@router.post("/analyze", response_model=NDVIResponse)
async def analyze_ndvi(request: NDVIRequest):
    """
    Analyze NDVI for given coordinates and date range
    """
    try:
        # Validate date format
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if end_date > datetime.now():
            raise HTTPException(status_code=400, detail="End date cannot be in the future")
        
        # Validate coordinates
        if not (-90 <= request.latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        
        if not (-180 <= request.longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        
        result = ndvi_service.calculate_ndvi(request)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/history")
async def get_ndvi_history(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    days: int = Query(30, description="Number of days to retrieve", ge=1, le=365)
):
    """
    Get NDVI history for the specified coordinates
    """
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        
        if not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        
        history = ndvi_service.get_ndvi_history(latitude, longitude, days)
        trend = ndvi_service.analyze_trend(history)
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "history": history,
            "trend_analysis": trend
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health-status")
async def get_vegetation_health(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate")
):
    """
    Get current vegetation health status for given coordinates
    """
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        
        if not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        
        # Create a request for current date
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

def _get_recommendations(health_status: str) -> list:
    """Get recommendations based on vegetation health"""
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

@router.post("/image")
async def get_satellite_image(request: NDVIRequest):
    return ndvi_service.get_true_color_image(request)

