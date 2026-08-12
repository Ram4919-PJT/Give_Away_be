"""Create the three service databases if missing."""

from __future__ import annotations

import asyncio

import asyncpg

POSTGRES_PASSWORDS = ["0141", "4919", "postgres", "root", "1234", "admin"]
DATABASES = ("iam_db", "core_mgmt_db", "communication_db")


async def main() -> None:
    conn = None
    for pwd in POSTGRES_PASSWORDS:
        try:
            conn = await asyncpg.connect(f"postgresql://postgres:{pwd}@localhost:5432/postgres")
            print(f"Connected with password '{pwd}'")
            break
        except Exception:
            continue
    if conn is None:
        raise SystemExit("Could not connect to PostgreSQL")

    try:
        for db in DATABASES:
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db)
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db}"')
                print(f"Created {db}")
            else:
                print(f"{db} already exists")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
