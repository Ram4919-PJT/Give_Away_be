"""Drop and recreate public schema for service databases (dev reset).

Usage:
    python scripts/reset_service_schemas.py
    python scripts/reset_service_schemas.py core_mgmt_db communication_db
"""

from __future__ import annotations

import asyncio
import sys

import asyncpg

POSTGRES_PASSWORDS = ["4919", "0141", "postgres", "root", "1234", "admin"]
DEFAULT_DATABASES = ("core_mgmt_db", "communication_db")


async def connect_admin() -> tuple[asyncpg.Connection, str]:
    for password in POSTGRES_PASSWORDS:
        try:
            conn = await asyncpg.connect(
                f"postgresql://postgres:{password}@localhost:5432/postgres"
            )
            return conn, password
        except Exception:
            continue
    raise RuntimeError("Could not connect to PostgreSQL on localhost:5432")


async def reset_schema(db_name: str, password: str) -> None:
    conn = await asyncpg.connect(
        f"postgresql://postgres:{password}@localhost:5432/{db_name}"
    )
    try:
        await conn.execute("DROP SCHEMA public CASCADE")
        await conn.execute("CREATE SCHEMA public")
        await conn.execute("GRANT ALL ON SCHEMA public TO postgres")
        await conn.execute("GRANT ALL ON SCHEMA public TO public")
        print(f"Reset schema: {db_name}")
    finally:
        await conn.close()


async def main(database_names: list[str]) -> int:
    _, password = await connect_admin()
    for db_name in database_names:
        await reset_schema(db_name, password)
    return 0


if __name__ == "__main__":
    targets = sys.argv[1:] or list(DEFAULT_DATABASES)
    raise SystemExit(asyncio.run(main(targets)))
