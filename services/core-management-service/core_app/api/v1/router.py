from fastapi import APIRouter

from core_app.api.v1 import donations, profiles, verification

api_router = APIRouter()
api_router.include_router(profiles.router)
api_router.include_router(donations.router)
api_router.include_router(verification.router)
