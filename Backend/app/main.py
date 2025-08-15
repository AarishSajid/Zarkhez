from fastapi import FastAPI # type: ignore
from app.apis import NDVI_api, auth_api, fields_api, weather_api,disease_api  # Import your NDVI router
# from app.api import disease, auth  # Your other routers
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Agricultural Monitoring API",
    description="API for disease detection and NDVI analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify exact domains instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your routers
app.include_router(NDVI_api.router, prefix="/ndvi")
app.include_router(auth_api.router, prefix="/auth")
app.include_router(fields_api.router, prefix="/fields")
app.include_router(weather_api.router, prefix="/weather")
app.include_router(disease_api.router, prefix="/disease")

@app.get("/")
async def root():
    return {"message": "Agricultural Monitoring API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agricultural-monitoring-api"}