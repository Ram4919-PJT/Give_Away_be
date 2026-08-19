# Database migrations

Give Away uses a strict separation between **application data access** and **schema evolution**.

## Architecture

```
Application services
        ↓
SQLAlchemy ORM          ← CRUD, queries, relationships, business data
        ↓
PostgreSQL              ← persistent storage

Schema changes (separate path):
Alembic                 ← tables, columns, indexes, constraints, versioning
        ↓
PostgreSQL
```

| Component | Purpose |
|-----------|---------|
| **SQLAlchemy ORM** | Models, CRUD, queries, relationships, application data operations |
| **Alembic** | Create/alter tables, columns, indexes, constraints; migration history (`alembic_version`) |
| **PostgreSQL** | Stores data and schema |

ORM models define the **intended** schema for the application. Alembic revisions apply **auditable, versioned** DDL to PostgreSQL.

## Services and databases

| Service | Database | Alembic location | Current head (consolidated) |
|---------|----------|------------------|----------------------------|
| iam-service | `iam_db` | `services/iam-service/alembic/` | `001` |
| core-management-service | `core_mgmt_db` | `services/core-management-service/alembic/` | `011_ngo_program_extensions` |
| communication-service | `communication_db` | `services/communication-service/alembic/` | `003_email_delivery_logs` |

## Official workflow for schema changes

1. **Modify** the SQLAlchemy ORM model in the appropriate service.
2. **Generate** an Alembic revision:

   ```bash
   cd services/<service-name>
   alembic revision --autogenerate -m "short_description"
   ```

3. **Review** the generated migration manually (autogenerate is not infallible).
4. **Test** on a **disposable** database:

   ```bash
   alembic upgrade head
   ```

5. **Verify** schema (tables, columns, indexes, constraints).
6. **Commit** the ORM change and Alembic revision together.

Never commit model changes without the matching migration (or an explicit decision that no DDL is required).

## Fresh development database setup

From `Give_Away_be`:

```bash
python scripts/setup_databases.py
```

This:

1. Runs `alembic upgrade head` for all three services (schema only via Alembic).
2. Seeds demo data via `scripts/seed_*.sql` (data only, not DDL).

Optional destructive reset for core/communication during local dev:

```bash
python scripts/setup_databases.py --reset-core-comm
```

This drops and recreates the `public` schema for `core_mgmt_db` and `communication_db`, then runs Alembic and seeds.

## Production and staging

### Existing database (already has schema)

1. Verify live schema and `SELECT version_num FROM alembic_version`.
2. If schema already matches a revision but version is behind, use **`alembic stamp <revision>`** only after explicit verification (stamp does not run DDL).
3. If migrations are genuinely unapplied, use **`alembic upgrade head`**.

### Fresh database

```bash
alembic upgrade head
```

per service, in dependency order (IAM, core, communication are independent databases).

### Never in production

- `Base.metadata.create_all()` for schema setup
- Legacy `scripts/ensure_*.sql` files
- Legacy `scripts/run_*_migration.py` runners
- Manual `ALTER TABLE` / `CREATE TABLE` outside Alembic

## Prohibited practices

| Practice | Why |
|----------|-----|
| New `scripts/ensure_*.sql` schema files | Bypasses Alembic history |
| New `scripts/run_*_migration.py` runners | Duplicate migration path |
| Manual DDL in production | Untracked, non-repeatable |
| `create_all()` for production schema | Bypasses Alembic |
| Running legacy SQL or runners on Alembic-managed DBs | Risk of duplicate objects / drift |

Historical files live under `scripts/legacy_sql_migrations/` for reference only. See that README for SQL → Alembic mapping.

## IAM `init_db()` (test-only)

`services/iam-service/app/db/init_db.py` is **not** a production schema tool.

`create_all()` runs only when:

```bash
IAM_ALLOW_CREATE_ALL_FOR_TESTS=1
```

Otherwise `init_db()` raises an error directing developers to Alembic.

## Migration hygiene check (CI / pre-commit)

Run from `Give_Away_be`:

```bash
python scripts/check_migration_hygiene.py
```

This fails if:

1. New `scripts/ensure_*.sql` files appear outside `legacy_sql_migrations/`
2. New `scripts/run_*_migration.py` files are added
3. New `create_all()` usage appears outside allowed test-only paths

Install optional pre-commit hook (repository root or `Give_Away_be`):

```bash
pip install pre-commit
pre-commit install
```

See `.pre-commit-config.yaml`.

## Legacy consolidation reference

Manual SQL migrations were consolidated into Alembic revisions `007`–`011` (core) and `003` (communication). Details: `scripts/legacy_sql_migrations/README.md`.

## Quick reference

```bash
# Current revision
alembic current

# Apply pending migrations
alembic upgrade head

# New migration (after model change)
alembic revision --autogenerate -m "add_foo_column"

# Stamp only (existing DB already has schema — use with care)
alembic stamp <revision_id>
```
