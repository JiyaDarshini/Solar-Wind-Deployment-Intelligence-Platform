"""
Module 7: Site Suitability Intelligence Engine

Orchestrates Milestone 2 engines (environmental, GIS, solar, wind) plus
the Module 10 Site Scoring Engine to produce a multi-factor feasibility
assessment: deployment feasibility, environmental impact evaluation, and
investment prioritization, per the spec's Suitability Factors:
  Renewable Resource Availability, Terrain Suitability,
  Infrastructure Accessibility, Environmental Constraints,
  Economic Viability.
"""
from typing import Optional

from app.models.environmental import (
    SiteLocation,
    SolarPredictionRequest,
    WindPredictionRequest,
)
from app.models.suitability import FeasibilityAssessment, SuitabilityCategory, SuitabilityFactorsInput
from app.services.environmental_service import get_environmental_service
from app.services.gis_service import get_gis_service
from app.services.site_scoring_service import get_site_scoring_service
from app.services.solar_prediction_service import get_solar_prediction_service
from app.services.wind_prediction_service import get_wind_prediction_service


class SiteSuitabilityService:
    async def assess(self, request: SuitabilityFactorsInput) -> FeasibilityAssessment:
        env_service = get_environmental_service()
        gis_service = get_gis_service()
        scoring_service = get_site_scoring_service()

        site = SiteLocation(site_id=request.site_id, latitude=request.latitude, longitude=request.longitude)
        profile = await env_service.build_environmental_profile(site)

        proximity = await gis_service.infrastructure_proximity_report(request.latitude, request.longitude)
        accessibility_score = gis_service.accessibility_score(proximity)

        protected_zone = proximity.get("protected_zones")
        protected_conflict = request.protected_land_conflict
        if protected_conflict is None:
            protected_conflict = bool(
                protected_zone and protected_zone.found and protected_zone.distance_km is not None
                and protected_zone.distance_km < 0.3
            )

        water_body = proximity.get("water_bodies")
        water_proximity_km = water_body.distance_km if water_body and water_body.found else None

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
            protected_land_conflict=protected_conflict,
            water_proximity_km=water_proximity_km,
        )

        notes = []
        if protected_conflict:
            notes.append("Site overlaps or borders a protected zone - deployment likely requires regulatory review.")
        if profile.terrain.slope_degrees > 15:
            notes.append(f"Steep terrain ({profile.terrain.slope_degrees}\u00b0) may increase construction cost.")
        if accessibility_score < 40:
            notes.append("Limited proximity to grid infrastructure (roads/substations/transmission lines).")
        if site_score.category in (SuitabilityCategory.EXCELLENT, SuitabilityCategory.HIGHLY_SUITABLE):
            notes.append("Strong renewable resource availability supports prioritized investment.")
        if not notes:
            notes.append("No major constraints identified in this initial assessment.")

        impact_level = "High" if protected_conflict else ("Moderate" if (water_proximity_km or 99) < 1.0 else "Low")

        feasible = site_score.category not in (SuitabilityCategory.UNSUITABLE,) and not (
            protected_conflict and site_score.overall_deployment_score < 40
        )

        return FeasibilityAssessment(
            site_id=request.site_id,
            deployment_feasible=feasible,
            feasibility_notes=notes,
            environmental_impact_level=impact_level,
            site_score=site_score,
        )


_site_suitability_service_singleton: Optional[SiteSuitabilityService] = None


def get_site_suitability_service() -> SiteSuitabilityService:
    global _site_suitability_service_singleton
    if _site_suitability_service_singleton is None:
        _site_suitability_service_singleton = SiteSuitabilityService()
    return _site_suitability_service_singleton
