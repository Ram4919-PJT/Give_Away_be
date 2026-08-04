# IAM Service

Authentication, authorization, user accounts, roles, OTP, and login audit for the Give Away Platform.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ with database `iam_db`

```sql
CREATE DATABASE iam_db;
```

## Setup

```bash
cd services/iam-service
cp .env.example .env
# Edit .env — set DATABASE_URL, JWT_SECRET_KEY

pip install -r requirements.txt
alembic upgrade head
python scripts/seed_roles.py
```

Run via the **API gateway** (recommended):

```bash
cd ../..
python run.py
```

Or run IAM standalone for development:

```bash
uvicorn app.main:app --reload --port 8001
```

| URL (via gateway :8000) | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | Secret for signing access tokens (min 32 chars) |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `OTP_LOG_TO_CONSOLE` | Print OTP codes to console in dev |

See `.env.example` for the full list.

## API modules

| Module | Prefix |
|--------|--------|
| Authentication | `/api/v1/auth` |
| OTP | `/api/v1/otp` |
| Users | `/api/v1/users` |
| Roles | `/api/v1/roles` |
| Login audit | `/api/v1/audit` |

## Default roles

Seeded by `python scripts/seed_roles.py`:

- `DONOR` — contributes money or items
- `RECEIVER` — receives financial assistance
- `NGO` — partner organization
- `SUPER_ADMIN` — platform administrator (create user manually or via register + DB update)

## Project structure

```
app/
├── main.py              # FastAPI app & middleware
├── config.py            # Settings from .env
├── api/v1/              # Route handlers
├── core/                # Business logic
├── core/security/       # JWT, passwords, refresh tokens
├── models/              # SQLAlchemy ORM
├── schemas/             # Pydantic request/response models
├── repositories/        # Database access layer
├── dependencies/        # Auth & RBAC dependencies
├── db/                  # Engine & sessions
├── events/              # Event publisher (stub)
└── middleware/          # Exception handlers
scripts/
└── seed_roles.py        # Seed default roles
```

## Development

```bash
pip install -r requirements-dev.txt
pytest
```
