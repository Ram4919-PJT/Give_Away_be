import logging

from shared.redis.events import publish_event

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes domain events to the shared Redis stream."""

    @staticmethod
    async def publish(event_name: str, payload: dict) -> None:
        await publish_event(event_name, payload)
