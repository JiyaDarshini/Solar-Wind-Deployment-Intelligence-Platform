"""
API routes for Module 6: Wind Potential Prediction Engine.

Mount in your main.py with:
    app.include_router(wind_router, prefix="/api/v1/wind", tags=["wind"])
"""
from fastapi import APIRouter, HTTPException

from app.models.environmental import SiteLocation, WindMetrics, WindPredictionRequest
from app.services.environmental_service import get_environmental_service
from app.services.wind_prediction_service import get_wind_prediction_service

router = APIRouter()


@router.post("/predict", response_model=WindMetrics)
async def predict_wind_potential(request: WindPredictionRequest):
    """Runs the full Wind Potential Prediction pipeline: fetches the
    environmental profile for the site, extrapolates wind speed to hub
    height, then predicts capacity factor and derives Wind Power
    Density, Turbulence Intensity, Capacity Factor, and Expected Annual
    Energy Production."""
    env_service = get_environmental_service()
    wind_service = get_wind_prediction_service()

    site = SiteLocation(site_id=request.site_id, latitude=request.latitude, longitude=request.longitude)
    try:
        profile = await env_service.build_environmental_profile(site)
        return wind_service.predict(request, profile)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Wind prediction failed: {exc}") from exc
