# Movie Recommendation System

> Production-grade movie recommendation platform demonstrating backend excellence — clean architecture, comprehensive testing, proper observability — with Spark ETL, ALS collaborative filtering, FastAPI serving, and Kubernetes-ready deployment.

[![CI](https://github.com/ganesh/movie-recommendation-system/actions/workflows/ci.yml/badge.svg)](https://github.com/ganesh/movie-recommendation-system/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     MovieLens 25M Dataset                        │
│                         (25M ratings)                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Spark ETL     │
                    │  (PySpark)      │
                    └───┬─────────┬───┘
                        │         │
              ┌─────────▼──┐  ┌──▼──────────┐
              │ PostgreSQL  │  │ ALS Training│
              │ (metadata)  │  │  (MLflow)   │
              └─────┬───────┘  └──────┬──────┘
                    │                 │
              ┌─────▼─────────────────▼──────┐
              │         FastAPI Service       │
              │  ┌─────────────────────────┐  │
              │  │ Recommendations Engine  │  │
              │  │  - Cold start handling  │  │
              │  │  - Caching (Redis)      │  │
              │  │  - Explainability       │  │
              │  └─────────────────────────┘  │
              │  Prometheus metrics │ Health   │
              └──────────┬───────────────────┘
                         │
              ┌──────────▼──────────┐
              │    React Frontend   │
              │  (Vite + Tailwind)  │
              └─────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Data Pipeline** | PySpark, MovieLens 25M |
| **ML Models** | Spark ALS, MLflow |
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic v2, asyncpg |
| **Caching** | Redis 7 (async client) |
| **Database** | PostgreSQL 16, Alembic migrations |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, React Query |
| **Observability** | Prometheus, structlog (JSON) |
| **Infrastructure** | Docker, Docker Compose, GitHub Actions CI/CD |
| **Code Quality** | ruff, mypy (strict), pytest, pre-commit hooks |

## Features

- **Personalized Recommendations** — ALS collaborative filtering with tiered cold-start handling
- **Sub-100ms Response Times** — Multi-layer Redis caching (user recs, popular, metadata)
- **Recommendation Explainability** — Each suggestion includes a human-readable explanation
- **Clean Architecture** — Routers → Services → Repositories separation with dependency injection
- **Comprehensive Testing** — Unit + integration tests with 60%+ coverage
- **Production Observability** — Prometheus metrics, structured JSON logging, health probes
- **Modern Frontend** — Dark-themed movie browser with search, filters, and recommendation carousels

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend development)

### 1. Clone & Configure

```bash
git clone https://github.com/ganesh/movie-recommendation-system.git
cd movie-recommendation-system
cp .env.example .env
```

### 2. Start All Services

```bash
# Start PostgreSQL, Redis, API, and Frontend
make dev

# Or with Docker Compose directly
docker compose up -d
```

### 3. Seed the Database

```bash
# Run migrations and seed sample data
make db-migrate
make db-seed
```

The application will be available at:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Prometheus Metrics**: http://localhost:8000/metrics

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/recommendations/{user_id}` | Personalized recommendations |
| `GET` | `/api/v1/recommendations/similar/{movie_id}` | Similar movies |
| `GET` | `/api/v1/movies` | Search/browse movie catalog |
| `GET` | `/api/v1/movies/popular` | Popular movies by genre |
| `GET` | `/api/v1/movies/{movie_id}` | Movie details |
| `GET` | `/api/v1/users/{user_id}` | User profile |
| `GET` | `/api/v1/users/{user_id}/ratings` | User's rating history |
| `POST` | `/api/v1/users/{user_id}/ratings` | Submit a rating |
| `GET` | `/api/v1/discover?q=...` | Semantic movie search |
| `POST` | `/api/v1/auth/google` | Google Sign-In |
| `GET` | `/api/v1/health` | Liveness probe |
| `GET` | `/api/v1/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus metrics |

## Project Structure

```
movie-recommendation-system/
├── api/                          # FastAPI backend
│   ├── alembic/                  # Database migrations
│   ├── app/
│   │   ├── core/                 # Config, DB, Redis, logging, exceptions
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── repositories/         # Data access layer
│   │   ├── services/             # Business logic
│   │   ├── routers/              # API endpoints
│   │   └── scripts/              # DB seeding
│   ├── tests/                    # Unit + integration tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                     # React application
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   ├── pages/                # Page-level components
│   │   └── services/             # API client
│   └── Dockerfile
├── spark/                        # Spark ETL & model training
│   ├── etl/                      # Data ingestion pipeline
│   └── models/                   # ALS training with MLflow
├── scripts/                      # Setup & data scripts
├── docker-compose.yml            # Local development
├── Makefile                      # Common commands
└── .github/workflows/ci.yml     # CI/CD pipeline
```

## Development

### Local Development (without Docker)

```bash
# Install API dependencies
cd api && pip install -e ".[dev]"

# Start API (requires PostgreSQL + Redis running)
make dev-api

# In another terminal, start frontend
cd frontend && npm install && npm run dev
```

### Running Tests

```bash
make test               # Run all tests
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-coverage      # With coverage report
```

### Code Quality

```bash
make lint               # Run ruff + mypy
make format             # Auto-format code
```

### ML Pipeline

```bash
make data-download      # Download MovieLens 25M (~250MB)
make data-process       # Run Spark ETL pipeline
make train-als          # Train ALS model with MLflow tracking
```

## Recommendation Strategy

The system implements a tiered recommendation approach:

| User State | Strategy | Method |
|-----------|----------|--------|
| New user (0 ratings) | Popular | Top movies by rating count |
| Few ratings (<5) | Content-based | Genre similarity fallback |
| Active user (5+) | Collaborative | ALS factor-based scoring |

Each recommendation includes:
- **Predicted rating** — Estimated user preference
- **Explanation** — Why this movie was recommended
- **Confidence score** — Model certainty
- **Model source** — Which algorithm generated it

## Deployment

### Railway + Vercel (Free Tier — Recommended)

**Backend (Railway — $5 free credit/month):**

1. Go to [railway.app](https://railway.app) → New Project → **Deploy from GitHub Repo**
2. Select `movie-recommendation-system` — Railway detects the Dockerfile
3. Add **PostgreSQL** and **Redis** plugins from the Railway dashboard
4. Set environment variables on the API service:
   - `TMDB_API_KEY` — Get free at [themoviedb.org](https://www.themoviedb.org/settings/api)
   - `CORS_ORIGINS` — `["https://your-app.vercel.app"]` (update after Vercel deploy)
   - `JWT_SECRET` — Any random string
5. The database auto-seeds on first startup

**Frontend (Vercel — completely free):**

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → Import your GitHub repo
2. Set **Root Directory** to `frontend`
3. Add environment variable: `VITE_API_URL` = `https://your-api.up.railway.app` (your Railway API URL)
4. Deploy — Vercel builds and serves the static site with zero cold starts

### Docker (Local Development)

```bash
make docker-build       # Build all images
docker compose up -d    # Start all services
```

## License

MIT
