from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, users, projects, sites

# Create tables (Milestone 1: simple create_all; use Alembic migrations from Milestone 2 onward)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Solar & Wind Deployment Intelligence Platform API",
    description="Milestone 1: Project Initialization, Auth & Core Setup",
    version="0.1.0",
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(sites.router)
app.include_router(sites.site_router)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
