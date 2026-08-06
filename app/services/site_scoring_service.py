"""
Module 10: Site Scoring Engine

Implements the exact weighted scoring model from the project spec:

    Deployment Suitability Score =
        Renewable Resource Availability (35%)
      + Geographic Suitability          (25%)
      + Infrastructure Accessibility    (15%)
      + Environmental Impact            (15%)
      + Economic Feasibility            (10%)

Each sub-factor is normalized to a 0-100 scale before weighting. Final
score is bucketed into the five Suitability Categories from the spec.
"""
from datetime import datetime
from typing import Optional

import numpy as np

from app.models.environmental import SolarMetrics, WindMetrics
from app.models.suitability import ScoreBreakdown, SiteScore, SuitabilityCategory

_WEIGHTS = {
    "renewable_resource_availability": 0.35,
    "geographic_suitability": 0.25,
    "infrastructure_accessibility": 0.15,
    "environmental_impact": 0.15,
    "economic_feasibility": 0.10,
}

_CATEGORY_THRESHOLDS = [
    (85, SuitabilityCategory.EXCELLENT),
    (70, SuitabilityCategory.HIGHLY_SUITABLE),
    (50, SuitabilityCategory.MODERATELY_SUITABLE),
    (30, SuitabilityCategory.LOW_SUITABILITY),
    (0, SuitabilityCategory.UNSUITABLE),
]


class SiteScoringService:
    @staticmethod
    def _resource_availability_score(
        solar_metrics: Optional[SolarMetrics], wind_metrics: Optional[WindMetrics]
    ) -> tuple[float, Optional[float], Optional[float]]:
        """0-100 score from whichever capacity factors are available.
        Solar CF ceiling ~35%, wind CF ceiling ~55% per the ML training
        ranges, so each is normalized against its own realistic ceiling."""
        solar_score = None
        wind_score = None
        if solar_metrics:
            solar_score = round(np.clip(solar_metrics.capacity_factor_pct / 35 * 100, 0, 100), 2)
        if wind_metrics:
            wind_score = round(np.clip(wind_metrics.capacity_factor_pct / 55 * 100, 0, 100), 2)

        candidates = [s for s in (solar_score, wind_score) if s is not None]
        combined = float(np.mean(candidates)) if candidates else 0.0
        return round(combined, 2), solar_score, wind_score

    @staticmethod
    def _geographic_suitability_score(slope_degrees: float, protected_land_conflict: bool) -> float:
        if protected_land_conflict:
            return 5.0
        slope_score = max(0.0, 100 - slope_degrees * 4.5)
        return round(min(100.0, slope_score), 2)

    @staticmethod
    def _economic_feasibility_score(
        land_cost_usd_per_hectare: Optional[float], grid_connection_cost_estimate_usd: Optional[float]
    ) -> float:
        if land_cost_usd_per_hectare is None and grid_connection_cost_estimate_usd is None:
            return 60.0
        land_score = 100.0
        if land_cost_usd_per_hectare is not None:
            land_score = max(0.0, 100 - (land_cost_usd_per_hectare / 20000) * 100)
        grid_score = 100.0
        if grid_connection_cost_estimate_usd is not None:
            grid_score = max(0.0, 100 - (grid_connection_cost_estimate_usd / 2_000_000) * 100)
        return round((land_score + grid_score) / 2, 2)

    @staticmethod
    def _environmental_impact_score(protected_land_conflict: bool, water_proximity_km: Optional[float]) -> float:
        score = 100.0
        if protected_land_conflict:
            score -= 60
        if water_proximity_km is not None and water_proximity_km < 0.5:
            score -= 20
        return round(max(0.0, score), 2)

    @staticmethod
    def _categorize(overall_score: float) -> SuitabilityCategory:
        for threshold, category in _CATEGORY_THRESHOLDS:
            if overall_score >= threshold:
                return category
        return SuitabilityCategory.UNSUITABLE

    def score_site(
        self,
        site_id: str,
        slope_degrees: float,
        accessibility_score: float,
        solar_metrics: Optional[SolarMetrics] = None,
        wind_metrics: Optional[WindMetrics] = None,
        land_cost_usd_per_hectare: Optional[float] = None,
        grid_connection_cost_estimate_usd: Optional[float] = None,
        protected_land_conflict: bool = False,
        water_proximity_km: Optional[float] = None,
    ) -> SiteScore:
        resource_score, solar_score, wind_score = self._resource_availability_score(solar_metrics, wind_metrics)
        geo_score = self._geographic_suitability_score(slope_degrees, protected_land_conflict)
        infra_score = round(accessibility_score, 2)
        env_score = self._environmental_impact_score(protected_land_conflict, water_proximity_km)
        econ_score = self._economic_feasibility_score(land_cost_usd_per_hectare, grid_connection_cost_estimate_usd)

        breakdown = ScoreBreakdown(
            renewable_resource_availability=resource_score,
            geographic_suitability=geo_score,
            infrastructure_accessibility=infra_score,
            environmental_impact=env_score,
            economic_feasibility=econ_score,
        )

        overall = (
            resource_score * _WEIGHTS["renewable_resource_availability"]
            + geo_score * _WEIGHTS["geographic_suitability"]
            + infra_score * _WEIGHTS["infrastructure_accessibility"]
            + env_score * _WEIGHTS["environmental_impact"]
            + econ_score * _WEIGHTS["economic_feasibility"]
        )
        overall = round(min(100.0, max(0.0, overall)), 2)

        investment_score = round(overall * 0.6 + econ_score * 0.4, 2)

        return SiteScore(
            site_id=site_id,
            solar_suitability_score=solar_score,
            wind_suitability_score=wind_score,
            infrastructure_score=infra_score,
            investment_score=investment_score,
            overall_deployment_score=overall,
            category=self._categorize(overall),
            breakdown=breakdown,
            generated_at=datetime.utcnow(),
        )


_site_scoring_service_singleton: Optional[SiteScoringService] = None


def get_site_scoring_service() -> SiteScoringService:
    global _site_scoring_service_singleton
    if _site_scoring_service_singleton is None:
        _site_scoring_service_singleton = SiteScoringService()
    return _site_scoring_service_singleton
