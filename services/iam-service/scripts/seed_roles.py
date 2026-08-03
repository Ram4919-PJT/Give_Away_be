"""Seed default IAM roles."""

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.enums import RoleName
from app.models.role import Role

ROLES = [
    (RoleName.DONOR, "Donor who contributes money or items"),
    (RoleName.RECEIVER, "Individual receiving financial assistance"),
    (RoleName.NGO, "NGO partner organization"),
    (RoleName.SUPER_ADMIN, "Platform super administrator"),
]


async def seed_roles() -> None:
    async with AsyncSessionLocal() as session:
        for role_name, description in ROLES:
            existing = await session.execute(
                select(Role).where(Role.role_name == role_name)
            )
            if existing.scalar_one_or_none():
                continue

            session.add(Role(role_name=role_name, description=description))

        await session.commit()
        print("Roles seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_roles())
