# IAM Service

Authentication, authorization, user accounts, roles, OTP, and login audit for the Give Away Platform.

## Local development

### Prerequisites

- Python 3.11+
- PostgreSQL with database `iam_db`

```sql
CREATE DATABASE iam_db;
```

### Setup

```bash
cd services/iam-service
cp .env.example .env
pip install -e .
alembic upgrade head
python scripts/seed_roles.py
uvicorn app.main:app --reload --port 8001
```

Swagger UI: http://localhost:8001/docs

## Structure

```
app/
├── main.py              # FastAPI entrypoint
├── config.py            # Settings
├── api/v1/              # HTTP routes
├── core/                # Business logic
├── core/security/       # JWT, password, refresh utilities
├── models/              # SQLAlchemy ORM (5 tables)
├── schemas/             # Pydantic DTOs
├── repositories/        # Database access
├── dependencies/        # FastAPI auth dependencies
├── db/                  # Session & base
├── events/              # Event publisher stub
└── middleware/          # Exception handlers
```

## FRD modules

| Module | Routes |
|--------|--------|
| Authentication | `/api/v1/auth/*` |
| OTP | `/api/v1/otp/*` |
| User management | `/api/v1/users/*` |
| Role management | `/api/v1/roles/*` |
| Login audit | `/api/v1/audit/*` |

## Default roles

- DONOR
- RECEIVER
- NGO
- SUPER_ADMIN (seed only; create first admin manually in DB or extend seed script)
