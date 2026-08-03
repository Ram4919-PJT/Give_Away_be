"""Seed default IAM roles (idempotent).

Run from the iam-service directory:
    python scripts/seed_roles.py
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.enums import RoleName
from app.models.role import Role

ROLES: list[tuple[RoleName, str]] = [
    (RoleName.DONOR, "Donor who contributes money or items"),
    (RoleName.RECEIVER, "Individual receiving financial assistance"),
    (RoleName.NGO, "NGO partner organization"),
    (RoleName.SUPER_ADMIN, "Platform super administrator"),
]


async def seed_roles() -> None:
    created: list[str] = []
    skipped: list[str] = []

    async with AsyncSessionLocal() as session:
        try:
            for role_name, description in ROLES:
                result = await session.execute(
                    select(Role).where(Role.role_name == role_name)
                )
                if result.scalar_one_or_none():
                    skipped.append(role_name.value)
                    continue

                session.add(Role(role_name=role_name, description=description))
                created.append(role_name.value)

            await session.commit()
        except Exception as exc:
            await session.rollback()
            print(f"Error seeding roles: {exc}", file=sys.stderr)
            raise

    if created:
        print(f"Created roles: {', '.join(created)}")
    if skipped:
        print(f"Already exist: {', '.join(skipped)}")
    if not created and skipped:
        print("All roles already seeded.")


if __name__ == "__main__":
    asyncio.run(seed_roles())
