"""Start the Give Away API gateway.

Usage (from give-away-backend/):
    python run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
IAM_DIR = ROOT / "services" / "iam-service"
CORE_DIR = ROOT / "services" / "core-management-service"
COMM_DIR = ROOT / "services" / "communication-service"

for path in (ROOT, IAM_DIR, CORE_DIR, COMM_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def main() -> None:
    from gateway.config import settings
    from main import app

    path_count = len(app.openapi().get("paths", {}))
    print(f"Gateway ready — {path_count} API paths registered")
    if path_count < 20:
        raise SystemExit(
            "Service routes missing from OpenAPI. Stop other servers on port 8000 and retry."
        )

    uvicorn.run(
        "main:app",
        host=settings.GATEWAY_HOST,
        port=settings.GATEWAY_PORT,
        reload=settings.GATEWAY_RELOAD,
        reload_dirs=[
            str(ROOT),
            str(IAM_DIR / "app"),
            str(CORE_DIR / "core_app"),
            str(COMM_DIR / "comm_app"),
        ],
    )


if __name__ == "__main__":
    main()

