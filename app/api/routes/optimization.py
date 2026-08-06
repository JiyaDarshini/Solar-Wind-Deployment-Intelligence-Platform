"""
API routes for Module 9: Deployment Optimization Engine.

Mount in your main.py with:
    app.include_router(optimization_router, prefix="/api/v1/optimization", tags=["optimization"])
"""
from fastapi import APIRouter, HTTPException

from app.models.environmental import (
    SiteLocation,
    SolarPredictionRequest,
    WindPredictionRequest,
)
from app.models.suitability import (
    DeploymentOptimizationResult,
    SuitabilityFactorsInput,
)
from app.services.deployment_optimization_service import get_deployment_optimization_service
from app.services.environmental_service import get_environmental_service
from app.services.gis_service import get_gis_service
from app.services.site_scoring_service import get_site_scoring_service
from app.services.solar_prediction_service import get_solar_prediction_service
from app.services.wind_prediction_service import get_wind_prediction_service

router = APIRouter()


@router.post("/optimize", response_model=DeploymentOptimizationResult)
async def optimize_deployment(
    request: SuitabilityFactorsInput,
    land_area_hectares: float,
):
    """Runs the full pipeline (environmental + GIS + solar/wind +
    scoring) then produces a technology recommendation, sized capacity,
    and phased expansion plan for the site."""
    env_service = get_environmental_service()
    gis_service = get_gis_service()
    scoring_service = get_site_scoring_service()
    optimization_service = get_deployment_optimization_service()

    site = SiteLocation(site_id=request.site_id, latitude=request.latitude, longitude=request.longitude)
    try:
        profile = await env_service.build_environmental_profile(site)
        proximity = await gis_service.infrastructure_proximity_report(request.latitude, request.longitude)
        accessibility_score = gis_service.accessibility_score(proximity)

        solar_metrics = None
        wind_metrics = None
        if request.technology in ("solar", "hybrid"):
            solar_service = get_solar_prediction_service()
            solar_metrics = solar_service.predict(
                SolarPredictionRequest(site_id=request.site_id, latitude=request.latitude, longitude=request.longitude),
                profile,
            )
        if request.technology in ("wind", "hybrid"):
            wind_service = get_wind_prediction_service()
            wind_metrics = wind_service.predict(
                WindPredictionRequest(site_id=request.site_id, latitude=request.latitude, longitude=request.longitude),
                profile,
            )

        site_score = scoring_service.score_site(
            site_id=request.site_id,
            slope_degrees=profile.terrain.slope_degrees,
            accessibility_score=accessibility_score,
            solar_metrics=solar_metrics,
            wind_metrics=wind_metrics,
            land_cost_usd_per_hectare=request.land_cost_usd_per_hectare,
            grid_connection_cost_estimate_usd=request.grid_connection_cost_estimate_usd,
            protected_land_conflict=bool(request.protected_land_conflict),
        )

        return optimization_service.optimize(
            site_id=request.site_id,
            land_area_hectares=land_area_hectares,
            site_score=site_score,
            solar_metrics=solar_metrics,
            wind_metrics=wind_metrics,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Deployment optimization failed: {exc}") from exc
