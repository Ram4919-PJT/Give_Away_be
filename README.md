# Give Away Backend

Backend for the Give Away platform — **one API gateway** on port **8000** that registers three microservices.

## Architecture

```
Web / Mobile  →  API Gateway (:8000)
                    ├── IAM Service           → iam_db
                    ├── Core Management       → core_mgmt_db
                    └── Communication         → communication_db
```

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/docs | Swagger UI (all services) |
| http://127.0.0.1:8000/gateway/health | Gateway health |
| http://127.0.0.1:8000/health | IAM health |
| http://127.0.0.1:8000/api/v1/core/health | Core health |
| http://127.0.0.1:8000/api/v1/notifications/health | Communication health |

> Use `127.0.0.1` in the browser, not `0.0.0.0`.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** running locally
- **Redis** (optional but recommended) — `docker compose up -d redis`
- **pip**

## First-time setup

### 1. Create PostgreSQL databases

Create these databases (via pgAdmin, psql, or the helper script):

| Database | Service |
|----------|---------|
| `iam_db` | IAM |
| `core_mgmt_db` | Core Management |
| `communication_db` | Communication |

Helper script (edit the postgres password inside if needed):

```powershell
cd give-away-backend
pip install asyncpg
python scripts/create_databases.py
```

Also create `iam_db` manually if it does not exist yet.

### 2. Configure environment files

Copy and edit `.env` files — **JWT_SECRET_KEY must be the same** in all three services.

```powershell
cd give-away-backend
copy .env.example .env

cd services\iam-service
copy .env.example .env

cd ..\core-management-service
copy .env.example .env

cd ..\communication-service
copy .env.example .env
```

Update in each service `.env`:

- `DATABASE_URL` — your postgres user/password
- `JWT_SECRET_KEY` — same value in IAM, Core, and Communication

### 3. Install Python dependencies

From the backend root:

```powershell
cd give-away-backend

pip install -r requirements.txt
pip install -r services\core-management-service\requirements.txt
pip install -r services\communication-service\requirements.txt
```

### 4. Run database migrations

```powershell
cd services\iam-service
alembic upgrade head
python scripts\seed_roles.py

cd ..\core-management-service
alembic upgrade head

cd ..\communication-service
alembic upgrade head

cd ..\..
```

### 5. Start Redis (recommended)

```powershell
cd Give_Away_be
docker compose up -d redis
```

Set `REDIS_ENABLED=false` in `.env` to run without Redis (events log locally; rate limits skipped).

## Start the backend

```powershell
cd give-away-backend
python run.py
```

You should see:

```
Gateway ready — 33 API paths registered
```

Alternative:

```powershell
uvicorn main:app --reload --port 8000
```

### Troubleshooting

- **Port 8000 already in use:** End leftover `python` processes in Task Manager, then run again.
- **Only 21 routes in Swagger:** An old gateway is still running — kill it and restart.
- **Swagger:** Open http://127.0.0.1:8000/docs

## Test credentials

Seed neat demo data into all three service databases:

```powershell
cd Give_Away_be
python scripts\seed_database.py
```

Password for all seeded accounts: **`Test@1234`**

| Email | Role | State |
|-------|------|-------|
| `admin@giveaway.org` | Admin | — |
| `ananya.donor@gmail.com` | Donor | Verified |
| `pending.donor@gmail.com` | Donor | Pending |
| `ramesh.receiver@gmail.com` | Receiver | Verified |
| `sita.receiver@gmail.com` | Receiver | Pending |
| `contact@hopefoundation.org` | NGO | Verified |
| `info@careshare.org` | NGO | Pending |

Full list: [`scripts/TEST_LOGINS.md`](scripts/TEST_LOGINS.md)

Mobile must be a 10-digit Indian number starting with 6–9 (e.g. `9876543210`).

## API route map

| Prefix | Service | Examples |
|--------|---------|----------|
| `/api/v1/auth/*` | IAM | login, register, refresh |
| `/api/v1/users/*` | IAM | user profile, list users |
| `/api/v1/core/*` | Core | profiles, donations, verification |
| `/api/v1/notifications/*` | Communication | notifications, preferences |

## Project layout

```
give-away-backend/
├── main.py                 # Gateway entry (creates FastAPI app)
├── run.py                  # Start gateway: python run.py
├── gateway/
│   ├── config.py           # Gateway host, port, CORS
│   └── lifespan.py         # Combined DB shutdown for all services
├── scripts/
│   └── create_databases.py
└── services/
    ├── iam-service/        # Auth, users, roles (package: app)
    ├── core-management-service/   # Business data (package: core_app)
    └── communication-service/     # Notifications (package: comm_app)
```

## Configuration

| File | Purpose |
|------|---------|
| `.env` | Gateway host, port, CORS |
| `services/iam-service/.env` | IAM database, JWT, OTP |
| `services/core-management-service/.env` | Core database, JWT |
| `services/communication-service/.env` | Communication database, JWT |

## Redis

Shared Redis infrastructure lives in `shared/redis/` and is configured in the root `.env`.

| Feature | Redis usage |
|---------|-------------|
| Events | Stream `giveaway:events` — IAM publishes, Core + Communication consume |
| Login rate limit | `iam:rate:login:{email}` — 5 attempts / 15 min |
| OTP rate limit | `iam:rate:otp:{identifier}` — 3 attempts / 10 min |
| Unread notifications | `comm:unread:{user_id}` counter |

**Event flow:** `user.registered` → Core creates profile stub + Communication sends welcome notification.

Check Redis status: `GET /gateway/health` → `redis_connected: true`

```
Give_Away_be/
├── shared/redis/           # Shared client, events, rate limits
├── docker-compose.yml      # Redis for local dev
└── gateway/lifespan.py     # Connects Redis + starts consumers
```
