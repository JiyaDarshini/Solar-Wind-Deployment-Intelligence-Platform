import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Float,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    RENEWABLE_ENERGY_PLANNER = "renewable_energy_planner"
    GIS_ANALYST = "gis_analyst"
    PROJECT_MANAGER = "project_manager"
    INVESTOR_DEVELOPER = "investor_developer"
    GOVERNMENT_REGULATOR = "government_regulator"
    ADMINISTRATOR = "administrator"


class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=True)  # nullable for OAuth-only users
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RENEWABLE_ENERGY_PLANNER)
    auth_provider = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.LOCAL)
    organization = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    region = Column(String, nullable=True)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    sites = relationship("Site", back_populates="project", cascade="all, delete-orphan")


class LandOwnership(str, enum.Enum):
    PRIVATE = "private"
    GOVERNMENT = "government"
    LEASED = "leased"
    COMMUNITY = "community"
    UNKNOWN = "unknown"


class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)

    # Core site attributes (from spec section: Site Information)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    land_area_hectares = Column(Float, nullable=True)
    elevation_m = Column(Float, nullable=True)
    existing_infrastructure = Column(Text, nullable=True)
    land_ownership = Column(Enum(LandOwnership), default=LandOwnership.UNKNOWN)

    # Cached environmental snapshot (populated by environmental data engine)
    avg_solar_irradiance_kwh_m2_day = Column(Float, nullable=True)
    avg_wind_speed_m_s = Column(Float, nullable=True)
    avg_temperature_c = Column(Float, nullable=True)
    annual_rainfall_mm = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="sites")
