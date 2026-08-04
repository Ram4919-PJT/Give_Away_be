import logging

logger = logging.getLogger(__name__)


class EventPublisher:
    """Stub publisher for development. Replace with Redis/RabbitMQ later."""

    @staticmethod
    async def publish(event_name: str, payload: dict) -> None:
        logger.info("Event published: %s payload=%s", event_name, payload)
