# Solar & Wind Deployment Intelligence Platform — Milestone 1

**Scope:** Project Initialization, Design Process & Core Setup (Week 1 & 2)

## What's implemented

- **Auth & RBAC**: registration, JWT login (`/api/auth/login`), refresh tokens, Google OAuth2 login, role-based access control with 6 roles (Renewable Energy Planner, GIS Analyst, Project Manager, Investor/Developer, Government/Regulator, Administrator).
- **Project & Site Management**: project CRUD, site registration with coordinates/land area/elevation/infrastructure/ownership, site listing, site comparison endpoint.
- **Environmental Data Collection Engine**: integrates NASA POWER (solar irradiance, temperature, rainfall), Open-Meteo (wind speed proxy for Global Wind Atlas), and OpenStreetMap Overpass (nearby roads/substations/power lines) — cached onto each Site record via `/api/sites/{id}/enrich-environmental-data`.
- **Frontend**: React app with login/register, Google OAuth callback, project list/create, and a site table with a one-click "Fetch environmental data" action.
- **Dockerized**: `docker-compose.yml` spins up PostgreSQL+PostGIS, the FastAPI backend, and the React frontend together.

## Quick start

```bash
cd milestone1
cp backend/.env.example backend/.env   # fill in SECRET_KEY, Google OAuth creds, etc.
docker compose up --build
```

- Backend API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Manual (non-Docker) setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# make sure PostgreSQL + PostGIS extension is running and DATABASE_URL is set
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create a user account |
| POST | `/api/auth/login` | Get access + refresh JWT tokens |
| POST | `/api/auth/refresh` | Refresh an expired access token |
| GET | `/api/auth/oauth/google/login` | Start Google OAuth2 flow |
| GET | `/api/auth/me` | Current user profile |
| GET/PATCH | `/api/users/{id}/role` | Admin: change a user's role (RBAC) |
| POST/GET | `/api/projects/` | Create / list projects |
| POST/GET | `/api/projects/{id}/sites/` | Register / list sites for a project |
| POST | `/api/sites/{id}/enrich-environmental-data` | Pull solar/wind/climate/infrastructure data for a site |
| POST | `/api/sites/compare` | Compare multiple sites side by side |

## Notes on next milestones

This build intentionally stops at data ingestion — the solar/wind **prediction models**, **site suitability scoring**, **deployment optimization**, and **dashboards** described in the full spec are Milestone 2+ work and are not included here.
