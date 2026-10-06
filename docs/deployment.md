# HoneyVault Deployment Guide

**Owner:** T4 — Deployment & Release (Vedant)  
**Target Environments:** Local Docker Compose, Neon Postgres, Render (API & Honeychecker), Vercel (Frontend)

---

## 1. Overview & Architecture

HoneyVault is composed of three runtime components and two dedicated databases:

```text
       ┌────────────────────────┐
       │     Frontend (Vercel)  │
       │  React + Vite SPA      │
       └───────────┬────────────┘
                   │ HTTPS (API requests)
                   ▼
       ┌────────────────────────┐         Signed / mTLS          ┌────────────────────────┐
       │   HoneyVault API       │ ─────────────────────────────> │      Honeychecker      │
       │   (Render / Docker)    │                                │   (Render / Docker)    │
       └───────────┬────────────┘                                └───────────┬────────────┘
                   │                                                         │
                   │ SQL (psycopg 3)                                         │ SQL (psycopg 3)
                   ▼                                                         ▼
       ┌────────────────────────┐                                ┌────────────────────────┐
       │    Neon Database 1     │                                │    Neon Database 2     │
       │     `honeyvault`       │                                │    `honeychecker`      │
       └────────────────────────┘                                └────────────────────────┘
```

> [!IMPORTANT]
> **Database Isolation Invariant:** The `honeyvault` and `honeychecker` databases are strictly isolated. The API never has database access or credentials to the honeychecker database, ensuring that an SQL injection or compromised API DB snapshot does not disclose which candidate sweetword is the user's authentic password.

---

## 2. Local Docker Usage

Docker Compose orchestrates the complete backend stack locally using Docker 24+ and Compose v2.

### 2.1 Services Defined in `docker-compose.yml`
- **`db`**: PostgreSQL 16 Alpine container. Executes `docker/postgres-init.sql` on first boot to initialize separate `honeyvault` and `honeychecker` roles and databases. Includes container healthchecks.
- **`honeychecker`**: Honeychecker service running Python 3.12, exposed on port `8001`.
- **`api`**: HoneyVault API running Python 3.12, exposed on port `8000`. Runs `alembic upgrade head` automatically on container start.

### 2.2 Quickstart Commands

```bash
# 1. Build container images (build context is repo root)
docker compose build

# 2. Start services in background
docker compose up -d

# 3. Verify health status
curl http://localhost:8000/api/health
curl http://localhost:8001/hc/health

# 4. View container logs
docker compose logs -f api
docker compose logs -f honeychecker
docker compose logs -f db

# 5. Stop services (preserves database volume)
docker compose down

# 6. Stop and wipe database volume (clean reset)
docker compose down -v
```

### 2.3 Health Check Verification
When healthy, the endpoints return:
- `http://localhost:8000/api/health`:
  ```json
  {"status":"ok","version":"0.1.0","honeycore_impl":"stub","honeychecker":"ok"}
  ```
- `http://localhost:8001/hc/health`:
  ```json
  {"status":"ok","service":"honeychecker","version":"0.1.0","db":"ok"}
  ```

---

## 3. Neon Postgres Setup (Dual Database Architecture)

Neon provides serverless PostgreSQL with scale-to-zero capabilities.

### 3.1 Provisioning the Databases
1. Log in to [Neon Console](https://console.neon.tech).
2. Create a new Project named `honeyvault-prod` (region: **AWS Singapore `ap-southeast-1`** to minimize latency with Render).
3. Under the project, create **two distinct databases**:
   - Database 1: `honeyvault`
   - Database 2: `honeychecker`
4. Create dedicated roles or use the default pooled/direct roles for each database:
   - For `honeyvault-api`: connection string pointing to `honeyvault` database.
   - For `honeychecker`: connection string pointing to `honeychecker` database.

### 3.2 SQLAlchemy 2.0 Connection String Format
Both applications use psycopg 3. Ensure the scheme is prefixed with `postgresql+psycopg://` and includes `sslmode=require`:

```text
# For honeyvault-api (DATABASE_URL):
postgresql+psycopg://USER:PASSWORD@ep-xxxx.ap-southeast-1.aws.neon.tech/honeyvault?sslmode=require

# For honeychecker (HC_DATABASE_URL):
postgresql+psycopg://USER:PASSWORD@ep-xxxx.ap-southeast-1.aws.neon.tech/honeychecker?sslmode=require
```

### 3.3 Database Migrations on Neon
- **`honeyvault`**: Alembic manages table creation. When the API container spins up, `alembic upgrade head` runs automatically. You can also run migrations locally against Neon:
  ```bash
  DATABASE_URL="postgresql+psycopg://..." alembic upgrade head
  ```
- **`honeychecker`**: Automatically executes `Base.metadata.create_all()` on startup during the FastAPI lifespan hook.

---

## 4. Render Blueprint Deployment

Render deploys `honeyvault-api` and `honeyvault-honeychecker` using the declarative blueprint in [`render.yaml`](file:///c:/Users/Vedant/OneDrive/Desktop/CNS---Honey-Encryption-Vault/render.yaml).

### 4.1 Deployment Setup
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Go to **Blueprints** → **New Blueprint Instance**.
3. Connect the GitHub repository `rohansd05/CNS---Honey-Encryption-Vault` and select branch `dev` (or `main` at phase gate).
4. Render will detect [`render.yaml`](file:///c:/Users/Vedant/OneDrive/Desktop/CNS---Honey-Encryption-Vault/render.yaml) and configure:
   - `honeyvault-api` (Docker web service, region `singapore`, port auto-assigned)
   - `honeyvault-honeychecker` (Docker web service, region `singapore`, port auto-assigned)
5. Fill in the required environment variables in the Render Dashboard (listed with `sync: false`).

### 4.2 Transport Security on Render (`signed` mode)
Render terminates TLS at its edge proxy. Direct mutual TLS (`mTLS`) is not possible between free-tier web services on Render. Therefore:
- Set `HONEYCHECKER_TRANSPORT=signed` on `honeyvault-api`.
- Set `HC_TRANSPORT=signed` on `honeyvault-honeychecker`.
- The API signs each request payload and headers (`X-HV-Cert`, `X-HV-Timestamp`, `X-HV-Nonce`, `X-HV-Signature`) using ECDSA-P256-SHA256, and honeychecker validates the signature and replay window.

---

## 5. Vercel Frontend Deployment

The frontend React + TypeScript + Vite SPA is deployed on [Vercel](https://vercel.com).

### 5.1 Project Configuration
1. Import repository on Vercel.
2. Configure project settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm ci`

### 5.2 Single Page Application Routing
To support client-side routing via React Router, ensure [`frontend/vercel.json`](file:///c:/Users/Vedant/OneDrive/Desktop/CNS---Honey-Encryption-Vault/frontend/vercel.json) contains:
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/"
    }
  ]
}
```

### 5.3 Frontend Environment Variables
Set the following environment variables in Vercel:
- `VITE_API_BASE_URL`: URL of the deployed Render API (e.g., `https://honeyvault-api.onrender.com`).
- `VITE_USE_MOCKS`: `false` (in staging/production to consume live API).
- `VITE_DEMO_MODE`: `true` (enables demo banner and attacker console).
- `VITE_APP_NAME`: `HoneyVault`.

---

## 6. Environment Variable Matrix

| Variable | Service | Default / Example | Secret? | Description |
|---|---|---|---|---|
| `APP_ENV` | API, HC | `production` | No | Environment name (`development`, `staging`, `production`) |
| `LOG_LEVEL` | API, HC | `INFO` | No | Logging verbosity |
| `DEMO_MODE` | API | `true` | No | Enables demo endpoints and evaluation attack console |
| `DATABASE_URL` | API | `postgresql+psycopg://...` | **Yes** | Connection string for HoneyVault Postgres DB |
| `ALLOWED_ORIGINS` | API | `https://honeyvault.vercel.app` | No | Comma-separated CORS allowed origins |
| `JWT_SECRET` | API | *Random 48-byte URL-safe string* | **Yes** | HMAC key for signing user session tokens |
| `JWT_ALGORITHM` | API | `HS256` | No | Algorithm for JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | API | `60` | No | Token lifetime in minutes |
| `HONEYCORE_IMPL` | API | `stub` (P0-1) / `real` (P2+) | No | Implementation selector for cryptographic core |
| `VAULT_KDF_PROFILE` | API | `default` (or `demo`) | No | KDF cost profile (`default`, `server_lite`, `demo`) |
| `HONEYWORDS_K` | API | `10` | No | Number of candidate passwords generated per user |
| `HONEYWORDS_KDF_PROFILE` | API | `server_lite` | No | Argon2 cost profile for honeyword hashes |
| `ADMIN_USERNAME` | API | `admin` | No | Username for platform administrator |
| `ADMIN_LOGIN_PASSWORD` | API | *Random secure password* | **Yes** | Password for platform administrator |
| `KEY_WRAP_SECRET` | API | *Base64 32 random bytes* | **Yes** | Server KEK wrapping ECC user identity private keys |
| `HONEYCHECKER_URL` | API | `https://honeyvault-hc.onrender.com` | No | URL to Honeychecker service |
| `HONEYCHECKER_TRANSPORT` | API | `signed` (Render) / `plain` (Local) | No | Transport mechanism (`plain`, `mtls`, `signed`) |
| `HC_CLIENT_CERT_B64` | API | *Base64 PEM* | **Yes** | API client certificate for signed transport |
| `HC_CLIENT_KEY_B64` | API | *Base64 PEM* | **Yes** | API client private key for signed transport |
| `HC_DATABASE_URL` | Honeychecker | `postgresql+psycopg://...` | **Yes** | Dedicated Honeychecker database connection string |
| `HC_TRANSPORT` | Honeychecker | `signed` (Render) / `plain` (Local) | No | Must match `HONEYCHECKER_TRANSPORT` |
| `HC_ALLOWED_CLIENT_CN` | Honeychecker | `honeyvault-api` | No | Expected CN of API client certificate |
| `HC_TRUSTED_CA_CERT_B64` | Honeychecker | *Base64 PEM* | **Yes** | Trusted Root CA certificate for chain validation |
| `VITE_API_BASE_URL` | Frontend | `https://honeyvault-api.onrender.com` | No | Backend API endpoint URL |
| `VITE_USE_MOCKS` | Frontend | `false` | No | Toggle MSW mock API vs real backend |

---

## 7. "Warm Up Before Demo" Checklist

Render free-tier web services spin down after 15 minutes of inactivity, and Neon databases scale down to zero compute. If an evaluator accesses the site cold, the initial request may take 30–60 seconds while containers boot and databases resume.

### Pre-Demo Warmup Protocol (Execute 5–10 minutes before presenting):

1. **Ping Honeychecker Health Endpoint:**
   ```bash
   curl -i https://honeyvault-honeychecker.onrender.com/hc/health
   ```
   *Expected response:* HTTP 200 `{"status":"ok","service":"honeychecker","version":"...","db":"ok"}`

2. **Ping API Health Endpoint:**
   ```bash
   curl -i https://honeyvault-api.onrender.com/api/health
   ```
   *Expected response:* HTTP 200 `{"status":"ok","version":"...","honeycore_impl":"...","honeychecker":"ok"}`  
   *Note:* Ensure `"honeychecker": "ok"` in the response. If `"down"`, wait 10 seconds for the honeychecker container to finish starting.

3. **Ping Frontend Web App:**
   ```bash
   curl -i https://honeyvault.vercel.app/
   ```
   *Expected response:* HTTP 200 (HTML document delivered via Vercel Edge CDN).

4. **Test Demo Account Login in Browser:**
   - Navigate to `https://honeyvault.vercel.app/login`
   - Log in with Demo credentials
   - Perform a vault unlock to verify KDF computation and ensure Neon connection pool is warm.
