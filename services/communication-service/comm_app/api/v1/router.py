from fastapi import APIRouter

from comm_app.api.v1 import notifications, preferences

api_router = APIRouter()
api_router.include_router(notifications.router)
api_router.include_router(preferences.router)
