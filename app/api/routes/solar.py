"""
API routes for Module 5: Solar Potential Prediction Engine.

Mount in your main.py with:
    app.include_router(solar_router, prefix="/api/v1/solar", tags=["solar"])
"""
from fastapi import APIRouter, HTTPException

from app.models.environmental import SiteLocation, SolarMetrics, SolarPredictionRequest
from app.services.environmental_service import get_environmental_service
from app.services.solar_prediction_service import get_solar_prediction_service

router = APIRouter()


@router.post("/predict", response_model=SolarMetrics)
async def predict_solar_potential(request: SolarPredictionRequest):
    """Runs the full Solar Potential Prediction pipeline: fetches the
    environmental profile for the site, then predicts capacity factor
    and derives Annual Irradiance, Peak Sun Hours, Expected Energy
    Output, Capacity Factor, and Performance Ratio."""
    env_service = get_environmental_service()
    solar_service = get_solar_prediction_service()

    site = SiteLocation(site_id=request.site_id, latitude=request.latitude, longitude=request.longitude)
    try:
        profile = await env_service.build_environmental_profile(site)
        return solar_service.predict(request, profile)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Solar prediction failed: {exc}") from exc
