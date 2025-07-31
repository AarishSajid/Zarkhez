from fastapi import APIRouter, Query # type: ignore
from app.services.weather_service import fetch_weather

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("/")
def get_weather(
    lat: float = Query(default=None),
    lon: float = Query(default=None),
    city: str = Query(default=None)
):
    result = fetch_weather(lat=lat, lon=lon, city=city)
    return result
