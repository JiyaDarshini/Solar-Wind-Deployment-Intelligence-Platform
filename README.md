Solar & Wind Deployment Intelligence Platform

An AI-powered platform that recommends optimal locations for solar and wind energy deployment by analyzing environmental, geographic, climatic, and infrastructure-related factors. Built for renewable energy planners, GIS analysts, project managers, and administrators to identify suitable sites, estimate energy generation potential, evaluate feasibility, and support investment decisions.

Table of Contents
Objective
Tech Stack
Project Structure
Milestone 1 — Core Foundation
Milestone 2 — Environmental Intelligence & Resource Prediction
Setup & Installation (Windows)
Environment Variables
Running the Platform
API Reference
Roadmap
Objective
Build an AI-powered Solar & Wind Deployment Intelligence Platform that leverages geospatial analytics, satellite imagery, weather forecasting, terrain analysis, machine learning, and optimization algorithms to:

Identify suitable renewable energy deployment locations
Estimate solar and wind generation potential
Evaluate project feasibility and environmental impact
Support investment decision-making

User roles: Renewable Energy Planner, GIS Analyst, Project Manager, Administrator
Tech Stack
Layer	Technologies
Backend	Python, FastAPI
Frontend	React.js, Vite
Primary Database	PostgreSQL + PostGIS
Secondary Database	MongoDB
Cache	Redis
ML / Prediction	XGBoost, LightGBM, Random Forest, scikit-learn
GIS / Geospatial	GeoPandas, Shapely, Rasterio, GDAL
External APIs	NASA POWER, Open-Meteo/SRTM, OpenStreetMap Overpass, OpenWeather, Copernicus Sentinel Hub (planned), Global Wind Atlas (planned)
Auth	JWT, OAuth2, Role-Based Access Control
DevOps	Docker, Docker Compose, GitHub Actions
Project Structure
Solar-Wind-Deployment-Intelligence-Platform/
├── backend/                 # Milestone 1 — auth, RBAC, project/site management
├── frontend/                 # React/Vite UI — login, dashboard, site registration, comparison
├── app/                        # Milestone 2 — environmental intelligence & prediction engines
│   ├── core/                # Config (merged with Milestone 1 settings)
│   ├── models/               # Pydantic schemas
│   ├── services/              # Business logic (environmental, GIS, solar, wind, reports)
│   ├── ml/                     # Model training scripts + saved artifacts
│   └── api/routes/           # FastAPI routers
├── docker-compose.yml
├── .gitignore
└── README.md
Milestone 1 — Core Foundation

Status: Complete

FastAPI backend with PostgreSQL/PostGIS, MongoDB, and Redis (Docker Compose)
JWT authentication with OAuth2 login
Role-based access control (Renewable Energy Planner, GIS Analyst, Project Manager, Administrator)
Full CRUD for projects, sites, and regions
Site comparison and audit history endpoints
Live integrations with NASA POWER, Open-Meteo/SRTM, and OpenStreetMap Overpass
React/Vite frontend: Login, Register, Dashboard, Site Registration, Comparison pages
Milestone 2 — Environmental Intelligence & Resource Prediction

Status: Complete

Implements Modules 3–6 from the platform spec as a self-contained, drop-in addition to the app/ folder (does not overwrite Milestone 1 auth/user/project files).

Module	Description
Module 3 — Environmental Data Collection Engine	Weather/climate ingestion (NASA POWER, OpenWeather), terrain analysis (SRTM elevation via Rasterio), all with graceful fallbacks if external APIs are unreachable
Module 4 — Geographic Intelligence Engine	Infrastructure proximity analysis (roads, transmission lines, substations, urban areas, protected zones, water bodies, agricultural land) via OpenStreetMap Overpass + GeoPandas/Shapely, plus a derived accessibility score
Module 5 — Solar Potential Prediction Engine	XGBoost/Random Forest model → Annual Irradiance, Peak Sun Hours, Expected Energy Output, Capacity Factor, Performance Ratio, shading loss, monthly generation breakdown
Module 6 — Wind Potential Prediction Engine	LightGBM/Random Forest model with log-law wind shear extrapolation to hub height → Average Wind Speed, Wind Power Density, Turbulence Intensity, Capacity Factor, Expected Annual Energy Production, turbine suitability classification
Resource Assessment Reports	Combines all engines into a single report, persisted to MongoDB

Notes:

ML models are trained on a physically-grounded synthetic dataset (documented in train_solar_model.py / train_wind_model.py) pending real historical training data. Prediction services fall back to heuristic formulas if .joblib artifacts haven't been generated, so the API never hard-fails.
Copernicus Sentinel Hub and Global Wind Atlas integrations are configured but not yet wired to live calls — planned for a later milestone.
Setup & Installation (Windows)
Prerequisites
Python 3.10+
Node.js 18+
Docker Desktop (or native PostgreSQL + PostGIS as a fallback)
Git
Clone the repository
cmd
git clone https://github.com/JiyaDarshini/Solar-Wind-Deployment-Intelligence-Platform.git
cd Solar-Wind-Deployment-Intelligence-Platform
Backend setup
cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

If rasterio fails to install: pip install rasterio --only-binary :all:

Train the ML models (one-time)
cmd
python -m app.ml.train_solar_model
python -m app.ml.train_wind_model
Frontend setup
cmd
cd frontend
npm install
Docker (recommended, full stack)
cmd
docker-compose up --build
Native Windows fallback (if Docker is unavailable)
Install PostgreSQL with the PostGIS extension locally
Run backend with uvicorn app.main:app --reload
Run frontend with npm run dev from the frontend folder
Environment Variables

Create a .env file in the project root:

env
# Database
POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/solarwind
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=solarwind_env
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=change-me
OAUTH2_CLIENT_ID=
OAUTH2_CLIENT_SECRET=

# External APIs (all optional — module degrades gracefully without them)
OPENWEATHER_API_KEY=
COPERNICUS_SENTINEL_CLIENT_ID=
COPERNICUS_SENTINEL_CLIENT_SECRET=

NASA POWER and OpenStreetMap Overpass require no API key.

Running the Platform
cmd
uvicorn app.main:app --reload

Backend runs at http://localhost:8000 — interactive API docs at http://localhost:8000/docs.

cmd
cd frontend
npm run dev

Frontend runs at http://localhost:5173 (default Vite port).

API Reference
Auth & Users (Milestone 1)
Method	Path
POST	/api/v1/auth/register
POST	/api/v1/auth/login
GET	/api/v1/users/me
Projects & Sites (Milestone 1)
Method	Path
POST	/api/v1/projects
POST	/api/v1/sites
GET	/api/v1/sites/compare
Environmental Intelligence (Milestone 2)
Method	Path	Purpose
POST	/api/v1/environmental/profile	Weather/climate + terrain profile for a site
GET	/api/v1/environmental/proximity	Infrastructure proximity + accessibility score
POST	/api/v1/solar/predict	Solar Potential Prediction Engine
POST	/api/v1/wind/predict	Wind Potential Prediction Engine
POST	/api/v1/reports/generate/{site_id}	Full resource assessment report (env + solar + wind)
GET	/api/v1/reports/{site_id}	Fetch a saved report
GET	/api/v1/reports/	List recent reports
Roadmap
Milestone	Weeks	Focus
✅ Milestone 1	1–2	Project initialization, auth, RBAC, project/site management
✅ Milestone 2	3–4	Environmental intelligence, GIS processing, solar & wind prediction
⬜ Milestone 3	5–6	Site suitability engine, deployment optimization, forecasting, investment recommendations, dashboards
⬜ Milestone 4	7–8	Executive dashboards, reports & GIS visualization, testing, Docker/cloud deployment
