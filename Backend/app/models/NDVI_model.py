from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NDVIRequest(BaseModel):
    """
    Request model for NDVI analysis.
    User can provide either:
      - latitude & longitude (single point)
      - OR north, south, east, west (bounding box)
    """
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
    north: Optional[float] = None
    south: Optional[float] = None
    east: Optional[float] = None
    west: Optional[float] = None
    start_date: str
    end_date: str

class NDVIResponse(BaseModel):
    """Response model for NDVI analysis"""
    latitude: Optional[float]   # May be None if using bbox
    longitude: Optional[float]  # May be None if using bbox
    ndvi_value: float
    date: str
    vegetation_health: str  # "Poor", "Fair", "Good", "Excellent"
    message: str

class NDVIData(BaseModel):
    """Model for NDVI data point (historical)"""
    latitude: float
    longitude: float
    ndvi_value: float
    date: datetime
    created_at: datetime = datetime.now()
