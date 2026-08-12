"""Seed iam_db, core_mgmt_db, and communication_db with neat demo data.

Uses:
  scripts/seed_iam.sql
  scripts/seed_core.sql
  scripts/seed_communication.sql

Passwords are hashed with the same SHA256+bcrypt scheme as IAM login.
Default password for all seeded users: Test@1234
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

import asyncpg
import bcrypt

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PASSWORD = "Test@1234"
POSTGRES_PASSWORDS = ["0141", "4919", "postgres", "root", "1234", "admin"]

DBS = {
    "iam_db": SCRIPT_DIR / "seed_iam.sql",
    "core_mgmt_db": SCRIPT_DIR / "seed_core.sql",
    "communication_db": SCRIPT_DIR / "seed_communication.sql",
}

IAM_TRUNCATE = """
TRUNCATE TABLE
  otp_verifications,
  refresh_tokens,
  login_audit,
  users,
  roles
RESTART IDENTITY CASCADE;
"""

CORE_TRUNCATE = """
TRUNCATE TABLE
  allocations,
  disbursements,
  fund_ledger,
  pickup_schedules,
  inventory_transactions,
  inventory_items,
  application_status_history,
  donation_status_history,
  ngo_fund_requests,
  ngo_item_requests,
  assistance_applications,
  item_donations,
  money_donations,
  fund_pools,
  rejection_reasons,
  verification_status_history,
  verification_documents,
  verification_requests,
  beneficiaries,
  programs,
  ngo_profiles,
  receiver_profiles,
  donor_profiles,
  addresses
RESTART IDENTITY CASCADE;
"""

COMM_TRUNCATE = """
TRUNCATE TABLE
  notification_delivery_logs,
  user_notification_preferences,
  notifications,
  notification_templates
RESTART IDENTITY CASCADE;
"""

TRUNCATE_SQL = {
    "iam_db": IAM_TRUNCATE,
    "core_mgmt_db": CORE_TRUNCATE,
    "communication_db": COMM_TRUNCATE,
}


def hash_password(plain: str) -> str:
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")


async def connect_admin() -> tuple[asyncpg.Connection, str]:
    for pwd in POSTGRES_PASSWORDS:
        try:
            conn = await asyncpg.connect(f"postgresql://postgres:{pwd}@localhost:5432/postgres")
            return conn, pwd
        except Exception:
            continue
    raise RuntimeError("Could not connect to PostgreSQL as postgres on localhost:5432")


async def ensure_databases(admin: asyncpg.Connection) -> None:
    for db_name in DBS:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database {db_name}")
        else:
            print(f"Database {db_name} already exists")


async def seed_one(db_name: str, password: str, pwd_hash: str) -> None:
    sql_path = DBS[db_name]
    if not sql_path.exists():
        raise FileNotFoundError(sql_path)

    sql = sql_path.read_text(encoding="utf-8").replace("__PASSWORD_HASH__", pwd_hash)
    conn = await asyncpg.connect(f"postgresql://postgres:{password}@localhost:5432/{db_name}")
    try:
        await conn.execute(TRUNCATE_SQL[db_name])
        await conn.execute(sql)
        print(f"Seeded {db_name} from {sql_path.name}")
    finally:
        await conn.close()


async def verify_counts(password: str) -> None:
    checks = {
        "iam_db": ["roles", "users"],
        "core_mgmt_db": ["programs", "donor_profiles", "receiver_profiles", "ngo_profiles", "money_donations"],
        "communication_db": ["notifications", "notification_templates"],
    }
    print("\nRow counts:")
    for db_name, tables in checks.items():
        conn = await asyncpg.connect(f"postgresql://postgres:{password}@localhost:5432/{db_name}")
        try:
            parts = []
            for table in tables:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                parts.append(f"{table}={count}")
            print(f"  {db_name}: " + ", ".join(parts))
        finally:
            await conn.close()


async def main() -> None:
    print("Give Away — seeding service databases...")
    admin, password = await connect_admin()
    print(f"Connected with postgres password '{password}'")
    try:
        await ensure_databases(admin)
    finally:
        await admin.close()

    pwd_hash = hash_password(DEFAULT_PASSWORD)
    for db_name in DBS:
        try:
            await seed_one(db_name, password, pwd_hash)
        except Exception as exc:
            print(f"ERROR seeding {db_name}: {exc}")
            sys.exit(1)

    await verify_counts(password)
    print("\nDone.")
    print(f"All test users password: {DEFAULT_PASSWORD}")
    print("See scripts/TEST_LOGINS.md for account list.")


if __name__ == "__main__":
    asyncio.run(main())
