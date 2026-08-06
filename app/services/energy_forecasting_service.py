"""
Module 8: Energy Forecasting Engine

Produces long-term energy production forecasts, revenue prediction, and
grid contribution forecasting from Milestone 2's solar/wind metrics -
per spec: Energy production forecasting, Seasonal generation prediction,
Long-term energy estimation, Grid contribution forecasting, Revenue
prediction.
"""
from datetime import datetime
from typing import Optional

from app.models.environmental import SolarMetrics, WindMetrics
from app.models.suitability import EnergyForecast, EnergyForecastRequest, YearlyForecastPoint


class EnergyForecastingService:
    @staticmethod
    def _combine_monthly(solar: Optional[SolarMetrics], wind: Optional[WindMetrics]) -> list[float]:
        solar_monthly = solar.monthly_generation_mwh if solar else [0.0] * 12
        wind_monthly = wind.monthly_generation_mwh if wind else [0.0] * 12
        return [round(s + w, 2) for s, w in zip(solar_monthly, wind_monthly)]

    def forecast(
        self,
        request: EnergyForecastRequest,
        solar_metrics: Optional[SolarMetrics] = None,
        wind_metrics: Optional[WindMetrics] = None,
    ) -> EnergyForecast:
        if not solar_metrics and not wind_metrics:
            raise ValueError("At least one of solar_metrics or wind_metrics is required")

        technology = (
            "hybrid" if solar_metrics and wind_metrics else ("solar" if solar_metrics else "wind")
        )

        year1_solar = solar_metrics.expected_energy_output_mwh_year if solar_metrics else 0.0
        year1_wind = wind_metrics.expected_annual_energy_production_mwh if wind_metrics else 0.0
        year1_generation = round(year1_solar + year1_wind, 2)

        seasonal_monthly = self._combine_monthly(solar_metrics, wind_metrics)

        degradation = request.annual_degradation_pct / 100
        yearly_projection: list[YearlyForecastPoint] = []
        lifetime_generation = 0.0
        lifetime_revenue = 0.0

        for year in range(1, request.project_lifetime_years + 1):
            factor = (1 - degradation) ** (year - 1)
            gen = round(year1_generation * factor, 2)
            revenue = round(gen * request.electricity_price_usd_per_mwh, 2)
            grid_contribution = None
            if request.grid_capacity_mw and request.grid_capacity_mw > 0:
                grid_contribution = round(
                    min(100.0, (gen / (request.grid_capacity_mw * 8760)) * 100), 3
                )
            yearly_projection.append(
                YearlyForecastPoint(year=year, generation_mwh=gen, revenue_usd=revenue, grid_contribution_pct=grid_contribution)
            )
            lifetime_generation += gen
            lifetime_revenue += revenue

        return EnergyForecast(
            site_id=request.site_id,
            technology=technology,
            year_1_generation_mwh=year1_generation,
            lifetime_generation_mwh=round(lifetime_generation, 2),
            lifetime_revenue_usd=round(lifetime_revenue, 2),
            seasonal_generation_mwh=seasonal_monthly,
            yearly_projection=yearly_projection,
            generated_at=datetime.utcnow(),
        )


_energy_forecasting_service_singleton: Optional[EnergyForecastingService] = None


def get_energy_forecasting_service() -> EnergyForecastingService:
    global _energy_forecasting_service_singleton
    if _energy_forecasting_service_singleton is None:
        _energy_forecasting_service_singleton = EnergyForecastingService()
    return _energy_forecasting_service_singleton
