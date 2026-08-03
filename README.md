# Give Away Backend

Backend services for the Give Away platform.

## Services

| Service | Path | Status |
|---------|------|--------|
| IAM (auth, users, roles, OTP) | `services/iam-service/` | Active |

## Quick start (IAM)

```bash
cd services/iam-service
cp .env.example .env
# Edit .env — set DATABASE_URL and JWT_SECRET_KEY

pip install -r requirements.txt
alembic upgrade head
python scripts/seed_roles.py
uvicorn app.main:app --reload --port 8001
```

- API docs: http://localhost:8001/docs
- Health: http://localhost:8001/health

## Configuration

All IAM secrets and settings belong in **`services/iam-service/.env`**.  
Do not duplicate secrets in this root folder.

Install dependencies from root:

```bash
pip install -r requirements.txt
```
