import asyncio

import asyncpg


async def main() -> None:
    conn = await asyncpg.connect("postgresql://postgres:0141@localhost:5432/postgres")
    for db in ("core_mgmt_db", "communication_db"):
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db}"')
            print(f"Created {db}")
        else:
            print(f"{db} already exists")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
