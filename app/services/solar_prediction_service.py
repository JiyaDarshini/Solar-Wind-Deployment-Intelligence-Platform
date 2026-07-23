"""
Module 5: Solar Potential Prediction Engine

Combines the EnvironmentalProfile (irradiance, temperature, cloud cover,
terrain slope/aspect) with the trained capacity-factor model to produce
the full Solar Metrics set from the PDF spec:
  Annual Irradiance, Peak Sun Hours, Expected Energy Output,
  Capacity Factor, Performance Ratio (+ shading + monthly breakdown).
"""
import logging
import math
import os
from typing import Optional

import joblib
import numpy as np

from app.core.config import get_settings
from app.models.environmental import EnvironmentalProfile, SolarMetrics, SolarPredictionRequest

logger = logging.getLogger(__name__)
settings = get_settings()

# Rough monthly irradiance seasonality curve (relative, sums to 12).
# Northern-hemisphere-shaped; mirrored for southern hemisphere sites.
_NORTHERN_SEASONAL_WEIGHTS = np.array([0.70, 0.78, 0.95, 1.05, 1.15, 1.20,
                                       1.18, 1.12, 1.00, 0.88, 0.72, 0.67])


class SolarPredictionService:
    def __init__(self):
        self._model_bundle = self._load_model()

    def _load_model(self) -> Optional[dict]:
        path = settings.SOLAR_MODEL_PATH
        if not os.path.exists(path):
            logger.warning(
                "Solar model artifact not found at %s. Run "
                "`python -m app.ml.train_solar_model` first. Falling back "
                "to a heuristic capacity-factor estimate.",
                path,
            )
            return None
        return joblib.load(path)

    def _predict_capacity_factor(
        self, irradiance: float, temperature: float, cloud_cover: float,
        slope: float, aspect_penalty: float, panel_efficiency: float,
    ) -> float:
        if self._model_bundle is None:
            # Heuristic fallback mirroring the synthetic training formula
            cf = (
                (irradiance / 8.0) * 32
                - (cloud_cover / 100) * 6
                - (slope / 45) * 3
                - aspect_penalty * 4
                + (panel_efficiency - 18) * 0.6
                - max(temperature - 25, 0) * 0.08
            )
            return float(np.clip(cf, 5, 35))

        model = self._model_bundle["model"]
        features = self._model_bundle["features"]
        row = {
            "irradiance_kwh_m2_day": irradiance,
            "temperature_c": temperature,
            "cloud_cover_pct": cloud_cover,
            "slope_degrees": slope,
            "aspect_penalty": aspect_penalty,
            "panel_efficiency_pct": panel_efficiency,
        }
        X = [[row[f] for f in features]]
        return float(np.clip(model.predict(X)[0], 3, 38))

    @staticmethod
    def _aspect_to_penalty(aspect_degrees: float, latitude: float) -> float:
        """0 = ideal orientation (equator-facing), 1 = worst (pole-facing)."""
        ideal_aspect = 180.0 if latitude >= 0 else 0.0
        diff = abs((aspect_degrees - ideal_aspect + 180) % 360 - 180)
        return round(diff / 180, 3)

    def predict(
        self, request: SolarPredictionRequest, profile: EnvironmentalProfile
    ) -> SolarMetrics:
        irradiance = profile.climate.avg_solar_irradiance_kwh_m2_day
        temperature = profile.climate.avg_temperature_c
        cloud_cover = profile.climate.avg_cloud_cover_pct
        slope = profile.terrain.slope_degrees
        aspect_penalty = self._aspect_to_penalty(profile.terrain.aspect_degrees, request.latitude)

        capacity_factor = self._predict_capacity_factor(
            irradiance, temperature, cloud_cover, slope, aspect_penalty, request.panel_efficiency_pct
        )

        annual_irradiance = round(irradiance * 365, 1)
        peak_sun_hours = round(irradiance, 2)  # kWh/m2/day numerically equals PSH

        # Expected annual energy (MWh) = capacity * hours/year * CF
        expected_energy_mwh = round(
            request.system_capacity_kw * 8760 * (capacity_factor / 100) / 1000, 2
        )

        # Performance ratio: derates capacity factor's "theoretical" ceiling
        # by temperature, soiling, and inverter/wiring losses.
        temp_derate = max(0.0, (temperature - 25)) * 0.004  # ~0.4%/degC above 25C
        soiling_and_system_losses = 0.08
        performance_ratio = round((1 - temp_derate - soiling_and_system_losses) * 100, 2)
        performance_ratio = max(60.0, min(90.0, performance_ratio))

        shading_loss_pct = round(min(25.0, slope * 0.8), 2)

        seasonal = _NORTHERN_SEASONAL_WEIGHTS if request.latitude >= 0 else _NORTHERN_SEASONAL_WEIGHTS[::-1]
        monthly = [round(expected_energy_mwh * (w / 12), 2) for w in seasonal]

        return SolarMetrics(
            site_id=request.site_id,
            annual_irradiance_kwh_m2=annual_irradiance,
            peak_sun_hours=peak_sun_hours,
            expected_energy_output_mwh_year=expected_energy_mwh,
            capacity_factor_pct=round(capacity_factor, 2),
            performance_ratio_pct=performance_ratio,
            shading_loss_pct=shading_loss_pct,
            monthly_generation_mwh=monthly,
        )


_solar_service_singleton: Optional[SolarPredictionService] = None


def get_solar_prediction_service() -> SolarPredictionService:
    global _solar_service_singleton
    if _solar_service_singleton is None:
        _solar_service_singleton = SolarPredictionService()
    return _solar_service_singleton
