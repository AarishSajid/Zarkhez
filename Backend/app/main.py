from fastapi import FastAPI # type: ignore
from app.apis import NDVI_api, auth_api, fields_api  # Import your NDVI router
# from app.api import disease, auth  # Your other routers
from dotenv import load_dotenv
load_dotenv()


app = FastAPI(
    title="Agricultural Monitoring API",
    description="API for disease detection and NDVI analysis",
    version="1.0.0"
)
# Include your routers
app.include_router(NDVI_api.router, prefix="/ndvi")
app.include_router(auth_api.router, prefix="/auth")
app.include_router(fields_api.router, prefix="/fields")

@app.get("/")
async def root():
    return {"message": "Agricultural Monitoring API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agricultural-monitoring-api"}