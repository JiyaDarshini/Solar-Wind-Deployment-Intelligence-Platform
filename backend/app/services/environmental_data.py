"""
Environmental Data Collection Engine (Milestone 1 scope).

Integrates external datasets identified in the spec:
- NASA POWER API        -> solar irradiance, temperature, rainfall (climatology)
- Open-Meteo API         -> wind speed (used here as a free stand-in for Global Wind Atlas,
                            since Global Wind Atlas has no public REST API)
- OpenStreetMap Overpass -> nearby infrastructure (roads, substations, transmission lines)

Full prediction/scoring models (solar/wind potential engines, site suitability, etc.)
are out of scope for Milestone 1 and are implemented in later milestones. This module
only fetches and caches the raw environmental snapshot used to seed those engines.
"""

from typing import Optional

import httpx

from app.config import settings


class EnvironmentalDataError(Exception):
    pass


async def fetch_nasa_power_climatology(latitude: float, longitude: float) -> dict:
    """
    Fetches long-term climatology (solar irradiance, temperature, precipitation)
    for a given point from the NASA POWER API.
    """
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,T2M,PRECTOTCORR",
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "format": "JSON",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(settings.NASA_POWER_BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EnvironmentalDataError(f"NASA POWER request failed: {exc}") from exc

    data = resp.json()
    try:
        params_data = data["properties"]["parameter"]
        irradiance = params_data["ALLSKY_SFC_SW_DWN"]["ANN"]  # kWh/m^2/day, annual avg
        temperature = params_data["T2M"]["ANN"]  # deg C, annual avg
        rainfall = params_data["PRECTOTCORR"]["ANN"]  # mm/day, annual avg -> convert to mm/year
    except (KeyError, TypeError) as exc:
        raise EnvironmentalDataError(f"Unexpected NASA POWER response format: {exc}") from exc

    return {
        "avg_solar_irradiance_kwh_m2_day": round(irradiance, 3),
        "avg_temperature_c": round(temperature, 2),
        "annual_rainfall_mm": round(rainfall * 365, 1),
    }


async def fetch_wind_speed(latitude: float, longitude: float) -> dict:
    """
    Fetches average wind speed for a point using Open-Meteo's historical/forecast API
    as a lightweight proxy dataset for wind resource assessment.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m",
        "forecast_days": 7,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(settings.OPEN_METEO_BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EnvironmentalDataError(f"Wind data request failed: {exc}") from exc

    data = resp.json()
    speeds = data.get("hourly", {}).get("wind_speed_10m", [])
    if not speeds:
        raise EnvironmentalDataError("No wind speed data returned")

    avg_speed = sum(speeds) / len(speeds)
    return {"avg_wind_speed_m_s": round(avg_speed, 2)}


async def fetch_nearby_infrastructure(
    latitude: float, longitude: float, radius_m: int = 5000
) -> dict:
    """
    Queries OpenStreetMap's Overpass API for nearby roads, substations, and
    transmission lines, used for infrastructure proximity / accessibility analysis.
    """
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"](around:{radius_m},{latitude},{longitude});
      node["power"="substation"](around:{radius_m},{latitude},{longitude});
      way["power"="line"](around:{radius_m},{latitude},{longitude});
    );
    out center;
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(settings.OSM_OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EnvironmentalDataError(f"OSM Overpass request failed: {exc}") from exc

    elements = resp.json().get("elements", [])
    roads = [e for e in elements if e.get("tags", {}).get("highway")]
    substations = [e for e in elements if e.get("tags", {}).get("power") == "substation"]
    power_lines = [e for e in elements if e.get("tags", {}).get("power") == "line"]

    return {
        "nearby_roads_count": len(roads),
        "nearby_substations_count": len(substations),
        "nearby_power_lines_count": len(power_lines),
        "search_radius_m": radius_m,
    }


async def build_environmental_snapshot(latitude: float, longitude: float) -> dict:
    """
    Aggregates all environmental/geographic data sources into a single snapshot
    used to populate a Site's cached environmental fields.
    """
    snapshot: dict = {}
    errors: dict = {}

    for label, coro in (
        ("solar_climate", fetch_nasa_power_climatology(latitude, longitude)),
        ("wind", fetch_wind_speed(latitude, longitude)),
    ):
        try:
            snapshot.update(await coro)
        except EnvironmentalDataError as exc:
            errors[label] = str(exc)

    try:
        snapshot["infrastructure"] = await fetch_nearby_infrastructure(latitude, longitude)
    except EnvironmentalDataError as exc:
        errors["infrastructure"] = str(exc)

    if errors:
        snapshot["_partial_errors"] = errors

    return snapshot
