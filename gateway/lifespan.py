from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI

logger = logging.getLogger(__name__)

_consumer_tasks: list[asyncio.Task[None]] = []


async def _start_event_consumers() -> list[asyncio.Task[None]]:
    from shared.redis.client import get_redis

    if get_redis() is None:
        return []

    from comm_app.events.consumer import run_communication_consumer
    from core_app.events.consumer import run_core_consumer

    tasks = [
        asyncio.create_task(run_core_consumer(), name="core-event-consumer"),
        asyncio.create_task(run_communication_consumer(), name="comm-event-consumer"),
    ]
    logger.info("Started %s Redis event consumer(s)", len(tasks))
    return tasks


async def _stop_event_consumers(tasks: list[asyncio.Task[None]]) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


@asynccontextmanager
async def combined_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.main import lifespan as iam_lifespan
    from comm_app.main import lifespan as comm_lifespan
    from core_app.main import lifespan as core_lifespan
    from shared.redis.client import close_redis, init_redis

    await init_redis()
    consumer_tasks = await _start_event_consumers()

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(iam_lifespan(app))
        await stack.enter_async_context(core_lifespan(app))
        await stack.enter_async_context(comm_lifespan(app))
        yield

    await _stop_event_consumers(consumer_tasks)
    await close_redis()
