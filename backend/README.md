# ARGUMAP — FastAPI Backend Service

This directory contains the Python backend service for **ARGUMAP** (Automated Argument Structure Analysis and Debate Reasoning).

* **Framework:** FastAPI (Python 3.10+)
* **Data Layer:** SQLAlchemy v2 (PostgreSQL-ready with SQLite development fallback)
* **Validation:** Pydantic v2
* **API Documentation:** Automatic OpenAPI / Swagger UI

---

## 1. Setup & Installation

### 1.1 Create the Virtual Environment
From the repository root or `backend/` directory:

```bash
# Windows
py -3.10 -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3.10 -m venv venv
source venv/bin/activate
```

### 1.2 Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 2. Environment Configuration

Copy the example environment configuration to `.env`:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

### Available Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string (falls back to local SQLite in development; mandatory in production) | `sqlite:///./argumap_dev.db` |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins (e.g. `https://argumap.vercel.app,http://localhost:5173`) | `http://localhost:5173,http://localhost:3000` |
| `CORS_ORIGIN_REGEX` | Optional regex pattern for frontend origins (e.g. `https:\/\/.*\.vercel\.app`) | `None` |
| `APP_ENV` | Runtime environment (`development`, `staging`, `production`) | `development` |
| `HOST` | Server host binding (`0.0.0.0` for Docker/Render) | `0.0.0.0` |
| `PORT` | Server port binding (Render injects `$PORT` automatically) | `8000` |
| `LOG_LEVEL` | Logging level (`debug`, `info`, `warning`, `error`) | `info` |

> **Security Rule:** Never commit `.env` or hardcode database credentials.

---

## 3. Starting the Backend Server

### Local Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment (Render + PostgreSQL)
See the complete deployment guide in [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

* **Root Directory:** `backend`
* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
* **Health Check Path:** `/api/health`

The service will be accessible at:
* **Root Endpoint:** `http://127.0.0.1:8000/`
* **Health Check:** `http://127.0.0.1:8000/api/health`

---

## 4. Interactive API Documentation (Swagger)

FastAPI automatically generates interactive API documentation:
* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **OpenAPI JSON Specification:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 5. Running Automated Tests

Run the complete test suite using `pytest`:

```bash
# Run all tests
pytest tests/ -v

# Run with output capture disabled
pytest tests/ -v -s
```

All test cases run against an isolated in-memory SQLite fixture and do not require a live PostgreSQL server.

---

## 6. Endpoints Overview

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/` | Root service metadata & health links |
| `GET` | `/api/health` | Service health & database connectivity status |
| `POST` | `/api/debates` | Ingest debate session & parse speaker turns |
| `GET` | `/api/debates/{id}` | Retrieve debate details, turns, and run history |
| `POST` | `/api/analyze` | Ingest transcript & initiate analysis run (Phase 4 placeholder) |
| `GET` | `/api/analysis/{id}` | Retrieve analysis run, argument graph, and insights |
