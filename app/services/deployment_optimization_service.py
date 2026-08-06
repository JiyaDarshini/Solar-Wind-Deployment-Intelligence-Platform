"""
Module 9: Deployment Optimization Engine

Per spec: Optimal location recommendation, Technology selection,
Capacity planning, Hybrid solar-wind recommendations, Expansion
planning.

Uses the Site Score + solar/wind metrics to decide which technology (or
hybrid mix) best fits a site, sizes an initial capacity, and lays out a
phased expansion plan.
"""
from datetime import datetime
from typing import Optional

from app.models.environmental import SolarMetrics, WindMetrics
from app.models.suitability import (
    DeploymentOptimizationResult,
    ExpansionPlanStep,
    SiteScore,
    TechnologyRecommendation,
)

SOLAR_MW_PER_HECTARE = 0.5
WIND_MW_PER_TURBINE = 2.5


class DeploymentOptimizationService:
    @staticmethod
    def _select_technology(
        solar_metrics: Optional[SolarMetrics], wind_metrics: Optional[WindMetrics]
    ) -> TechnologyRecommendation:
        solar_cf = solar_metrics.capacity_factor_pct if solar_metrics else None
        wind_cf = wind_metrics.capacity_factor_pct if wind_metrics else None

        if solar_cf is not None and wind_cf is not None:
            solar_norm = solar_cf / 35
            wind_norm = wind_cf / 55
            diff = abs(solar_norm - wind_norm)

            if diff < 0.15:
                solar_share = round(solar_norm / (solar_norm + wind_norm) * 100, 1)
                return TechnologyRecommendation(
                    recommended_technology="hybrid",
                    rationale=(
                        f"Solar (CF {solar_cf}%) and wind (CF {wind_cf}%) resources are comparably "
                        "strong at this site - a hybrid plant diversifies generation across day/night "
                        "and seasonal cycles."
                    ),
                    solar_capacity_mw=0.0,
                    wind_capacity_mw=0.0,
                    hybrid_ratio_solar_pct=solar_share,
                )
            elif solar_norm > wind_norm:
                return TechnologyRecommendation(
                    recommended_technology="solar",
                    rationale=f"Solar capacity factor ({solar_cf}%) significantly outperforms wind ({wind_cf}%) at this site.",
                    solar_capacity_mw=0.0,
                    wind_capacity_mw=0.0,
                )
            else:
                return TechnologyRecommendation(
                    recommended_technology="wind",
                    rationale=f"Wind capacity factor ({wind_cf}%) significantly outperforms solar ({solar_cf}%) at this site.",
                    solar_capacity_mw=0.0,
                    wind_capacity_mw=0.0,
                )
        elif solar_cf is not None:
            return TechnologyRecommendation(
                recommended_technology="solar",
                rationale=f"Only solar resource data available (CF {solar_cf}%).",
                solar_capacity_mw=0.0,
                wind_capacity_mw=0.0,
            )
        else:
            return TechnologyRecommendation(
                recommended_technology="wind",
                rationale=f"Only wind resource data available (CF {wind_cf}%).",
                solar_capacity_mw=0.0,
                wind_capacity_mw=0.0,
            )

    @staticmethod
    def _size_capacity(
        land_area_hectares: float, technology: str, hybrid_ratio_solar_pct: Optional[float]
    ) -> tuple[float, float, float]:
        if technology == "solar":
            solar_mw = round(land_area_hectares * SOLAR_MW_PER_HECTARE, 2)
            return solar_mw, 0.0, solar_mw
        if technology == "wind":
            turbines = max(1, int(land_area_hectares / 4))
            wind_mw = round(turbines * WIND_MW_PER_TURBINE, 2)
            return 0.0, wind_mw, wind_mw

        ratio = (hybrid_ratio_solar_pct or 50.0) / 100
        solar_land = land_area_hectares * ratio
        wind_land = land_area_hectares * (1 - ratio)
        solar_mw = round(solar_land * SOLAR_MW_PER_HECTARE, 2)
        turbines = max(1, int(wind_land / 4))
        wind_mw = round(turbines * WIND_MW_PER_TURBINE, 2)
        return solar_mw, wind_mw, round(solar_mw + wind_mw, 2)

    @staticmethod
    def _build_expansion_plan(total_capacity_mw: float, site_score: SiteScore) -> list[ExpansionPlanStep]:
        phase1 = round(total_capacity_mw * 0.4, 2)
        phase2 = round(total_capacity_mw * 0.35, 2)
        phase3 = round(total_capacity_mw - phase1 - phase2, 2)

        return [
            ExpansionPlanStep(
                phase=1,
                description="Initial pilot deployment to validate resource predictions against real generation data.",
                capacity_mw=phase1,
                trigger_condition="Project approval and financing secured",
            ),
            ExpansionPlanStep(
                phase=2,
                description="Scale-up deployment once Phase 1 performance is validated.",
                capacity_mw=phase2,
                trigger_condition="Phase 1 capacity factor within 10% of forecast for 12 consecutive months",
            ),
            ExpansionPlanStep(
                phase=3,
                description="Full build-out to planned site capacity.",
                capacity_mw=phase3,
                trigger_condition=(
                    "Grid interconnection upgrade complete"
                    if site_score.infrastructure_score < 60
                    else "Phase 2 complete and offtake agreements confirmed"
                ),
            ),
        ]

    def optimize(
        self,
        site_id: str,
        land_area_hectares: float,
        site_score: SiteScore,
        solar_metrics: Optional[SolarMetrics] = None,
        wind_metrics: Optional[WindMetrics] = None,
    ) -> DeploymentOptimizationResult:
        tech_rec = self._select_technology(solar_metrics, wind_metrics)
        solar_mw, wind_mw, total_mw = self._size_capacity(
            land_area_hectares, tech_rec.recommended_technology, tech_rec.hybrid_ratio_solar_pct
        )
        tech_rec.solar_capacity_mw = solar_mw
        tech_rec.wind_capacity_mw = wind_mw

        expansion_plan = self._build_expansion_plan(total_mw, site_score)

        notes = []
        if site_score.overall_deployment_score < 50:
            notes.append("Overall suitability score is below 'Moderately Suitable' - consider a smaller pilot phase or alternate site.")
        if land_area_hectares < 2:
            notes.append("Small land area limits total deployable capacity; expansion may require adjacent land acquisition.")
        if not notes:
            notes.append("Site supports the full phased capacity plan as sized.")

        return DeploymentOptimizationResult(
            site_id=site_id,
            technology_recommendation=tech_rec,
            optimal_capacity_mw=total_mw,
            expansion_plan=expansion_plan,
            optimization_notes=notes,
            generated_at=datetime.utcnow(),
        )


_deployment_optimization_service_singleton: Optional[DeploymentOptimizationService] = None


def get_deployment_optimization_service() -> DeploymentOptimizationService:
    global _deployment_optimization_service_singleton
    if _deployment_optimization_service_singleton is None:
        _deployment_optimization_service_singleton = DeploymentOptimizationService()
    return _deployment_optimization_service_singleton
