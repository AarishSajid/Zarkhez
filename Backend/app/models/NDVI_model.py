from pydantic import BaseModel #typing: ignore
from typing import Optional
from datetime import datetime

class NDVIRequest(BaseModel):
    """Request model for NDVI analysis"""
    latitude: float
    longitude: float
    start_date: str  # Format: YYYY-MM-DD
    end_date: str    # Format: YYYY-MM-DD

class NDVIResponse(BaseModel):
    """Response model for NDVI analysis"""
    latitude: float
    longitude: float
    ndvi_value: float
    date: str
    vegetation_health: str  # "Poor", "Fair", "Good", "Excellent"
    message: str

class NDVIData(BaseModel):
    """Model for NDVI data point"""
    latitude: float
    longitude: float
    ndvi_value: float
    date: datetime
    created_at: datetime = datetime.now()