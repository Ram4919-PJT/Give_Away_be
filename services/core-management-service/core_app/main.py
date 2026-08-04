from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.v1.router import api_router
from core_app.config import settings
from core_app.core.exceptions import AppError
from core_app.db.session import engine, get_db
from core_app.middleware.exception_handlers import app_error_handler, value_error_handler

health_router = APIRouter(tags=["Core - Health"])


@health_router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.APP_NAME, "env": settings.ENV}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


def register_core(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.include_router(health_router, prefix="/api/v1/core")
    app.include_router(api_router, prefix="/api/v1/core")
