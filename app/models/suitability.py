"""
Pydantic schemas for Milestone 3 - Site Intelligence & Optimization
(Modules 7-10: Site Suitability, Energy Forecasting, Deployment
Optimization, Site Scoring).

These build on top of the Milestone 2 EnvironmentalProfile / SolarMetrics
/ WindMetrics objects (app.models.environmental) rather than duplicating
them.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Module 10: Site Scoring Engine ----------

class SuitabilityCategory(str, Enum):
    EXCELLENT = "Excellent"
    HIGHLY_SUITABLE = "Highly Suitable"
    MODERATELY_SUITABLE = "Moderately Suitable"
    LOW_SUITABILITY = "Low Suitability"
    UNSUITABLE = "Unsuitable"


class ScoreBreakdown(BaseModel):
    renewable_resource_availability: float = Field(..., ge=0, le=100)
    geographic_suitability: float = Field(..., ge=0, le=100)
    infrastructure_accessibility: float = Field(..., ge=0, le=100)
    environmental_impact: float = Field(..., ge=0, le=100)
    economic_feasibility: float = Field(..., ge=0, le=100)


class SiteScore(BaseModel):
    site_id: str
    solar_suitability_score: Optional[float] = None
    wind_suitability_score: Optional[float] = None
    infrastructure_score: float
    investment_score: float
    overall_deployment_score: float = Field(..., ge=0, le=100)
    category: SuitabilityCategory
    breakdown: ScoreBreakdown
    generated_at: datetime


# ---------- Module 7: Site Suitability Intelligence Engine ----------

class SuitabilityFactorsInput(BaseModel):
    """Raw inputs the suitability engine needs - most are pulled
    automatically from Milestone 2 engines, but callers may override any
    of them (e.g. a GIS analyst manually correcting a land-ownership
    constraint flag)."""
    site_id: str
    latitude: float
    longitude: float
    technology: str = Field("hybrid", pattern="^(solar|wind|hybrid)$")
    land_cost_usd_per_hectare: Optional[float] = None
    grid_connection_cost_estimate_usd: Optional[float] = None
    protected_land_conflict: Optional[bool] = None


class FeasibilityAssessment(BaseModel):
    site_id: str
    deployment_feasible: bool
    feasibility_notes: list[str]
    environmental_impact_level: str  # Low / Moderate / High
    investment_priority_rank: Optional[int] = None
    site_score: SiteScore


# ---------- Module 8: Energy Forecasting Engine ----------

class EnergyForecastRequest(BaseModel):
    site_id: str
    project_lifetime_years: int = 25
    electricity_price_usd_per_mwh: float = 55.0
    annual_degradation_pct: float = 0.5  # panel/turbine output decline per year
    grid_capacity_mw: Optional[float] = None


class YearlyForecastPoint(BaseModel):
    year: int
    generation_mwh: float
    revenue_usd: float
    grid_contribution_pct: Optional[float] = None


class EnergyForecast(BaseModel):
    site_id: str
    technology: str
    year_1_generation_mwh: float
    lifetime_generation_mwh: float
    lifetime_revenue_usd: float
    seasonal_generation_mwh: list[float]  # 12 months, year-1
    yearly_projection: list[YearlyForecastPoint]
    generated_at: datetime


# ---------- Module 9: Deployment Optimization Engine ----------

class TechnologyRecommendation(BaseModel):
    recommended_technology: str  # solar / wind / hybrid
    rationale: str
    solar_capacity_mw: float
    wind_capacity_mw: float
    hybrid_ratio_solar_pct: Optional[float] = None


class ExpansionPlanStep(BaseModel):
    phase: int
    description: str
    capacity_mw: float
    trigger_condition: str


class DeploymentOptimizationResult(BaseModel):
    site_id: str
    technology_recommendation: TechnologyRecommendation
    optimal_capacity_mw: float
    expansion_plan: list[ExpansionPlanStep]
    optimization_notes: list[str]
    generated_at: datetime


# ---------- Ranked recommendation across multiple sites ----------

class RankedSiteRecommendation(BaseModel):
    site_id: str
    overall_deployment_score: float
    category: SuitabilityCategory
    recommended_technology: str
    lifetime_revenue_usd: Optional[float] = None
    rank: int
