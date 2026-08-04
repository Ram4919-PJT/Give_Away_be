from fastapi import Request
from fastapi.responses import JSONResponse

from core_app.core.exceptions import AppError


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )
