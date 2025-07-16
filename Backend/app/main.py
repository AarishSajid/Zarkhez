from fastapi import FastAPI
from app.apis import NDVI_api  # Import your NDVI router
# from app.api import disease, auth  # Your other routers

app = FastAPI(
    title="Agricultural Monitoring API",
    description="API for disease detection and NDVI analysis",
    version="1.0.0"
)

# Include NDVI router
app.include_router(NDVI_api.router, prefix="/api/v1")

# Include other routers as you create them
# app.include_router(disease.router, prefix="/api/v1")
# app.include_router(auth.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Agricultural Monitoring API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agricultural-monitoring-api"}