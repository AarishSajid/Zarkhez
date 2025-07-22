import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from app.models.NDVI_model import NDVIRequest, NDVIResponse, NDVIData
from sentinelhub import SHConfig, SentinelHubRequest, DataCollection, MimeType, bbox_to_dimensions, BBox  # type: ignore
from fastapi import Response # type: ignore
from PIL import Image # type: ignore
import io,os

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

            # Use bbox if all numbers & valid
            if all(isinstance(v, (int, float)) for v in [request.north, request.south, request.east, request.west]):
                if request.north <= request.south:
                    raise ValueError("North must be greater than south")
                if request.east <= request.west:
                    raise ValueError("East must be greater than west")
                if not (-90 <= request.north <= 90): raise ValueError("North out of range")
                if not (-90 <= request.south <= 90): raise ValueError("South out of range")
                if not (-180 <= request.east <= 180): raise ValueError("East out of range")
                if not (-180 <= request.west <= 180): raise ValueError("West out of range")
                print("Using bounding box mode")
                bbox = BBox([request.west, request.south, request.east, request.north], crs='EPSG:4326')
                response_lat = None
                response_lon = None

            # Else use center point
            elif isinstance(request.latitude, (int, float)) and isinstance(request.longitude, (int, float)):
                if not (-90 <= request.latitude <= 90): raise ValueError("Latitude out of range")
                if not (-180 <= request.longitude <= 180): raise ValueError("Longitude out of range")
                print("Using point mode")
                delta = 0.01
                bbox = BBox([
                    request.longitude - delta, request.latitude - delta,
                    request.longitude + delta, request.latitude + delta
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
                    output: { bands: 1, sampleType: "FLOAT32" }
                };
            }

            function evaluatePixel(sample) {
                // Mask clouds & snow
                if ([3, 8, 9, 10, 11].includes(sample.SCL)) return [NaN];
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
                responses=[SentinelHubRequest.output_response('default', MimeType.TIFF)],
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
            ndvi_value = float(ndvi_value_raw) if not np.isnan(ndvi_value_raw) else 0.0

            # Clamp extremes
            ndvi_value = min(max(ndvi_value, -0.2), 0.8)

            valid_pixels = np.count_nonzero(~np.isnan(ndvi_array))
            print(f"Valid NDVI pixels after masking: {valid_pixels}")

            health_status = self.get_vegetation_health(ndvi_value)

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


    def get_true_color_image(self, request: NDVIRequest) -> Response:
        """
        Fetch true color satellite image from Sentinel Hub as PNG.
        """
        # Determine bbox
        if all(v is not None for v in [request.north, request.south, request.east, request.west]):
            if request.north <= request.south:
                    raise ValueError("North must be greater than south")
            if request.east <= request.west:
                    raise ValueError("East must be greater than west")
            bbox = BBox([request.west, request.south, request.east, request.north], crs='EPSG:4326')
        elif request.latitude is not None and request.longitude is not None:
            bbox = BBox([
                request.longitude - 0.0001, request.latitude - 0.0001,
                request.longitude + 0.0001, request.latitude + 0.0001
            ], crs='EPSG:4326')
        else:
            raise ValueError("Must provide either bounding box or point coordinates")

        size = bbox_to_dimensions(bbox, resolution=10)

        # Evalscript for true color (RGB)
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

        # Use clean relative folder: Backend/app/tmp/sentinel_images
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tmp_dir = os.path.abspath(os.path.join(base_dir, '..', 'tmp', 'sentinel_images'))
        os.makedirs(tmp_dir, exist_ok=True)

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
            config=self.config,
            data_folder=tmp_dir
        )

        # Get image data (returns np.ndarray with shape HxWx3)
        img_array = request_img.get_data()[0]

        # Convert to uint8 if needed
        if img_array.dtype != np.uint8:
            img_array = np.clip(img_array, 0, 255).astype(np.uint8)

        # Convert to PIL Image
        img = Image.fromarray(img_array)

        # Save to in‑memory buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Return as FastAPI Response
        return Response(content=buffer.read(), media_type="image/png")
    
    def get_heatmap_image(self, request: NDVIRequest) -> Response:
        """
        Fetch heatmap image based on NDVI values from Sentinel Hub as PNG.
        """
        # Determine bbox
        if all(v is not None for v in [request.north, request.south, request.east, request.west]):
            if request.north <= request.south:
                    raise ValueError("North must be greater than south")
            if request.east <= request.west:
                    raise ValueError("East must be greater than west")
            bbox = BBox([request.west, request.south, request.east, request.north], crs='EPSG:4326')
        elif request.latitude is not None and request.longitude is not None:
            bbox = BBox([
                request.longitude - 0.0001, request.latitude - 0.0001,
                request.longitude + 0.0001, request.latitude + 0.0001
            ], crs='EPSG:4326')
        else:
            raise ValueError("Must provide either bounding box or point coordinates")

        size = bbox_to_dimensions(bbox, resolution=10)

        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: ["B04", "B08", "SCL"],
                output: { bands: 3, sampleType: "UINT8" }
            };
        }
        var cloudValues = [3, 8, 9, 10, 11];
        function evaluatePixel(sample) {
            if (cloudValues.includes(sample.SCL)) {
                return [0, 0, 0]; // black for clouds
            }
            let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
            if (ndvi < 0.0) return [165, 0, 38];
            else if (ndvi < 0.2) return [215, 48, 39];
            else if (ndvi < 0.4) return [244, 109, 67];
            else if (ndvi < 0.6) return [253, 174, 97];
            else if (ndvi < 0.8) return [254, 224, 144];
            else return [255, 255, 191];
        }
        """

        request_img = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(request.start_date, request.end_date)
            )],
            responses=[SentinelHubRequest.output_response('default', MimeType.PNG)],
            bbox=bbox,
            size=size,
            config=self.config
        )

        ndvi_array = request_img.get_data()[0]  # NumPy array, shape (H,W,3), dtype=uint8

        # Convert NumPy array to PNG bytes:
        img = Image.fromarray(ndvi_array, mode='RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="image/png")


    def get_ndvi_history(self, lat: float, lon: float, days: int = 30, step_days: int = 7) -> List[Dict]:
        """
        Fetch real NDVI history by calling calculate_ndvi for the center point
        at each time interval. Skips points where NDVI is zero (i.e., missing or invalid data).

        :param lat: Latitude of center point
        :param lon: Longitude of center point
        :param days: Total number of days to look back
        :param step_days: Interval in days between measurements
        :return: List of dicts with date, ndvi_value, vegetation_health
        """
        history = []
        today = datetime.now()
        num_points = max(1, days // step_days)

        print(f"DEBUG: Requested NDVI history lat={lat}, lon={lon}, days={days}, step_days={step_days}")

        for i in range(num_points):
            end_date = (today - timedelta(days=i * step_days)).strftime("%Y-%m-%d")
            start_date = (today - timedelta(days=(i * step_days) + 1)).strftime("%Y-%m-%d")

            # ONLY use latitude & longitude → keeps bbox fields None → forces point mode
            request = NDVIRequest(
                latitude=lat,
                longitude=lon,
                start_date=start_date,
                end_date=end_date
            )

            response = self.calculate_ndvi(request)

            if response.ndvi_value != 0.0:
                history.append({
                    "date": end_date,
                    "ndvi_value": round(response.ndvi_value, 3),
                    "vegetation_health": response.vegetation_health
                })
            else:
                print(f"DEBUG: Skipped date {end_date} due to missing NDVI data (value=0.0)")

        # Return oldest first
        return list(reversed(history))



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
        
    def get_vegetation_health(self, ndvi_value: float) -> str:
        if ndvi_value < 0.2:
            return "Poor"
        elif ndvi_value < 0.4:
            return "Fair"
        elif ndvi_value < 0.6:
            return "Good"
        else:
            return "Excellent"
