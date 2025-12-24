"""Trust management service.

Handles trust score updates and event logging for player-agent relationships.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.models.player import PlayerTrust, TrustEvent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Trust score bounds
MIN_TRUST = -100
MAX_TRUST = 100


async def get_trust_score(
    db: AsyncSession,
    player_id: UUID,
    agent_id: str,
) -> int:
    """Get the current trust score for a player-agent pair.

    Args:
        db: Database session
        player_id: Player UUID
        agent_id: Agent identifier (ember, miro)

    Returns:
        Trust score (-100 to 100), or 0 if no record exists
    """
    result = await db.execute(
        select(PlayerTrust).where(
            PlayerTrust.player_id == player_id,
            PlayerTrust.agent_id == agent_id,
        )
    )
    trust = result.scalar_one_or_none()

    if trust is None:
        return 0

    return trust.trust_score


async def update_trust(
    db: AsyncSession,
    player_id: UUID,
    agent_id: str,
    delta: int,
    reason: str,
    message_id: UUID | None = None,
) -> int:
    """Update trust score and log the event.

    Args:
        db: Database session
        player_id: Player UUID
        agent_id: Agent identifier (ember, miro)
        delta: Trust change amount (-20 to +20 typically)
        reason: Natural language reason for the change
        message_id: Optional link to the triggering message

    Returns:
        The new trust score after update
    """
    if delta == 0:
        # No change needed, just return current score
        return await get_trust_score(db, player_id, agent_id)

    # Get or create trust record
    result = await db.execute(
        select(PlayerTrust).where(
            PlayerTrust.player_id == player_id,
            PlayerTrust.agent_id == agent_id,
        )
    )
    trust = result.scalar_one_or_none()

    if trust is None:
        # Create new trust record
        trust = PlayerTrust(
            player_id=player_id,
            agent_id=agent_id,
            trust_score=0,
            interaction_count=0,
        )
        db.add(trust)

    # Calculate new score with bounds
    old_score = trust.trust_score
    new_score = max(MIN_TRUST, min(MAX_TRUST, old_score + delta))

    # Update trust record
    trust.trust_score = new_score
    trust.interaction_count += 1
    trust.last_interaction_at = datetime.now(UTC)

    # Log the trust event
    event = TrustEvent(
        player_id=player_id,
        agent_id=agent_id,
        delta=delta,
        reason=reason,
        message_id=message_id,
    )
    db.add(event)

    logger.info(
        "Trust updated: player=%s agent=%s delta=%+d (%d -> %d) reason=%s",
        player_id,
        agent_id,
        delta,
        old_score,
        new_score,
        reason[:50],
    )

    return new_score


async def get_trust_history(
    db: AsyncSession,
    player_id: UUID,
    agent_id: str | None = None,
    limit: int = 20,
) -> list[TrustEvent]:
    """Get recent trust events for a player.

    Args:
        db: Database session
        player_id: Player UUID
        agent_id: Optional filter by agent
        limit: Maximum events to return

    Returns:
        List of TrustEvent records, most recent first
    """
    query = select(TrustEvent).where(TrustEvent.player_id == player_id)

    if agent_id is not None:
        query = query.where(TrustEvent.agent_id == agent_id)

    query = query.order_by(TrustEvent.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())
