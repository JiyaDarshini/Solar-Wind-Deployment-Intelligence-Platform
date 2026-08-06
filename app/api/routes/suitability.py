"""
API routes for Module 7 (Site Suitability Intelligence Engine) and
Module 10 (Site Scoring Engine).

Mount in your main.py with:
    app.include_router(suitability_router, prefix="/api/v1/suitability", tags=["suitability"])
"""
from fastapi import APIRouter, HTTPException

from app.models.suitability import FeasibilityAssessment, SuitabilityFactorsInput
from app.services.site_suitability_service import get_site_suitability_service

router = APIRouter()


@router.post("/assess", response_model=FeasibilityAssessment)
async def assess_site_suitability(request: SuitabilityFactorsInput):
    """Runs the full suitability pipeline: environmental + GIS + solar/wind
    prediction + weighted site scoring, returning a feasibility
    assessment with the Deployment Suitability Score and category."""
    service = get_site_suitability_service()
    try:
        return await service.assess(request)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Suitability assessment failed: {exc}") from exc
