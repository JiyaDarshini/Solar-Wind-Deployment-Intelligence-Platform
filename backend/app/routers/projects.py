from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/projects", tags=["Projects"])

# Roles allowed to create/modify projects (site management workflow owners)
MANAGE_ROLES = (
    models.UserRole.RENEWABLE_ENERGY_PLANNER,
    models.UserRole.PROJECT_MANAGER,
    models.UserRole.ADMINISTRATOR,
)


def _get_owned_project_or_404(project_id: str, db: Session, current_user: models.User) -> models.Project:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != models.UserRole.ADMINISTRATOR:
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    return project


@router.post("/", response_model=schemas.ProjectOut, status_code=201)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES)),
):
    project = models.Project(
        name=payload.name,
        description=payload.description,
        region=payload.region,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Project)
    if current_user.role != models.UserRole.ADMINISTRATOR:
        query = query.filter(models.Project.owner_id == current_user.id)
    return query.order_by(models.Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _get_owned_project_or_404(project_id, db, current_user)


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: str,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES)),
):
    project = _get_owned_project_or_404(project_id, db, current_user)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.region is not None:
        project.region = payload.region

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MANAGE_ROLES)),
):
    project = _get_owned_project_or_404(project_id, db, current_user)
    db.delete(project)
    db.commit()
    return None
