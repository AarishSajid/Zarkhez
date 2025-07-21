import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from app.models.NDVI_model import NDVIRequest, NDVIResponse, NDVIData
from sentinelhub import SHConfig, SentinelHubRequest, DataCollection, MimeType, bbox_to_dimensions, BBox  # type: ignore
from fastapi import Response
from PIL import Image
import io

class NDVIService:
    """Service for NDVI calculations and analysis"""

    def __init__(self):
        # Initialize Sentinel Hub config
        self.config = SHConfig()
        self.config.sh_client_id = "9d228c34-521c-42ad-9ea3-2b5b00f1e4db"
        self.config.sh_client_secret = "85Jwh9rPxLhL2pOYfhQUsZcBq8jPFBd6"
        # Optionally: self.config.sh_base_url = 'https://services.sentinel-hub.com'

    def calculate_ndvi(self, request: NDVIRequest) -> NDVIResponse:
        """
        Calculate NDVI for given coordinates and date range using Sentinel Hub
        """
        try:
            print(f"DEBUG: north={request.north} ({type(request.north)}), south={request.south} ({type(request.south)}), east={request.east} ({type(request.east)}), west={request.west} ({type(request.west)})")

            if all(isinstance(v, (int, float)) for v in [request.north, request.south, request.east, request.west]):
                print("Using bounding box mode (all numbers)")
                if not (-90 <= request.north <= 90): raise ValueError("North out of range")
                if not (-90 <= request.south <= 90): raise ValueError("South out of range")
                if not (-180 <= request.east <= 180): raise ValueError("East out of range")
                if not (-180 <= request.west <= 180): raise ValueError("West out of range")
                bbox = BBox([request.west, request.south, request.east, request.north], crs='EPSG:4326')
                response_lat = None
                response_lon = None
            elif isinstance(request.latitude, (int, float)) and isinstance(request.longitude, (int, float)):
                print("Using point mode (confirmed numbers)")
                if not (-90 <= request.latitude <= 90): raise ValueError("Latitude out of range")
                if not (-180 <= request.longitude <= 180): raise ValueError("Longitude out of range")
                bbox = BBox([
                    request.longitude - 0.0001, request.latitude - 0.0001,
                    request.longitude + 0.0001, request.latitude + 0.0001
                ], crs='EPSG:4326')
                response_lat = request.latitude
                response_lon = request.longitude
            else:
                print("Neither bbox nor point were valid numbers")
                raise ValueError("Must provide valid bbox or point coordinates")


            print("Created bbox:", bbox)

            size = bbox_to_dimensions(bbox, resolution=10)
            print("Calculated size:", size)

            evalscript = """
            //VERSION=3
            function setup() {
            return {
                input: ["B04", "B08", "SCL"],
                output: { bands: 1 , sampleType: "FLOAT32"}
            };
            }

            function evaluatePixel(sample) {
            // Mask cloud / snow pixels
            if (sample.SCL == 3 || sample.SCL == 8 || sample.SCL == 9 || sample.SCL == 10 || sample.SCL == 11) {
                return [NaN];
            }
            let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
            return [ndvi];
            }

            """


            request_sentinel = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
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
            print("Received data from Sentinel:", type(ndvi_data), len(ndvi_data))
            ndvi_array = ndvi_data[0].squeeze()
            print("NDVI array shape:", ndvi_array.shape)
            print("NDVI array min:", np.nanmin(ndvi_array))
            print("NDVI array max:", np.nanmax(ndvi_array))
            print("NDVI array mean:", np.nanmean(ndvi_array))
            print("NDVI array median:", np.nanmedian(ndvi_array))
            ndvi_value_raw = np.nanmedian(ndvi_array)
            if np.isnan(ndvi_value_raw):
                ndvi_value = 0.0
            else:
                ndvi_value = float(ndvi_value_raw)
            # Clip unrealistically high values (>0.8) to 0.8
            if ndvi_value > 0.8:
                ndvi_value = 0.8
            elif ndvi_value < -0.2:
                ndvi_value = -0.2
                
            valid_pixels = np.count_nonzero(~np.isnan(ndvi_array))
            print(f"Valid NDVI pixels after masking: {valid_pixels}")

            health_status = self._get_vegetation_health(ndvi_value)

            return NDVIResponse(
                latitude=response_lat,
                longitude=response_lon,
                ndvi_value=round(ndvi_value, 3),
                date=request.end_date,
                vegetation_health=health_status,
                message="NDVI analysis from Sentinel Hub"
            )

        except Exception as e:
            print("ERROR in calculate_ndvi:", str(e))
            return NDVIResponse(
                latitude=None,
                longitude=None,
                ndvi_value=0.0,
                date=request.end_date,
                vegetation_health="Unknown",
                message=f"Error fetching NDVI: {str(e)}"
            )

    def get_true_color_image(self, request: NDVIRequest) -> bytes:
        """
        Fetch true color satellite image from Sentinel Hub as PNG.
        """
        # Determine bbox just like in calculate_ndvi
        if all(v is not None for v in [request.north, request.south, request.east, request.west]):
            bbox = BBox([request.west, request.south, request.east, request.north], crs='EPSG:4326')
        elif request.latitude is not None and request.longitude is not None:
            bbox = BBox([
                request.longitude - 0.0001, request.latitude - 0.0001,
                request.longitude + 0.0001, request.latitude + 0.0001
            ], crs='EPSG:4326')
        else:
            raise ValueError("Must provide either bounding box or point coordinates")

        size = bbox_to_dimensions(bbox, resolution=10)  # Adjust resolution if too big

        evalscript = """
        //VERSION=3
        function setup() {
        return {
            input: ["B04", "B03", "B02"],
            output: { bands: 3, sampleType: "UINT8" }
        };
        }
        function evaluatePixel(sample) {
        return [sample.B04 * 255, sample.B03 * 255, sample.B02 * 255];
        }
        """

        request_img = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=(request.start_date, request.end_date)
                )
            ],
            responses=[
                SentinelHubRequest.output_response('default', MimeType.PNG)
            ],
            bbox=bbox,
            size=size,
            config=self.config
        )

        ndvi_array = request_img.get_data()[0]  # NumPy array

        # Avoid nan/inf and clip outliers
        ndvi_array = np.nan_to_num(ndvi_array, nan=0.0)

        # Compute min and max excluding extreme outliers
        min_val = np.percentile(ndvi_array, 2)
        max_val = np.percentile(ndvi_array, 98)

        # Normalize to 0–1
        ndvi_normalized = (ndvi_array - min_val) / (max_val - min_val)
        ndvi_normalized = np.clip(ndvi_normalized, 0, 1)

        # Convert to image
        img = Image.fromarray((ndvi_normalized * 255).astype(np.uint8))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="image/png")


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
