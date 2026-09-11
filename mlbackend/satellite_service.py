import numpy as np
import datetime
from typing import Dict, List, Optional
from sentinelhub import (
    SentinelHubRequest,
    SentinelHubSession,
    MimeType,
    DataCollection,
    BBox,
    CRS,
    SHConfig,
)
try:
    from .config import settings
except ImportError:
    from config import settings


class SatelliteService:
    def __init__(self):
        self.config = SHConfig()
        self.config.sh_client_id = getattr(settings, "SENTINEL_CLIENT_ID", "")
        self.config.sh_client_secret = getattr(settings, "SENTINEL_CLIENT_SECRET", "")
        
    def _is_configured(self) -> bool:
        client_id = getattr(settings, "SENTINEL_CLIENT_ID", "")
        client_secret = getattr(settings, "SENTINEL_CLIENT_SECRET", "")
        return bool(client_id and client_secret)

    def get_crop_indices(self, lat: float, lon: float, buffer: float = 0.005) -> Dict:
        """
        Fetches Sentinel-2 data and calculates vegetation indices: NDVI, EVI.
        If credentials are missing, returns simulated data with a warning.
        """
        if not self._is_configured():
            return self._simulate_satellite_data(lat, lon)

        try:
            session = SentinelHubSession(config=self.config)
            
            # Define Bounding Box (approx. square field around point)
            bbox = BBox(bbox=[lon - buffer, lat - buffer, lon + buffer, lat + buffer], crs=CRS.WGS84)
            
            # Evalscript to calculate NDVI and EVI directly on Sentinel Hub servers
            evalscript = """
            //VERSION=3
            function setup() {
              return {
                input: ["B02", "B04", "B08"],
                output: { id: "default", bands: 2, sampleType: "FLOAT32" }
              };
            }
            function evaluatePixel(sample) {
              let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
              // EVI = 2.5 * ((B08 - B04) / (B08 + 6 * B04 - 7.5 * B02 + 1))
              let evi = 2.5 * ((sample.B08 - sample.B04) / (sample.B08 + 6.0 * sample.B04 - 7.5 * sample.B02 + 1.0));
              return [ndvi, evi];
            }
            """
            
            request = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
                        time_interval=(
                            (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                            datetime.datetime.now().strftime('%Y-%m-%d')
                        )
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response('default', MimeType.TIFF)
                ],
                bbox=bbox,
                size=[100, 100],  # 100x100 pixels grid
                config=self.config
            )

            # Execution
            data = request.get_data()[0]
            
            # Calculate average indices over the 100x100 grid (masking NaNs)
            ndvi_mean = np.nanmean(data[:, :, 0])
            evi_mean = np.nanmean(data[:, :, 1])
            
            return {
                "health_score": int(ndvi_mean * 100),
                "indices": {
                    "ndvi": round(float(ndvi_mean), 3),
                    "evi": round(float(evi_mean), 3),
                    "savi": round(float(ndvi_mean * 0.95), 3), # Estimated
                },
                "data_source": "Sentinel-2 L2A (Live Query)",
                "status": "LIVE"
            }

        except Exception as e:
            print(f"Satellite API Error: {e}")
            return self._simulate_satellite_data(lat, lon, error=str(e))

    def _simulate_satellite_data(self, lat: float, lon: float, error: Optional[str] = None) -> Dict:
        """Simulated fallback data when API is unavailable."""
        import random
        base_ndvi = 0.65 + random.uniform(-0.15, 0.2)
        return {
            "health_score": int(base_ndvi * 100),
            "indices": {
                "ndvi": round(base_ndvi, 3),
                "evi": round(base_ndvi * 0.85, 3),
                "savi": round(base_ndvi * 0.92, 3),
            },
            "data_source": "Sentinel-2 (Simulated — Missing API Keys)",
            "status": "SIMULATED",
            "msg": f"Configuration error: {error}" if error else "Connect Sentinel-Hub keys in .env"
        }

satellite_service = SatelliteService()
