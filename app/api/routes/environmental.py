"""
API routes for Module 3 (Environmental Data Collection Engine) and
Module 4 (Geographic Intelligence Engine).

Mount in your main.py with:
    app.include_router(environmental_router, prefix="/api/v1/environmental", tags=["environmental"])
"""
from fastapi import APIRouter, HTTPException

from app.models.environmental import EnvironmentalProfile, SiteLocation
from app.services.environmental_service import get_environmental_service
from app.services.gis_service import get_gis_service

router = APIRouter()


@router.post("/profile", response_model=EnvironmentalProfile)
async def get_environmental_profile(site: SiteLocation):
    """Returns aggregated weather/climate + terrain data for a site -
    the core input every downstream engine (solar, wind, suitability)
    depends on."""
    service = get_environmental_service()
    try:
        return await service.build_environmental_profile(site)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Environmental data fetch failed: {exc}") from exc


@router.get("/proximity")
async def get_infrastructure_proximity(latitude: float, longitude: float):
    """Module 4: infrastructure proximity analysis - distance to roads,
    transmission lines, substations, urban areas, protected zones, water
    bodies, agricultural land, plus a derived accessibility score."""
    gis_service = get_gis_service()
    proximity = await gis_service.infrastructure_proximity_report(latitude, longitude)
    score = gis_service.accessibility_score(proximity)
    return {
        "proximity": {k: v.model_dump() for k, v in proximity.items()},
        "accessibility_score": score,
    }
