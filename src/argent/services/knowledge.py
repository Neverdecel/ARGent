"""Knowledge management service.

Handles storage and retrieval of facts the player has learned from agents.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.models.player import PlayerKnowledge

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def get_player_knowledge(
    db: AsyncSession,
    player_id: UUID,
    category: str | None = None,
    source_agent: str | None = None,
) -> list[str]:
    """Get knowledge facts for a player.

    Args:
        db: Database session
        player_id: Player UUID
        category: Optional filter by category
        source_agent: Optional filter by source agent

    Returns:
        List of fact strings
    """
    query = select(PlayerKnowledge.fact).where(PlayerKnowledge.player_id == player_id)

    if category is not None:
        query = query.where(PlayerKnowledge.category == category)

    if source_agent is not None:
        query = query.where(PlayerKnowledge.source_agent == source_agent)

    query = query.order_by(PlayerKnowledge.learned_at.desc())

    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def add_knowledge(
    db: AsyncSession,
    player_id: UUID,
    facts: list[str],
    source_agent: str,
    message_id: UUID | None = None,
    category: str | None = None,
) -> list[PlayerKnowledge]:
    """Store new knowledge facts for a player.

    Args:
        db: Database session
        player_id: Player UUID
        facts: List of fact strings to store
        source_agent: Which agent revealed this (ember, miro)
        message_id: Optional link to the source message
        category: Optional category (key, dashboard, ember, miro)

    Returns:
        List of created PlayerKnowledge records
    """
    if not facts:
        return []

    # Get existing facts to avoid exact duplicates
    existing = await get_player_knowledge(db, player_id)
    existing_set = {f.lower().strip() for f in existing}

    created = []
    for fact in facts:
        fact = fact.strip()
        if not fact:
            continue

        # Skip exact duplicates (case-insensitive)
        if fact.lower() in existing_set:
            logger.debug("Skipping duplicate fact: %s", fact[:50])
            continue

        knowledge = PlayerKnowledge(
            player_id=player_id,
            fact=fact,
            category=category or _infer_category(fact, source_agent),
            source_agent=source_agent,
            learned_at=datetime.now(UTC),
            message_id=message_id,
        )
        db.add(knowledge)
        created.append(knowledge)
        existing_set.add(fact.lower())

    if created:
        logger.info(
            "Added %d knowledge facts for player=%s from agent=%s",
            len(created),
            player_id,
            source_agent,
        )

    return created


def _infer_category(fact: str, source_agent: str) -> str:
    """Infer category from fact content.

    Args:
        fact: The fact text
        source_agent: Which agent revealed it

    Returns:
        Category string
    """
    fact_lower = fact.lower()

    if any(word in fact_lower for word in ["key", "code", "access", "xxxx"]):
        return "key"
    if any(word in fact_lower for word in ["dashboard", "portal", "site", "page"]):
        return "dashboard"
    if "ember" in fact_lower:
        return "ember"
    if "miro" in fact_lower:
        return "miro"

    # Default to source agent
    return source_agent


async def get_knowledge_by_message(
    db: AsyncSession,
    message_id: UUID,
) -> list[PlayerKnowledge]:
    """Get all knowledge facts associated with a message.

    Args:
        db: Database session
        message_id: Message UUID

    Returns:
        List of PlayerKnowledge records linked to this message
    """
    result = await db.execute(
        select(PlayerKnowledge).where(PlayerKnowledge.message_id == message_id)
    )
    return list(result.scalars().all())
