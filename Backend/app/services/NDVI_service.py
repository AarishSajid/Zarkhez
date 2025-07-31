import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from app.models.NDVI_model import NDVIRequest, NDVIResponse, NDVIData
from sentinelhub import SHConfig, SentinelHubRequest, DataCollection, MimeType, bbox_to_dimensions, BBox,CRS  # type: ignore
from fastapi import Response # type: ignore
from PIL import Image # type: ignore
import io,os
from app.core.config import settings
import logging 

logger = logging.getLogger(__name__)

class NDVIService:
    """Service for NDVI calculations and analysis"""

    def __init__(self):
        # Initialize Sentinel Hub config
        self.config = SHConfig()
        self.config.sh_client_id = settings.SH_CLIENT_ID
        self.config.sh_client_secret = settings.SH_CLIENT_SECRET
        # Optionally: self.config.sh_base_url = 'https://services.sentinel-hub.com'

    def calculate_ndvi(self, request: NDVIRequest) -> NDVIResponse:
        """
        Calculate NDVI using Sentinel Hub data for point or bbox.

        Returns:
            NDVIResponse with NDVI stats, bbox info, etc.
        """
        try:
            # Decide mode
            if request.north and request.south and request.east and request.west:
                mode = "bbox"
                bbox = BBox([request.west, request.south, request.east, request.north], crs=CRS.WGS84)
                logger.debug(f"Using bbox mode with bbox={bbox}")
            else:
                mode = "point"
                delta = 0.01  # ~2km area
                bbox = BBox([request.longitude - delta, request.latitude - delta,
                            request.longitude + delta, request.latitude + delta], crs=CRS.WGS84)
                logger.debug(f"Using point mode (expanded) with bbox={bbox}")

            resolution = 10  # 10 meters
            width = int((bbox.max_x - bbox.min_x) * (111320 / resolution))  # 1 degree ≈ ~111.32 km
            height = int((bbox.max_y - bbox.min_y) * (111320 / resolution))
            size = (width, height)
            logger.debug(f"Calculated size: {size} for bbox {bbox}")
            # Sentinel request
            evalscript = """
            //VERSION=3
            function setup() {
                return {
                    input: ["B04", "B08", "SCL"],
                    output: { bands: 1, sampleType: "FLOAT32" }
                };
            }
            function evaluatePixel(sample) {
                if ([3, 8, 9, 10, 11].includes(sample.SCL)) return [NaN];
                let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
                return [ndvi];
            }
            """

            request_payload = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
                        time_interval=(request.start_date, request.end_date)
                    )
                ],
                responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
                bbox=bbox,
                size=size,
                config=self.config
            )

            ndvi_data = request_payload.get_data()
            logger.debug(f"Received data type: {type(ndvi_data)}, length: {len(ndvi_data)}")
            ndvi_array = ndvi_data[0].squeeze()
            logger.debug(f"NDVI array shape: {ndvi_array.shape}")

            if np.isnan(ndvi_array).all():
                logger.debug("All values are NaN → no valid pixels")
                average_ndvi = min_ndvi = max_ndvi = None
                valid_pixels = 0
                health_distribution = {}
                ndvi_value_raw = 0.0
                vegetation_health = "Unknown"
            else:
                average_ndvi = float(np.nanmean(ndvi_array))
                min_ndvi = float(np.nanmin(ndvi_array))
                max_ndvi = float(np.nanmax(ndvi_array))
                valid_pixels = int(np.count_nonzero(~np.isnan(ndvi_array)))
                health_distribution = {
                    "Poor": int(np.sum(ndvi_array < 0.2)),
                    "Fair": int(np.sum((ndvi_array >= 0.2) & (ndvi_array < 0.4))),
                    "Good": int(np.sum((ndvi_array >= 0.4) & (ndvi_array < 0.6))),
                    "Excellent": int(np.sum(ndvi_array >= 0.6))
                }
                ndvi_value_raw = float(np.nanmedian(ndvi_array))
                vegetation_health = self.get_vegetation_health(ndvi_value_raw)

                logger.debug(f"Computed stats: avg={average_ndvi}, min={min_ndvi}, max={max_ndvi}, valid_pixels={valid_pixels}")

            return NDVIResponse(
                latitude=request.latitude,
                longitude=request.longitude,
                ndvi_value=round(ndvi_value_raw, 3) if ndvi_value_raw else 0.0,
                date=request.end_date,
                vegetation_health=vegetation_health,
                average_ndvi=round(average_ndvi, 3) if average_ndvi is not None else None,
                min_ndvi=round(min_ndvi, 3) if min_ndvi is not None else None,
                max_ndvi=round(max_ndvi, 3) if max_ndvi is not None else None,
                valid_pixel_count=valid_pixels,
                health_distribution=health_distribution,
                bbox=[bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y],
                mode=mode,
                message="NDVI analysis complete"
            )

        except Exception as e:
            logger.error(f"ERROR in calculate_ndvi: {e}")
            raise

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
            else if (ndvi < 0.1) return [215, 48, 39];
            else if (ndvi < 0.2) return [244, 109, 67];
            else if (ndvi < 0.3) return [253, 174, 97];
            else if (ndvi < 0.4) return [254, 224, 144];
            else if (ndvi < 0.5) return [173, 221, 142];    
            else if (ndvi < 0.6) return [120, 198, 121];   
            else if (ndvi < 0.7) return [49, 163, 84];      
            else return [0, 104, 55];                       

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
        Fetch NDVI history using a small bbox around the center point to get real pixels.

        :param lat: Latitude of center point
        :param lon: Longitude of center point
        :param days: Total number of days to look back
        :param step_days: Interval in days between measurements
        :return: List of dicts with date, ndvi_value, average_ndvi etc.
        """
        history = []
        today = datetime.now()
        num_points = max(1, days // step_days)
        delta = 0.005  # about ~500m around the center

        logger.debug(f"Requested NDVI history lat={lat}, lon={lon}, days={days}, step_days={step_days}")

        for i in range(num_points):
            end_date = (today - timedelta(days=i * step_days)).strftime("%Y-%m-%d")
            start_date = (today - timedelta(days=(i * step_days) + 1)).strftime("%Y-%m-%d")

            request = NDVIRequest(
                north=lat + delta,
                south=lat - delta,
                east=lon + delta,
                west=lon - delta,
                start_date=start_date,
                end_date=end_date
            )

            response = self.calculate_ndvi(request)

            logger.debug(f"Date {end_date}: valid_pixel_count={response.valid_pixel_count}, ndvi_value={response.ndvi_value}")

            if response.valid_pixel_count and response.valid_pixel_count > 0:
                history.append({
                    "date": end_date,
                    "ndvi_value": round(response.ndvi_value, 3),
                    "average_ndvi": round(response.average_ndvi, 3) if response.average_ndvi is not None else None,
                    "min_ndvi": round(response.min_ndvi, 3) if response.min_ndvi is not None else None,
                    "max_ndvi": round(response.max_ndvi, 3) if response.max_ndvi is not None else None,
                    "vegetation_health": response.vegetation_health,
                    "valid_pixel_count": response.valid_pixel_count
                })
                logger.debug(f"Added date {end_date} with NDVI={response.ndvi_value}")
            else:
                logger.debug(f"Skipped date {end_date} due to missing NDVI data (valid pixels=0)")

        # Return oldest first
        return list(reversed(history))

    def analyze_trend(self, ndvi_history: list) -> dict:
        """
        Analyze NDVI trend over time using linear regression.

        :param ndvi_history: list of dicts with 'ndvi_value' per date
        :return: dict with trend label, slope, current_avg, message
        """
        if len(ndvi_history) < 2:
            return {
                "trend": "insufficient_data",
                "slope": 0.0,
                "current_avg": None,
                "message": "Not enough data for trend analysis"
            }

        values = [item["ndvi_value"] for item in ndvi_history]
        dates = list(range(len(values)))  # e.g., [0,1,2,3...]

        # Fit linear trend: degree=1
        slope, intercept = np.polyfit(dates, values, 1)

        # Decide label based on slope
        if slope > 0.05:
            trend_label = "improving fast"
        elif slope > 0.01:
            trend_label = "slightly improving"
        elif slope < -0.05:
            trend_label = "declining fast"
        elif slope < -0.01:
            trend_label = "slightly declining"
        else:
            trend_label = "stable"

        return {
            "trend": trend_label,
            "slope": round(slope, 4),
            "current_avg": round(np.mean(values), 3),
            "message": f"Vegetation health trend: {trend_label}"
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
