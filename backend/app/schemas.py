from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import UserRole, LandOwnership


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    role: UserRole = UserRole.RENEWABLE_ENERGY_PLANNER
    organization: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    organization: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)


class UserRoleUpdate(BaseModel):
    role: UserRole


# ---------- Project ----------

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    region: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    region: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Site ----------

class SiteCreate(BaseModel):
    name: str
    region: Optional[str] = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    land_area_hectares: Optional[float] = None
    elevation_m: Optional[float] = None
    existing_infrastructure: Optional[str] = None
    land_ownership: LandOwnership = LandOwnership.UNKNOWN


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    land_area_hectares: Optional[float] = None
    elevation_m: Optional[float] = None
    existing_infrastructure: Optional[str] = None
    land_ownership: Optional[LandOwnership] = None


class SiteOut(BaseModel):
    id: str
    project_id: str
    name: str
    region: Optional[str]
    latitude: float
    longitude: float
    land_area_hectares: Optional[float]
    elevation_m: Optional[float]
    existing_infrastructure: Optional[str]
    land_ownership: LandOwnership
    avg_solar_irradiance_kwh_m2_day: Optional[float]
    avg_wind_speed_m_s: Optional[float]
    avg_temperature_c: Optional[float]
    annual_rainfall_mm: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SiteComparisonRequest(BaseModel):
    site_ids: list[str]
