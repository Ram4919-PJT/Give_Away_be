"""Set up all Give Away service databases: migrate + seed.

Schema migrations are managed exclusively by Alembic per service (`alembic upgrade head`).
Do not run `scripts/run_*_migration.py` or legacy SQL under `scripts/legacy_sql_migrations/`.
See `docs/DATABASE_MIGRATIONS.md`.

Usage (from Give_Away_be):
    python scripts/setup_databases.py

Options:
    python scripts/setup_databases.py --reset-core-comm
        Also wipe core_mgmt_db and communication_db schemas before migrating.
        Use when regenerating Core/Communication migrations in development.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SERVICES = (
    BACKEND_ROOT / "services" / "iam-service",
    BACKEND_ROOT / "services" / "core-management-service",
    BACKEND_ROOT / "services" / "communication-service",
)


def run_migrations() -> None:
    for service_dir in SERVICES:
        print(f"\n==> Alembic upgrade: {service_dir.name}")
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=service_dir,
            check=True,
        )


async def reset_core_and_comm() -> None:
    from reset_service_schemas import main as reset_main

    await reset_main(["core_mgmt_db", "communication_db"])


async def seed_all() -> None:
    from seed_database import connect_admin, ensure_databases, hash_password, seed_one

    admin, password = await connect_admin()
    try:
        await ensure_databases(admin)
    finally:
        await admin.close()

    pwd_hash = hash_password("Test@1234")
    for db_name in ("iam_db", "core_mgmt_db", "communication_db"):
        print(f"\n==> Seeding {db_name}")
        await seed_one(db_name, password, pwd_hash)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate and seed Give Away databases")
    parser.add_argument(
        "--reset-core-comm",
        action="store_true",
        help="Drop and recreate schemas for core_mgmt_db and communication_db before migrating",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("Give Away — full database setup")

    try:
        if args.reset_core_comm:
            print("\n==> Resetting core_mgmt_db and communication_db schemas")
            asyncio.run(reset_core_and_comm())

        run_migrations()
        asyncio.run(seed_all())
    except subprocess.CalledProcessError as exc:
        print(f"Migration failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1

    print("\nSetup complete.")
    print("Test login: admin@giveaway.org / Test@1234")
    print("Start backend: python run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
