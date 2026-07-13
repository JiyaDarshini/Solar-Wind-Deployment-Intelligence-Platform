from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_roles
from app.routers.projects import _get_owned_project_or_404, MANAGE_ROLES
from app.services import environmental_data

router = APIRouter(prefix="/api/projects/{project_id}/sites", tags=["Sites"])
site_router = APIRouter(prefix="/api/sites", tags=["Sites"])


@router.post("/", response_model=schemas.SiteOut, status_code=201)
def register_site(
    project_id: str,
    payload: schemas.SiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES)),
):
    """Register a new site under a project (Project & Site Management module)."""
    _get_owned_project_or_404(project_id, db, current_user)

    site = models.Site(
        project_id=project_id,
        name=payload.name,
        region=payload.region,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location=from_shape(Point(payload.longitude, payload.latitude), srid=4326),
        land_area_hectares=payload.land_area_hectares,
        elevation_m=payload.elevation_m,
        existing_infrastructure=payload.existing_infrastructure,
        land_ownership=payload.land_ownership,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/", response_model=list[schemas.SiteOut])
def list_sites_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned_project_or_404(project_id, db, current_user)
    return (
        db.query(models.Site)
        .filter(models.Site.project_id == project_id)
        .order_by(models.Site.created_at.desc())
        .all()
    )


def _get_site_or_404(site_id: str, db: Session, current_user: models.User) -> models.Site:
    site = db.query(models.Site).filter(models.Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    _get_owned_project_or_404(site.project_id, db, current_user)
    return site


@site_router.get("/{site_id}", response_model=schemas.SiteOut)
def get_site(site_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _get_site_or_404(site_id, db, current_user)


@site_router.patch("/{site_id}", response_model=schemas.SiteOut)
def update_site(
    site_id: str,
    payload: schemas.SiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES)),
):
    site = _get_site_or_404(site_id, db, current_user)
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(site, field, value)

    if "latitude" in update_data or "longitude" in update_data:
        site.location = from_shape(Point(site.longitude, site.latitude), srid=4326)

    db.commit()
    db.refresh(site)
    return site


@site_router.delete("/{site_id}", status_code=204)
def delete_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES)),
):
    site = _get_site_or_404(site_id, db, current_user)
    db.delete(site)
    db.commit()
    return None


@site_router.post("/{site_id}/enrich-environmental-data", response_model=schemas.SiteOut)
async def enrich_site_environmental_data(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES, models.UserRole.GIS_ANALYST)),
):
    """
    Environmental Data Collection Engine: pulls solar irradiance, temperature,
    rainfall, wind speed, and nearby infrastructure data for a site's coordinates
    and caches it on the Site record.
    """
    site = _get_site_or_404(site_id, db, current_user)

    snapshot = await environmental_data.build_environmental_snapshot(site.latitude, site.longitude)

    if "avg_solar_irradiance_kwh_m2_day" in snapshot:
        site.avg_solar_irradiance_kwh_m2_day = snapshot["avg_solar_irradiance_kwh_m2_day"]
    if "avg_temperature_c" in snapshot:
        site.avg_temperature_c = snapshot["avg_temperature_c"]
    if "annual_rainfall_mm" in snapshot:
        site.annual_rainfall_mm = snapshot["annual_rainfall_mm"]
    if "avg_wind_speed_m_s" in snapshot:
        site.avg_wind_speed_m_s = snapshot["avg_wind_speed_m_s"]

    infra = snapshot.get("infrastructure")
    if infra:
        site.existing_infrastructure = (
            f"Roads: {infra['nearby_roads_count']}, "
            f"Substations: {infra['nearby_substations_count']}, "
            f"Power lines: {infra['nearby_power_lines_count']} "
            f"(within {infra['search_radius_m']}m)"
        )

    db.commit()
    db.refresh(site)
    return site


@site_router.post("/compare", response_model=list[schemas.SiteOut])
def compare_sites(
    payload: schemas.SiteComparisonRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Site comparison workflow: returns full data for multiple sites side by side."""
    sites = db.query(models.Site).filter(models.Site.id.in_(payload.site_ids)).all()
    for site in sites:
        _get_owned_project_or_404(site.project_id, db, current_user)
    return sites
