"""Huey task definitions for scheduled story events."""

import asyncio
import logging
import os

from huey import RedisHuey

logger = logging.getLogger(__name__)

# Initialize Huey with Redis
# Use environment variable directly to avoid circular imports with settings
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
huey = RedisHuey("argent", url=redis_url)


@huey.task()  # type: ignore[untyped-decorator]
def execute_story_event_task(
    event_id: str,
    player_id: str,
    context: dict,
) -> None:
    """
    Execute a story event (runs in Huey worker process).

    This is a sync function that wraps async handler execution.
    """
    from uuid import UUID

    from argent.scheduler.events import get_event
    from argent.scheduler.handlers import execute_handler

    logger.info("Executing scheduled event: %s for player %s", event_id, player_id)

    event = get_event(event_id)

    # Run the async handler in an event loop
    asyncio.run(execute_handler(event.handler, UUID(player_id), context))

    logger.info("Completed scheduled event: %s for player %s", event_id, player_id)
