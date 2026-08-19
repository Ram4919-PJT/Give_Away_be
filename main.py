from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_ROOT = Path(__file__).resolve().parent
_IAM_DIR = _ROOT / "services" / "iam-service"
_CORE_DIR = _ROOT / "services" / "core-management-service"
_COMM_DIR = _ROOT / "services" / "communication-service"

for _entry in (_ROOT, _IAM_DIR, _CORE_DIR, _COMM_DIR):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from app.main import register_iam  # noqa: E402
from comm_app.main import register_communication  # noqa: E402
from core_app.main import register_core  # noqa: E402
from gateway.config import settings  # noqa: E402
from gateway.lifespan import combined_lifespan  # noqa: E402


def create_gateway() -> FastAPI:
    gateway = FastAPI(
        title="Give Away API Gateway",
        version="1.0.0",
        description="Unified API entry point for Give Away platform services.",
        lifespan=combined_lifespan,
    )

    gateway.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uploads_dir = _ROOT / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    gateway.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @gateway.get("/gateway/health", tags=["Gateway"])
    async def gateway_health() -> dict[str, str | int]:
        return {
            "status": "ok",
            "gateway": "Give Away API Gateway",
            "port": settings.GATEWAY_PORT,
        }

    register_iam(gateway)
    register_core(gateway)
    register_communication(gateway)

    path_count = len(gateway.openapi().get("paths", {}))
    if path_count < 20:
        raise RuntimeError(
            f"Service routes failed to register (found {path_count} paths). "
            "Check services/* imports."
        )

    gateway.openapi_schema = None

    return gateway


app = create_gateway()
