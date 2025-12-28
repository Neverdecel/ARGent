"""Dashboard statistics service.

Aggregates player statistics for the hub dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.models.player import (
    Message,
    Player,
    PlayerKnowledge,
    PlayerTrust,
    StoryMilestone,
)


@dataclass
class AgentTrustStats:
    """Trust statistics for a single agent."""

    agent_id: str
    display_name: str
    trust_score: int  # -100 to +100
    interaction_count: int


@dataclass
class GameProgress:
    """Player's game progress statistics."""

    time_played_display: str  # "2d 5h" format
    game_started_at: datetime | None
    milestone_count: int
    knowledge_count: int
    knowledge_by_category: dict[str, int]


@dataclass
class ActivitySummary:
    """Player's communication activity statistics."""

    total_messages_sent: int
    total_messages_received: int
    conversation_count: int


@dataclass
class DashboardStats:
    """Complete dashboard statistics."""

    trust_stats: list[AgentTrustStats]
    game_progress: GameProgress
    activity: ActivitySummary


# Agent display names
AGENT_NAMES = {
    "ember": "Ember",
    "miro": "Miro",
}


def _format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return "Just started"

    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if days > 0:
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}d {remaining_hours}h"
        return f"{days}d"
    elif hours > 0:
        remaining_minutes = minutes % 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"
    else:
        return f"{minutes}m"


async def _get_trust_stats(db: AsyncSession, player_id: UUID) -> list[AgentTrustStats]:
    """Get trust statistics for all agents."""
    result = await db.execute(select(PlayerTrust).where(PlayerTrust.player_id == player_id))
    trust_records = {t.agent_id: t for t in result.scalars().all()}

    stats = []
    for agent_id, display_name in AGENT_NAMES.items():
        trust = trust_records.get(agent_id)
        stats.append(
            AgentTrustStats(
                agent_id=agent_id,
                display_name=display_name,
                trust_score=trust.trust_score if trust else 0,
                interaction_count=trust.interaction_count if trust else 0,
            )
        )

    return stats


async def _get_game_progress(db: AsyncSession, player_id: UUID) -> GameProgress:
    """Get game progress statistics."""
    # Get player for game_started_at
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()

    # Calculate time played
    game_started_at = player.game_started_at if player else None
    if game_started_at:
        duration = datetime.now(UTC) - game_started_at.replace(tzinfo=UTC)
        time_played_display = _format_duration(int(duration.total_seconds()))
    else:
        time_played_display = "Not started"

    # Count milestones
    milestone_result = await db.execute(
        select(func.count()).where(StoryMilestone.player_id == player_id)
    )
    milestone_count = milestone_result.scalar() or 0

    # Count knowledge by category
    knowledge_result = await db.execute(
        select(PlayerKnowledge.category, func.count())
        .where(PlayerKnowledge.player_id == player_id)
        .group_by(PlayerKnowledge.category)
    )
    knowledge_by_category: dict[str, int] = {}
    total_knowledge = 0
    for category, count in knowledge_result.all():
        cat_name = category or "general"
        knowledge_by_category[cat_name] = count
        total_knowledge += count

    return GameProgress(
        time_played_display=time_played_display,
        game_started_at=game_started_at,
        milestone_count=milestone_count,
        knowledge_count=total_knowledge,
        knowledge_by_category=knowledge_by_category,
    )


async def _get_activity_summary(db: AsyncSession, player_id: UUID) -> ActivitySummary:
    """Get communication activity statistics."""
    # Count messages sent (inbound = from player)
    result = await db.execute(
        select(func.count()).where(
            Message.player_id == player_id,
            Message.direction == "inbound",
        )
    )
    messages_sent = result.scalar() or 0

    # Count messages received (outbound = from agents)
    result = await db.execute(
        select(func.count()).where(
            Message.player_id == player_id,
            Message.direction == "outbound",
        )
    )
    messages_received = result.scalar() or 0

    # Count distinct conversations (session_id)
    result = await db.execute(
        select(func.count(distinct(Message.session_id))).where(
            Message.player_id == player_id,
            Message.session_id.isnot(None),
        )
    )
    conversation_count = result.scalar() or 0

    return ActivitySummary(
        total_messages_sent=messages_sent,
        total_messages_received=messages_received,
        conversation_count=conversation_count,
    )


async def get_dashboard_stats(db: AsyncSession, player_id: UUID) -> DashboardStats:
    """Get all dashboard statistics for a player.

    Args:
        db: Database session
        player_id: Player UUID

    Returns:
        DashboardStats with trust, progress, and activity data
    """
    trust_stats = await _get_trust_stats(db, player_id)
    game_progress = await _get_game_progress(db, player_id)
    activity = await _get_activity_summary(db, player_id)

    return DashboardStats(
        trust_stats=trust_stats,
        game_progress=game_progress,
        activity=activity,
    )
