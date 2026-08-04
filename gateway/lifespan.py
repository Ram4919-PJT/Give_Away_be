from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI


@asynccontextmanager
async def combined_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.main import lifespan as iam_lifespan
    from comm_app.main import lifespan as comm_lifespan
    from core_app.main import lifespan as core_lifespan

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(iam_lifespan(app))
        await stack.enter_async_context(core_lifespan(app))
        await stack.enter_async_context(comm_lifespan(app))
        yield
