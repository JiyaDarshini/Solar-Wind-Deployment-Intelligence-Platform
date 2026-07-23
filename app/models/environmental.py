"""
Pydantic schemas used across the Environmental Intelligence & Resource
Prediction module (Milestone 2).
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class SiteLocation(BaseModel):
    site_id: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    region: Optional[str] = None


# ---------- Environmental Data Collection Engine ----------

class WeatherDataPoint(BaseModel):
    date: date
    temperature_c: float
    rainfall_mm: float
    cloud_cover_pct: float
    humidity_pct: Optional[float] = None


class ClimateSummary(BaseModel):
    site_id: str
    period_start: date
    period_end: date
    avg_temperature_c: float
    total_rainfall_mm: float
    avg_cloud_cover_pct: float
    avg_solar_irradiance_kwh_m2_day: float
    avg_wind_speed_ms: float
    source: str = "NASA_POWER"


class TerrainSummary(BaseModel):
    site_id: str
    elevation_m: float
    slope_degrees: float
    aspect_degrees: float
    vegetation_index_ndvi: Optional[float] = None
    source: str = "SRTM_30m"


class EnvironmentalProfile(BaseModel):
    """Aggregated output of the Environmental Data Collection Engine
    for a single site - the object other engines (solar/wind/suitability)
    consume."""
    site: SiteLocation
    climate: ClimateSummary
    terrain: TerrainSummary
    generated_at: datetime


# ---------- Solar Potential Prediction Engine ----------

class SolarPredictionRequest(BaseModel):
    site_id: str
    latitude: float
    longitude: float
    panel_efficiency_pct: float = 20.0
    system_capacity_kw: float = 1000.0
    tilt_degrees: Optional[float] = None


class SolarMetrics(BaseModel):
    site_id: str
    annual_irradiance_kwh_m2: float
    peak_sun_hours: float
    expected_energy_output_mwh_year: float
    capacity_factor_pct: float
    performance_ratio_pct: float
    shading_loss_pct: float
    monthly_generation_mwh: list[float]


# ---------- Wind Potential Prediction Engine ----------

class WindPredictionRequest(BaseModel):
    site_id: str
    latitude: float
    longitude: float
    hub_height_m: float = 80.0
    turbine_rated_power_kw: float = 2500.0
    rotor_diameter_m: float = 100.0


class WindMetrics(BaseModel):
    site_id: str
    average_wind_speed_ms: float
    wind_power_density_w_m2: float
    turbulence_intensity_pct: float
    capacity_factor_pct: float
    expected_annual_energy_production_mwh: float
    turbine_suitability: str
    monthly_generation_mwh: list[float]


# ---------- Resource Assessment Report ----------

class ResourceAssessmentReport(BaseModel):
    site: SiteLocation
    environmental_profile: EnvironmentalProfile
    solar_metrics: Optional[SolarMetrics] = None
    wind_metrics: Optional[WindMetrics] = None
    generated_at: datetime
    report_version: str = "1.0"
