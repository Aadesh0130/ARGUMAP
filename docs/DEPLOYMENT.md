# ARGUMAP Production Deployment Guide

This guide contains step-by-step instructions for deploying the **ARGUMAP** system to production with:
- **Frontend:** [Vercel](https://vercel.com) (React 18, Vite 5, TypeScript, Tailwind CSS, React Flow)
- **Backend:** [Render](https://render.com) (FastAPI, Python 3.10, Uvicorn, SQLAlchemy 2)
- **Database:** [Render Managed PostgreSQL](https://render.com/docs/databases)

---

## Architecture Overview

```
 ┌──────────────────────┐         HTTPS / REST          ┌──────────────────────┐
 │   Vercel Frontend    │ ────────────────────────────> │    Render Backend    │
 │ (React / Vite SPA)   │ <──────────────────────────── │   (FastAPI Service)  │
 └──────────────────────┘   CORS Whitelisted Origin     └──────────┬───────────┘
                                                                   │
                                                                   │ SQLAlchemy Connection Pool
                                                                   ▼ (pool_pre_ping=True)
                                                        ┌──────────────────────┐
                                                        │  Render PostgreSQL   │
                                                        │ (Persistent Storage) │
                                                        └──────────────────────┘
```

---

## 1. Database Provisioning (Render PostgreSQL)

Deploy the database first so its connection string is available for the backend service.

### Step 1.1: Create Managed PostgreSQL Instance
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **PostgreSQL**.
3. Configure the database parameters:
   - **Name:** `argumap-db`
   - **Database:** `argumap`
   - **User:** `argumap_user`
   - **Region:** Choose the region closest to your users (e.g. `Frankfurt` or `Oregon`).
   - **PostgreSQL Version:** 16 (or latest stable).
   - **Instance Type:** Free or Starter.
4. Click **Create Database**.

### Step 1.2: Retrieve Connection Strings
Once provisioned, note the connection details from the Render dashboard:
- **Internal Database URL** (recommended for Render backend services in the same region):
  `postgresql://argumap_user:<PASSWORD>@dpg-xxxx-a:5432/argumap`
- **External Database URL** (for remote access or migration scripts):
  `postgresql://argumap_user:<PASSWORD>@dpg-xxxx-a.render.com/argumap`

> [!NOTE]
> Render may provide connection strings with the legacy `postgres://` scheme. The ARGUMAP backend automatically normalizes `postgres://` to `postgresql://` for SQLAlchemy 2 compatibility.
>
> In production (`APP_ENV=production`), automatic SQLite fallback is **strictly disabled**. If the database is unreachable, the backend fails visibly and reports unready to avoid silent data loss.

---

## 2. Backend Deployment (Render Web Service)

### Step 2.1: Create Web Service
1. In the Render Dashboard, click **New +** → **Web Service**.
2. Connect your Git repository.
3. Configure the service settings:
   - **Name:** `argumap-api`
   - **Region:** Same region as your database.
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free or Starter.

### Step 2.2: Configure Environment Variables
In the Render service **Environment** tab, add the following variables:

| Variable | Value | Purpose |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enables production safeguards (strict DB check, no SQLite fallback). |
| `DATABASE_URL` | `<Your Internal Database URL>` | PostgreSQL connection string from Step 1.2. |
| `CORS_ORIGINS` | `https://<your-vercel-app>.vercel.app,http://localhost:5173` | Comma-separated list of allowed frontend origins. |
| `CORS_ORIGIN_REGEX` | `^https:\/\/.*\.vercel\.app$` *(optional)* | Allows dynamic preview branches on Vercel. |
| `HOST` | `0.0.0.0` | Binds to all network interfaces. |
| `PORT` | *(Managed automatically by Render)* | Render injects this at container launch. |
| `LOG_LEVEL` | `info` | Standard production logging. |

### Step 2.3: Health Check Endpoint
Configure Render's Health Check Path:
- **Health Check Path:** `/api/health`

The health endpoint checks active database connectivity. It returns:
- `HTTP 200` (`"status": "healthy"`, `"database": "connected"`) when the database is responsive.
- `HTTP 503` (`"status": "unhealthy"`, `"database": "disconnected"`) when database connectivity fails.

---

## 3. Frontend Deployment (Vercel)

### Step 3.1: Import Project to Vercel
1. Log in to the [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your ARGUMAP repository.

### Step 3.2: Configure Project Settings
- **Framework Preset:** `Vite`
- **Root Directory:** Click **Edit** and set to `frontend`.
- **Build Command:** `npm run build` (or leave default `tsc && vite build`).
- **Output Directory:** `dist`.
- **Install Command:** `npm install`.

### Step 3.3: Environment Variables
Under **Environment Variables**, add:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://argumap-api.onrender.com/api` | The public base URL of your deployed Render backend service. |

> [!TIP]
> The frontend normalizes `VITE_API_URL` automatically: trailing slashes are trimmed and `/api` is appended if omitted.

### Step 3.4: SPA Routing Support
To prevent HTTP 404 errors when refreshing client-side routes (e.g. `/analyze`, `/processing`, `/results`, `/about`, `/technology`), the repository includes a `vercel.json` rewrite file:
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

---

## 4. Local Development vs. Production Verification

| Check | Local Development | Production (Render + Vercel) |
| :--- | :--- | :--- |
| Frontend API Base | `http://localhost:8000/api` | `https://<render-service>.onrender.com/api` |
| Database Engine | SQLite (`sqlite:///./argumap_dev.db`) | Managed PostgreSQL (`postgresql://...`) |
| DB Failure Behavior | Automatically falls back to SQLite | **Raises RuntimeError & halts startup** |
| Health Check | `HTTP 200` (`healthy`, `sqlite`) | `HTTP 200` (`healthy`, `postgresql`) |
| CORS Origins | `http://localhost:5173,http://localhost:3000` | Whitelisted Vercel domain + preview regex |
| SPA Route Refresh | Handled by Vite dev server | Handled by `vercel.json` rewrites |

---

## 5. Security & Secrets Hygiene

1. **Never commit `.env` files**: All secrets are stored in cloud environment settings.
2. **Database Passwords**: The backend's `_mask_db_url` helper strips passwords before any URL is written to logs or error messages.
3. **CORS Credentials**: If `*` is supplied as an origin, credentials are automatically disabled to prevent browser security exceptions.
4. **Health Check Sanitization**: `/api/health` reports status without leaking hostnames, ports, credentials, or error tracebacks.
