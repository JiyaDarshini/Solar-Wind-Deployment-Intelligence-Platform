"""
Module 6: Wind Potential Prediction Engine

Combines the EnvironmentalProfile (wind speed, elevation) with the
trained capacity-factor model to produce the full Wind Metrics set from
the PDF spec: Average Wind Speed, Wind Power Density, Turbulence
Intensity, Capacity Factor, Expected Annual Energy Production
(+ turbine suitability classification + monthly breakdown).
"""
import logging
import math
import os
from typing import Optional

import joblib
import numpy as np

from app.core.config import get_settings
from app.models.environmental import EnvironmentalProfile, WindMetrics, WindPredictionRequest

logger = logging.getLogger(__name__)
settings = get_settings()

_SEASONAL_WIND_WEIGHTS = np.array([1.15, 1.10, 1.05, 0.95, 0.85, 0.80,
                                    0.80, 0.85, 0.95, 1.05, 1.15, 1.20])

# IEC-style wind class thresholds (simplified) for turbine suitability
_TURBINE_SUITABILITY_BANDS = [
    (8.5, "Excellent - IEC Class I site"),
    (7.0, "Highly Suitable - IEC Class II site"),
    (5.5, "Moderately Suitable - IEC Class III site"),
    (4.0, "Low Suitability - marginal wind resource"),
    (0.0, "Unsuitable - insufficient wind resource"),
]


class WindPredictionService:
    def __init__(self):
        self._model_bundle = self._load_model()

    def _load_model(self) -> Optional[dict]:
        path = settings.WIND_MODEL_PATH
        if not os.path.exists(path):
            logger.warning(
                "Wind model artifact not found at %s. Run "
                "`python -m app.ml.train_wind_model` first. Falling back "
                "to a heuristic capacity-factor estimate.",
                path,
            )
            return None
        return joblib.load(path)

    @staticmethod
    def _air_density(elevation_m: float) -> float:
        return 1.225 * math.exp(-elevation_m / 8500)

    @staticmethod
    def _estimate_turbulence_intensity(wind_speed: float) -> float:
        """Turbulence intensity tends to fall as mean wind speed rises
        (IEC-style approximation), floored/ceilinged to realistic range."""
        ti = 18 - (wind_speed - 4) * 0.6
        return float(np.clip(ti, 6, 28))

    def _predict_capacity_factor(
        self, wind_speed: float, elevation: float, turbulence: float,
        hub_height: float, rotor_diameter: float, power_density: float,
    ) -> float:
        if self._model_bundle is None:
            hub_shear_bonus = (hub_height - 60) / 80 * 6
            turbulence_penalty = max(0.0, turbulence - 12) * 0.4
            cf = (power_density / 12) * 3.2 + hub_shear_bonus - turbulence_penalty
            return float(np.clip(cf, 5, 55))

        model = self._model_bundle["model"]
        features = self._model_bundle["features"]
        row = {
            "wind_speed_ms": wind_speed,
            "elevation_m": elevation,
            "turbulence_intensity_pct": turbulence,
            "hub_height_m": hub_height,
            "rotor_diameter_m": rotor_diameter,
            "power_density_w_m2": power_density,
        }
        X = [[row[f] for f in features]]
        return float(np.clip(model.predict(X)[0], 3, 58))

    @staticmethod
    def _classify_suitability(avg_wind_speed: float) -> str:
        for threshold, label in _TURBINE_SUITABILITY_BANDS:
            if avg_wind_speed >= threshold:
                return label
        return _TURBINE_SUITABILITY_BANDS[-1][1]

    def predict(
        self, request: WindPredictionRequest, profile: EnvironmentalProfile
    ) -> WindMetrics:
        wind_speed_10m = profile.climate.avg_wind_speed_ms
        elevation = profile.terrain.elevation_m

        # Log-law wind shear extrapolation from 10m measurement height to hub height
        roughness_length = 0.05  # open plain default; refine per land-cover class
        wind_speed_hub = wind_speed_10m * (
            math.log(request.hub_height_m / roughness_length) / math.log(10 / roughness_length)
        )
        wind_speed_hub = round(max(wind_speed_10m, wind_speed_hub), 2)

        turbulence_intensity = round(self._estimate_turbulence_intensity(wind_speed_hub), 2)
        air_density = self._air_density(elevation)
        power_density = round(0.5 * air_density * wind_speed_hub ** 3, 2)

        capacity_factor = self._predict_capacity_factor(
            wind_speed_hub, elevation, turbulence_intensity,
            request.hub_height_m, request.rotor_diameter_m, power_density,
        )

        aep_mwh = round(
            request.turbine_rated_power_kw * 8760 * (capacity_factor / 100) / 1000, 2
        )

        seasonal = _SEASONAL_WIND_WEIGHTS
        monthly = [round(aep_mwh * (w / 12), 2) for w in seasonal]

        return WindMetrics(
            site_id=request.site_id,
            average_wind_speed_ms=wind_speed_hub,
            wind_power_density_w_m2=power_density,
            turbulence_intensity_pct=turbulence_intensity,
            capacity_factor_pct=round(capacity_factor, 2),
            expected_annual_energy_production_mwh=aep_mwh,
            turbine_suitability=self._classify_suitability(wind_speed_hub),
            monthly_generation_mwh=monthly,
        )


_wind_service_singleton: Optional[WindPredictionService] = None


def get_wind_prediction_service() -> WindPredictionService:
    global _wind_service_singleton
    if _wind_service_singleton is None:
        _wind_service_singleton = WindPredictionService()
    return _wind_service_singleton
