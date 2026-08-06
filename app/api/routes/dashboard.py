"""
API routes feeding Module 11's Energy Planner Dashboard (recommended
deployment sites, ranked by suitability score). Full dashboard UI is a
frontend concern - this endpoint provides the ranked data it needs.

Mount in your main.py with:
    app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])
"""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.suitability import RankedSiteRecommendation, SuitabilityFactorsInput
from app.services.deployment_optimization_service import get_deployment_optimization_service
from app.services.energy_forecasting_service import get_energy_forecasting_service
from app.services.environmental_service import get_environmental_service
from app.services.gis_service import get_gis_service
from app.services.site_scoring_service import get_site_scoring_service
from app.services.site_suitability_service import get_site_suitability_service
from app.services.solar_prediction_service import get_solar_prediction_service
from app.services.wind_prediction_service import get_wind_prediction_service
from app.models.environmental import SiteLocation, SolarPredictionRequest, WindPredictionRequest
from app.models.suitability import EnergyForecastRequest

router = APIRouter()


class SiteCandidate(BaseModel):
    site_id: str
    latitude: float
    longitude: float
    technology: str = "hybrid"


class RankSitesRequest(BaseModel):
    candidates: list[SiteCandidate]


@router.post("/rank-sites", response_model=list[RankedSiteRecommendation])
async def rank_sites(request: RankSitesRequest):
    """Runs the suitability assessment across multiple candidate sites in
    parallel and returns them ranked best-to-worst by overall deployment
    score - this is what backs the Energy Planner Dashboard's
    'Recommended deployment sites' panel."""
    suitability_service = get_site_suitability_service()

    async def _assess_one(candidate: SiteCandidate):
        result = await suitability_service.assess(
            SuitabilityFactorsInput(
                site_id=candidate.site_id,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                technology=candidate.technology,
            )
        )
        return candidate, result

    try:
        results = await asyncio.gather(*[_assess_one(c) for c in request.candidates])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Site ranking failed: {exc}") from exc

    ranked = sorted(results, key=lambda pair: pair[1].site_score.overall_deployment_score, reverse=True)

    recommendations = []
    for rank, (candidate, assessment) in enumerate(ranked, start=1):
        recommendations.append(
            RankedSiteRecommendation(
                site_id=candidate.site_id,
                overall_deployment_score=assessment.site_score.overall_deployment_score,
                category=assessment.site_score.category,
                recommended_technology=candidate.technology,
                rank=rank,
            )
        )
    return recommendations
