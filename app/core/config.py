"""
Milestone 2 - Core configuration
Environmental Intelligence & Resource Prediction

Reads settings from environment variables so this plugs into whatever
config pattern Milestone 1 already uses. If you already have a
`app/core/config.py`, merge these fields into your existing Settings class
instead of overwriting it.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Database (reuse Milestone 1 connections) ---
    POSTGRES_DSN: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/solarwind"
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "solarwind_env"

    # --- External data source APIs ---
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    OPENWEATHER_API_KEY: str = ""
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    COPERNICUS_SENTINEL_CLIENT_ID: str = ""
    COPERNICUS_SENTINEL_CLIENT_SECRET: str = ""
    SENTINEL_HUB_BASE_URL: str = "https://services.sentinel-hub.com"
    GLOBAL_WIND_ATLAS_BASE_URL: str = "https://globalwindatlas.info/api"
    OSM_OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"

    # --- Caching ---
    REDIS_URL: str = "redis://localhost:6379/0"
    ENV_DATA_CACHE_TTL_SECONDS: int = 60 * 60 * 6  # 6 hours

    # --- ML model artifact paths (produced by app/ml/train_*.py) ---
    SOLAR_MODEL_PATH: str = "app/ml/artifacts/solar_potential_model.joblib"
    WIND_MODEL_PATH: str = "app/ml/artifacts/wind_potential_model.joblib"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
