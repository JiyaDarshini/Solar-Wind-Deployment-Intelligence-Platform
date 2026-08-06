"""
API routes for Module 8: Energy Forecasting Engine.

Mount in your main.py with:
    app.include_router(forecasting_router, prefix="/api/v1/forecasting", tags=["forecasting"])
"""
from fastapi import APIRouter, HTTPException

from app.models.environmental import (
    SiteLocation,
    SolarPredictionRequest,
    WindPredictionRequest,
)
from app.models.suitability import EnergyForecast, EnergyForecastRequest
from app.services.energy_forecasting_service import get_energy_forecasting_service
from app.services.environmental_service import get_environmental_service
from app.services.solar_prediction_service import get_solar_prediction_service
from app.services.wind_prediction_service import get_wind_prediction_service

router = APIRouter()


@router.post("/forecast", response_model=EnergyForecast)
async def forecast_energy(
    request: EnergyForecastRequest,
    latitude: float,
    longitude: float,
    technology: str = "hybrid",
):
    """Runs environmental + solar/wind prediction, then projects
    generation, revenue, and grid contribution across the full project
    lifetime (default 25 years)."""
    env_service = get_environmental_service()
    forecasting_service = get_energy_forecasting_service()

    site = SiteLocation(site_id=request.site_id, latitude=latitude, longitude=longitude)
    try:
        profile = await env_service.build_environmental_profile(site)

        solar_metrics = None
        wind_metrics = None
        if technology in ("solar", "hybrid"):
            solar_service = get_solar_prediction_service()
            solar_metrics = solar_service.predict(
                SolarPredictionRequest(site_id=request.site_id, latitude=latitude, longitude=longitude), profile
            )
        if technology in ("wind", "hybrid"):
            wind_service = get_wind_prediction_service()
            wind_metrics = wind_service.predict(
                WindPredictionRequest(site_id=request.site_id, latitude=latitude, longitude=longitude), profile
            )

        return forecasting_service.forecast(request, solar_metrics, wind_metrics)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Forecasting failed: {exc}") from exc
