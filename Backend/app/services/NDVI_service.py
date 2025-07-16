import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from app.models.NDVI_model import NDVIRequest, NDVIResponse, NDVIData
from sentinelhub import SHConfig, SentinelHubRequest, DataCollection, MimeType, bbox_to_dimensions, BBox  # type: ignore


class NDVIService:
    """Service for NDVI calculations and analysis"""

    def __init__(self):
        # Initialize Sentinel Hub config
        self.config = SHConfig()
        self.config.sh_client_id = "92530bbf-a5fd-4e21-83bb-198bdca75bf7"
        self.config.sh_client_secret = "MorXNIReuyVL70hQR70lgaRJ9qE0cvFY"
        # Optionally: self.config.sh_base_url = 'https://services.sentinel-hub.com'

    def calculate_ndvi(self, request: NDVIRequest) -> NDVIResponse:
        """
        Calculate NDVI for given coordinates and date range using Sentinel Hub
        """
        try:
            # Define a very small bounding box around the point
            bbox = BBox(
                bbox=[request.longitude - 0.0001, request.latitude - 0.0001,
                      request.longitude + 0.0001, request.latitude + 0.0001],
                crs='EPSG:4326'
            )

            size = bbox_to_dimensions(bbox, resolution=10)  # 10m resolution

            evalscript = """
            //VERSION=3
            function setup() {
              return {
                input: ["B04", "B08"],
                output: { bands: 1 }
              };
            }
            function evaluatePixel(sample) {
              let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
              return [ndvi];
            }
            """

            request_sentinel = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L1C,
                        time_interval=(request.start_date, request.end_date)
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response('default', MimeType.TIFF)
                ],
                bbox=bbox,
                size=size,
                config=self.config
            )

            ndvi_data = request_sentinel.get_data()
            ndvi_array = ndvi_data[0].squeeze()
            ndvi_value = float(np.nanmean(ndvi_array))
            ndvi_value = max(-1, min(1, ndvi_value))  # clamp between -1 and 1


            health_status = self._get_vegetation_health(ndvi_value)

            return NDVIResponse(
                latitude=request.latitude,
                longitude=request.longitude,
                ndvi_value=round(ndvi_value, 3),
                date=request.end_date,
                vegetation_health=health_status,
                message="NDVI analysis from Sentinel Hub"
            )

        except Exception as e:
            return NDVIResponse(
                latitude=request.latitude,
                longitude=request.longitude,
                ndvi_value=0.0,
                date=request.end_date,
                vegetation_health="Unknown",
                message=f"Error fetching NDVI: {str(e)}"
            )

    def _get_vegetation_health(self, ndvi_value: float) -> str:
        """Determine vegetation health based on NDVI value"""
        if ndvi_value < 0.2:
            return "Poor"
        elif ndvi_value < 0.4:
            return "Fair"
        elif ndvi_value < 0.6:
            return "Good"
        else:
            return "Excellent"

    def get_ndvi_history(self, lat: float, lon: float, days: int = 30) -> List[Dict]:
        """
        Get NDVI history for the last N days
        Note: still uses mock data; you can replace with real API calls & caching later
        """
        history = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            ndvi_value = 0.6 + np.random.normal(0, 0.1)  # simple mock
            ndvi_value = max(-1, min(1, ndvi_value))

            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "ndvi_value": round(ndvi_value, 3),
                "vegetation_health": self._get_vegetation_health(ndvi_value)
            })

        return list(reversed(history))  # Return in chronological order

    def analyze_trend(self, ndvi_history: List[Dict]) -> Dict:
        """Analyze NDVI trend over time"""
        if len(ndvi_history) < 2:
            return {"trend": "insufficient_data", "message": "Not enough data for trend analysis"}

        values = [item["ndvi_value"] for item in ndvi_history]

        if len(values) >= 7:
            recent_avg = np.mean(values[-7:])
            older_avg = np.mean(values[:-7])

            if recent_avg > older_avg + 0.05:
                trend = "improving"
            elif recent_avg < older_avg - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "current_avg": round(np.mean(values[-7:]) if len(values) >= 7 else np.mean(values), 3),
            "message": f"Vegetation health is {trend}"
        }
