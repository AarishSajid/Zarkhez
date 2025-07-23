from pydantic import BaseModel # type: ignore
from typing import Optional,Dict,List
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
    latitude: Optional[float]   # May be None if using bbox
    longitude: Optional[float]  # May be None if using bbox
    ndvi_value: float
    date: str
    vegetation_health: str  # "Poor", "Fair", "Good", "Excellent"
    average_ndvi: Optional[float] = None
    min_ndvi: Optional[float] = None
    max_ndvi: Optional[float] = None
    valid_pixel_count: Optional[int] = None
    health_distribution: Optional[Dict[str, int]] = None  # {"Poor": count, "Fair": count, "Good": count, "Excellent": count}
    bbox: Optional[List[float]] = None  # [west, south, east, north]
    mode: Optional[str] = None  # "point" or "bbox"
    message: str

class NDVIData(BaseModel):
    """Model for NDVI data point (historical)"""
    latitude: float
    longitude: float
    ndvi_value: float
    date: datetime
    created_at: datetime = datetime.now()
