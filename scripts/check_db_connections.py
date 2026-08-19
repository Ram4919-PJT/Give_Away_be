"""Quick check of PostgreSQL connectivity for all Give Away databases."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SERVICE_ENVS = {
    "IAM": BACKEND_ROOT / "services" / "iam-service" / ".env",
    "Core": BACKEND_ROOT / "services" / "core-management-service" / ".env",
    "Communication": BACKEND_ROOT / "services" / "communication-service" / ".env",
}

DATABASES = ["postgres", "iam_db", "core_mgmt_db", "communication_db"]
DEFAULT_PASSWORDS = ["4919", "0141", "postgres", "root", "1234", "admin"]


def parse_database_url(env_path: Path) -> str | None:
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip()
    return None


async def connect_with_password(password: str) -> asyncpg.Connection:
    return await asyncpg.connect(
        f"postgresql://postgres:{password}@localhost:5432/postgres",
        timeout=5,
    )


async def test_database(password: str, db_name: str) -> tuple[bool, str]:
    try:
        conn = await asyncpg.connect(
            f"postgresql://postgres:{password}@localhost:5432/{db_name}",
            timeout=5,
        )
        try:
            await conn.execute("SELECT 1")
            if db_name != "postgres":
                tables = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
                return True, f"connected, {tables} tables in public schema"
            return True, "connected"
        finally:
            await conn.close()
    except Exception as exc:
        return False, str(exc)


async def test_sqlalchemy_urls() -> None:
    print("\n=== SQLAlchemy settings from service .env files ===")
    sys.path.insert(0, str(BACKEND_ROOT / "services" / "iam-service"))
    sys.path.insert(0, str(BACKEND_ROOT / "services" / "core-management-service"))
    sys.path.insert(0, str(BACKEND_ROOT / "services" / "communication-service"))

    checks = [
        ("IAM", "app.config", "settings"),
        ("Core", "core_app.config", "settings"),
        ("Communication", "comm_app.config", "settings"),
    ]

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    for label, module_name, attr in checks:
        module = __import__(module_name, fromlist=[attr])
        settings = getattr(module, attr)
        url = settings.DATABASE_URL
        try:
            engine = create_async_engine(url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            print(f"{label:15} OK     {url}")
        except Exception as exc:
            print(f"{label:15} FAIL   {url}")
            print(f"                 {exc}")


async def main() -> int:
    print("Give Away — database connection check\n")

    password: str | None = None
    for candidate in DEFAULT_PASSWORDS:
        try:
            conn = await connect_with_password(candidate)
            await conn.close()
            password = candidate
            print(f"PostgreSQL admin login OK (password: {candidate})\n")
            break
        except Exception:
            continue

    if password is None:
        print("FAIL: Could not connect to PostgreSQL on localhost:5432 as user postgres")
        print("Tried passwords:", ", ".join(DEFAULT_PASSWORDS))
        return 1

    print("=== Direct database connections ===")
    all_ok = True
    for db_name in DATABASES:
        ok, detail = await test_database(password, db_name)
        status = "OK" if ok else "FAIL"
        print(f"{db_name:20} {status:6} {detail}")
        if not ok:
            all_ok = False

    print("\n=== Service .env DATABASE_URL values ===")
    for label, env_path in SERVICE_ENVS.items():
        url = parse_database_url(env_path)
        if url:
            print(f"{label:15} {url}")
        else:
            print(f"{label:15} MISSING .env or DATABASE_URL")
            all_ok = False

    try:
        await test_sqlalchemy_urls()
    except Exception as exc:
        print(f"\nSQLAlchemy check error: {exc}")
        all_ok = False

    print()
    if all_ok:
        print("All database connections look good.")
        return 0

    print("Some database checks failed. See details above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
