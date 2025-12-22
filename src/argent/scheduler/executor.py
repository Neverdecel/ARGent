"""Story event execution with mode-aware scheduling."""

import logging
import random
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.models.player import Player
from argent.scheduler.events import (
    DelayRange,
    EventTrigger,
    StoryEvent,
    get_event,
    get_events_after,
    get_events_triggered_by,
)

logger = logging.getLogger(__name__)


class EventExecutor(Protocol):
    """Protocol for event execution strategies."""

    async def execute(
        self,
        event: StoryEvent,
        player_id: UUID,
        context: dict[str, Any],
    ) -> None:
        """Execute or schedule the event."""
        ...


class ImmediateExecutor:
    """Execute events immediately (web_only mode, testing)."""

    async def execute(
        self,
        event: StoryEvent,
        player_id: UUID,
        context: dict[str, Any],
    ) -> None:
        """Execute event handler immediately."""
        from argent.scheduler.handlers import execute_handler

        logger.info(
            "Executing event immediately: %s for player %s",
            event.event_id,
            player_id,
        )
        await execute_handler(event.handler, player_id, context)


class HueyExecutor:
    """Schedule events via Huey for delayed execution (immersive mode)."""

    def _calculate_delay(self, delay_range: DelayRange) -> int:
        """Calculate random delay within the range."""
        if delay_range.min_seconds == delay_range.max_seconds:
            return delay_range.min_seconds
        return random.randint(delay_range.min_seconds, delay_range.max_seconds)

    async def execute(
        self,
        event: StoryEvent,
        player_id: UUID,
        context: dict[str, Any],
    ) -> None:
        """Schedule event via Huey with appropriate delay."""
        from argent.scheduler.tasks import execute_story_event_task

        delay_seconds = self._calculate_delay(event.delay)

        if delay_seconds == 0:
            # No delay - execute immediately via Huey
            logger.info(
                "Scheduling event immediately via Huey: %s for player %s",
                event.event_id,
                player_id,
            )
            execute_story_event_task(
                event_id=event.event_id,
                player_id=str(player_id),
                context=context,
            )
        else:
            logger.info(
                "Scheduling event with %d second delay: %s for player %s",
                delay_seconds,
                event.event_id,
                player_id,
            )
            execute_story_event_task.schedule(
                args=(event.event_id, str(player_id), context),
                delay=delay_seconds,
            )


class StoryEventScheduler:
    """Main scheduler that routes events to appropriate executor."""

    def __init__(
        self,
        db: AsyncSession,
        force_immediate: bool = False,
    ) -> None:
        self._db = db
        self._force_immediate = force_immediate
        self._immediate_executor = ImmediateExecutor()
        self._huey_executor = HueyExecutor()

    async def _get_player_mode(self, player_id: UUID) -> str:
        """Get player's communication mode."""
        result = await self._db.execute(
            select(Player.communication_mode).where(Player.id == player_id)
        )
        mode = result.scalar_one_or_none()
        return mode or "web_only"

    def _get_executor(self, mode: str) -> EventExecutor:
        """Get executor based on mode."""
        if self._force_immediate or mode == "web_only":
            return self._immediate_executor
        return self._huey_executor

    async def schedule_event(
        self,
        event_id: str,
        player_id: UUID,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Schedule a single story event for execution."""
        event = get_event(event_id)
        mode = await self._get_player_mode(player_id)
        executor = self._get_executor(mode)

        await executor.execute(event, player_id, context or {})

        # Also schedule any follow-up events
        for follow_up in get_events_after(event_id):
            await executor.execute(follow_up, player_id, context or {})

    async def trigger_game_start(
        self,
        player_id: UUID,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Trigger all GAME_START events for a player."""
        mode = await self._get_player_mode(player_id)
        executor = self._get_executor(mode)
        ctx = context or {}

        for event in get_events_triggered_by(EventTrigger.GAME_START):
            await executor.execute(event, player_id, ctx)

            # Schedule follow-up events
            for follow_up in get_events_after(event.event_id):
                await executor.execute(follow_up, player_id, ctx)


def get_scheduler(
    db: AsyncSession,
    force_immediate: bool = False,
) -> StoryEventScheduler:
    """Get a scheduler instance."""
    return StoryEventScheduler(db, force_immediate)
