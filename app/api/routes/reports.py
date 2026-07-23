"""
API routes for resource assessment report generation
(feeds Module 13: Reports & Export System).

Mount in your main.py with:
    app.include_router(reports_router, prefix="/api/v1/reports", tags=["reports"])
"""
from fastapi import APIRouter, HTTPException

from app.models.environmental import (
    ResourceAssessmentReport,
    SiteLocation,
    SolarPredictionRequest,
    WindPredictionRequest,
)
from app.services.environmental_service import get_environmental_service
from app.services.report_service import get_report_service
from app.services.solar_prediction_service import get_solar_prediction_service
from app.services.wind_prediction_service import get_wind_prediction_service

router = APIRouter()


@router.post("/generate/{site_id}", response_model=ResourceAssessmentReport)
async def generate_resource_assessment_report(
    site_id: str,
    latitude: float,
    longitude: float,
    include_solar: bool = True,
    include_wind: bool = True,
):
    """Runs the environmental + solar + wind engines together and stores
    a combined resource assessment report in MongoDB, keyed by site_id."""
    env_service = get_environmental_service()
    report_service = get_report_service()

    site = SiteLocation(site_id=site_id, latitude=latitude, longitude=longitude)
    try:
        profile = await env_service.build_environmental_profile(site)

        solar_metrics = None
        if include_solar:
            solar_service = get_solar_prediction_service()
            solar_metrics = solar_service.predict(
                SolarPredictionRequest(site_id=site_id, latitude=latitude, longitude=longitude), profile
            )

        wind_metrics = None
        if include_wind:
            wind_service = get_wind_prediction_service()
            wind_metrics = wind_service.predict(
                WindPredictionRequest(site_id=site_id, latitude=latitude, longitude=longitude), profile
            )

        return await report_service.build_report(site, profile, solar_metrics, wind_metrics)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Report generation failed: {exc}") from exc


@router.get("/{site_id}")
async def get_resource_assessment_report(site_id: str):
    report_service = get_report_service()
    report = await report_service.get_report(site_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report found for this site_id")
    return report


@router.get("/")
async def list_resource_assessment_reports(limit: int = 50):
    report_service = get_report_service()
    return await report_service.list_reports(limit=limit)
