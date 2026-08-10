import sys
from pathlib import Path
import asyncio

_ROOT = Path(r"d:\Aja\Give_away\Give_Away_be")
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "services" / "iam-service"))
sys.path.insert(0, str(_ROOT / "services" / "core-management-service"))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal as IamSessionLocal
from core_app.db.session import AsyncSessionLocal as CoreSessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.enums import RoleName, UserStatus
from core_app.models.profiles import DonorProfile, ReceiverProfile, NgoProfile
from core_app.models.enums import ProfileStatus
from app.core.security.password import hash_password

async def create_verified_users():
    users_to_create = [
        {"email": "verified_donor@test.com", "role": RoleName.DONOR, "mobile": "9999999901", "name": "Verified Donor"},
        {"email": "verified_receiver@test.com", "role": RoleName.RECEIVER, "mobile": "9999999902", "name": "Verified Receiver"},
        {"email": "verified_ngo@test.com", "role": RoleName.NGO, "mobile": "9999999903", "name": "Verified NGO"},
    ]
    
    password = hash_password("Test@1234")
    
    async with IamSessionLocal() as iam_db:
        # get roles
        roles = {}
        res = await iam_db.execute(select(Role))
        for r in res.scalars():
            roles[r.role_name] = r.role_id
            
        created_users = []
        for u in users_to_create:
            # check if exists
            res = await iam_db.execute(select(User).where(User.email == u["email"]))
            user = res.scalar_one_or_none()
            if not user:
                user = User(
                    email=u["email"],
                    mobile=u["mobile"],
                    full_name=u["name"],
                    password_hash=password,
                    role_id=roles[u["role"]],
                    status=UserStatus.ACTIVE
                )
                iam_db.add(user)
                await iam_db.flush()
            created_users.append({"user_id": user.user_id, "role": u["role"]})
            
        await iam_db.commit()
        
    async with CoreSessionLocal() as core_db:
        for u in created_users:
            if u["role"] == RoleName.DONOR:
                res = await core_db.execute(select(DonorProfile).where(DonorProfile.user_id == u["user_id"]))
                if not res.scalar_one_or_none():
                    core_db.add(DonorProfile(user_id=u["user_id"], status=ProfileStatus.ACTIVE, organization_name="Verified Donor Org"))
            elif u["role"] == RoleName.RECEIVER:
                res = await core_db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == u["user_id"]))
                if not res.scalar_one_or_none():
                    core_db.add(ReceiverProfile(user_id=u["user_id"], status=ProfileStatus.ACTIVE, household_size=4, monthly_income=5000.00))
            elif u["role"] == RoleName.NGO:
                res = await core_db.execute(select(NgoProfile).where(NgoProfile.user_id == u["user_id"]))
                if not res.scalar_one_or_none():
                    core_db.add(NgoProfile(user_id=u["user_id"], status=ProfileStatus.ACTIVE, registration_number="NGO123456", organization_name="Verified NGO Org"))
                    
        await core_db.commit()

if __name__ == "__main__":
    asyncio.run(create_verified_users())
    print("Verified users created successfully!")
