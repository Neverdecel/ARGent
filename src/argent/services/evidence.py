"""Evidence dashboard service.

Handles key validation, access logging, and limit enforcement for the
evidence dashboard (the in-fiction corporate portal).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.models.player import KeyAccessLog, PlayerKey, PlayerKnowledge

logger = logging.getLogger(__name__)


async def validate_key(db: AsyncSession, key_value: str) -> PlayerKey | None:
    """Validate a key exists in the database.

    Args:
        db: Database session
        key_value: The key string (format: XXXX-XXXX-XXXX-XXXX)

    Returns:
        PlayerKey if found, None otherwise
    """
    # Normalize key format (uppercase, with dashes)
    normalized = key_value.strip().upper()

    result = await db.execute(select(PlayerKey).where(PlayerKey.key_value == normalized))
    return result.scalar_one_or_none()


async def check_access_limit(key: PlayerKey) -> bool:
    """Check if key still has remaining accesses.

    Args:
        key: The PlayerKey to check

    Returns:
        True if access is allowed, False if limit exhausted
    """
    return key.access_count < key.access_limit


async def log_access(
    db: AsyncSession,
    key: PlayerKey,
    success: bool,
    request: Request,
) -> KeyAccessLog:
    """Log an access attempt to the evidence dashboard.

    Args:
        db: Database session
        key: The PlayerKey being accessed
        success: Whether access was granted
        request: FastAPI request for IP/user-agent

    Returns:
        The created KeyAccessLog entry
    """
    # Get IP address (handle proxies)
    ip_address = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()

    user_agent = request.headers.get("user-agent", "")[:500]  # Truncate long UAs

    log_entry = KeyAccessLog(
        player_id=key.player_id,
        key_id=key.id,
        accessed_at=datetime.now(UTC),
        success=success,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log_entry)

    logger.info(
        "Dashboard access %s: key=%s player=%s ip=%s",
        "granted" if success else "denied",
        key.key_value[:9] + "...",
        key.player_id,
        ip_address,
    )

    return log_entry


async def increment_access(db: AsyncSession, key: PlayerKey) -> None:
    """Increment access count and set first access timestamp.

    Args:
        db: Database session
        key: The PlayerKey to update
    """
    key.access_count += 1

    if key.first_accessed_at is None:
        key.first_accessed_at = datetime.now(UTC)

    logger.info(
        "Key access count: %d/%d for key=%s",
        key.access_count,
        key.access_limit,
        key.key_value[:9] + "...",
    )


async def record_dashboard_knowledge(
    db: AsyncSession,
    player_id: UUID,
) -> PlayerKnowledge | None:
    """Record that player accessed the evidence dashboard.

    This fact will appear in agent prompts, allowing Ember to know
    when the player has betrayed their trust.

    Args:
        db: Database session
        player_id: The player's UUID

    Returns:
        The created knowledge record, or None if already exists
    """
    # Check if already recorded
    fact_text = "Player accessed the evidence dashboard"
    result = await db.execute(
        select(PlayerKnowledge).where(
            PlayerKnowledge.player_id == player_id,
            PlayerKnowledge.fact == fact_text,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.debug("Dashboard access already recorded for player=%s", player_id)
        return None

    knowledge = PlayerKnowledge(
        player_id=player_id,
        fact=fact_text,
        category="dashboard",
        source_agent=None,  # System-generated
        learned_at=datetime.now(UTC),
    )
    db.add(knowledge)

    logger.info("Recorded dashboard access for player=%s", player_id)
    return knowledge


async def get_remaining_accesses(key: PlayerKey) -> int:
    """Get number of remaining accesses for a key.

    Args:
        key: The PlayerKey to check

    Returns:
        Number of remaining accesses (0 if exhausted)
    """
    return max(0, key.access_limit - key.access_count)
