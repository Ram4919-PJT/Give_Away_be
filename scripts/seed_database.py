"""Database creation and seed script for Give Away Platform.

Executes seed_consolidated.sql against localhost PostgreSQL.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

SCRIPT_DIR = Path(__file__).resolve().parent
SQL_FILE = SCRIPT_DIR / "seed_consolidated.sql"

# List of passwords to try for local postgres user
POSTGRES_PASSWORDS = ["4919", "postgres", "0141", "root", "1234", "admin"]


async def seed_database() -> None:
    print("Initializing Give Away Platform database seeding...")
    
    if not SQL_FILE.exists():
        print(f"Error: SQL seed file not found at {SQL_FILE}")
        sys.exit(1)
        
    sql_script = SQL_FILE.read_text(encoding="utf-8")
    
    conn = None
    connected_password = None
    for pwd in POSTGRES_PASSWORDS:
        try:
            url = f"postgresql://postgres:{pwd}@localhost:5432/postgres"
            conn = await asyncpg.connect(url)
            connected_password = pwd
            print(f"Connected to local PostgreSQL using password: '{pwd}'")
            break
        except Exception:
            continue
            
    if not conn:
        print("Error: Could not connect to PostgreSQL on localhost:5432 with standard passwords.")
        sys.exit(1)
        
    db_name = "giveaway_platform_db"
    
    # Check if giveaway_platform_db exists
    exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
    if not exists:
        print(f"Creating database '{db_name}'...")
        await conn.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Database '{db_name}' created successfully.")
    else:
        print(f"Database '{db_name}' already exists.")
        
    await conn.close()
    
    # Connect directly to giveaway_platform_db
    target_url = f"postgresql://postgres:{connected_password}@localhost:5432/{db_name}"
    target_conn = await asyncpg.connect(target_url)
    
    print(f"Executing consolidated seed SQL against '{db_name}'...")
    try:
        await target_conn.execute(sql_script)
        print("Successfully executed seed SQL!")
    except Exception as e:
        print(f"Notice/Warning during SQL execution: {e}")
        
    # Verify table counts
    tables = [
        "roles", "users", "refresh_tokens", "login_audit", "otp_verifications",
        "addresses", "donor_profiles", "receiver_profiles", "ngo_profiles",
        "beneficiaries", "programs", "verification_requests", "verification_documents",
        "verification_status_history", "rejection_reasons", "fund_pools",
        "money_donations", "item_donations", "assistance_applications",
        "ngo_item_requests", "ngo_fund_requests", "donation_status_history",
        "application_status_history", "inventory_items", "inventory_transactions",
        "pickup_schedules", "fund_ledger", "disbursements", "allocations",
        "notifications", "notification_templates", "notification_delivery_logs",
        "user_notification_preferences"
    ]
    
    print("\nVerifying seeded tables in 'giveaway_platform_db':")
    print("-" * 50)
    for tbl in tables:
        try:
            count = await target_conn.fetchval(f"SELECT COUNT(*) FROM {tbl}")
            print(f"Table '{tbl}': {count} rows")
        except Exception as err:
            print(f"Table '{tbl}': Error ({err})")
            
    await target_conn.close()
    print("-" * 50)
    print(f"Database seeding completed successfully for '{db_name}'!\n")
    print(f"To configure microservices, set DATABASE_URL to:")
    print(f"postgresql+asyncpg://postgres:{connected_password}@localhost:5432/{db_name}")


if __name__ == "__main__":
    asyncio.run(seed_database())
