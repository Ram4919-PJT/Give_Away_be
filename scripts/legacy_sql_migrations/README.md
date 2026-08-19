# Legacy SQL schema migrations (historical only)

These files are **historical references**. They are **not** part of the active migration system.

**Do not execute these scripts** against Alembic-managed databases (including any database where `alembic upgrade head` has been applied through the current revision heads).

## Active migration system

| Layer | Responsibility |
|-------|----------------|
| **SQLAlchemy ORM** | Application data operations (CRUD, queries, relationships) |
| **Alembic** | Database schema migrations (tables, columns, indexes, constraints) |
| **PostgreSQL** | Persistent storage |

**Alembic is the only supported schema migration mechanism.**

Official documentation: [`docs/DATABASE_MIGRATIONS.md`](../../docs/DATABASE_MIGRATIONS.md)

## Schema SQL → Alembic revision mapping

| Legacy SQL file | Alembic revision | Service |
|-----------------|------------------|---------|
| `ensure_kyc_verification_columns.sql` | `007_kyc_verification_extensions` | core-management-service |
| `ensure_receiver_kyc_phase2.sql` | `008_receiver_kyc_mobile_otp` | core-management-service |
| `ensure_assistance_columns.sql` | `009_assistance_review_fields` | core-management-service |
| `ensure_assistance_disbursement_columns.sql` | `010_assistance_disbursement` | core-management-service |
| `ensure_ngo_dashboard_columns.sql` | `011_ngo_program_extensions` | core-management-service |
| `ensure_email_delivery_table.sql` | `003_email_delivery_logs` | communication-service |

## Other historical files (not schema migration paths)

| File | Notes |
|------|--------|
| `ensure_recurring_gifts.sql` | Legacy seed/data script; `recurring_gifts` table is created by Alembic `64ee791c8f04` |
| `seed_consolidated.sql` | Deprecated monolithic bootstrap (CREATE TABLE + seed); use Alembic + `scripts/seed_*.sql` instead |

## Deprecated migration runners (do not run)

These scripts in `scripts/` exit immediately with an error. They must not be used:

- `run_kyc_migration.py`
- `run_receiver_kyc_phase2_migration.py`
- `run_assistance_migration.py`
- `run_assistance_disbursement_migration.py`
- `run_ngo_dashboard_migration.py`
- `run_email_migration.py`

Use per service:

```bash
cd services/<service-name>
alembic upgrade head
```

## Removal policy

Keep these files until development, test, staging, and production verification are complete and backups are confirmed. Do not delete without team approval.
