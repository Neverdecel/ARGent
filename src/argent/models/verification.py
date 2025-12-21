"""Verification token model for email and phone verification."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from argent.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from argent.models.player import Player


class TokenType(str, Enum):
    """Types of verification tokens."""

    EMAIL = "email"
    PHONE = "phone"


class VerificationToken(Base, UUIDMixin, TimestampMixin):
    """Verification tokens for email and phone verification.

    Email tokens: 32-byte random, URL-safe base64, stored as SHA256 hash
    Phone tokens: 6-digit numeric codes, stored plain (short expiry)
    """

    __tablename__ = "verification_tokens"

    player_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'email' or 'phone'
    token_value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column()  # NULL until verified

    # Relationships
    player: Mapped["Player"] = relationship()

    __table_args__ = (
        # Efficient lookup for active tokens by type and value
        Index(
            "idx_verification_tokens_lookup",
            "token_type",
            "token_value",
            postgresql_where=text("used_at IS NULL"),
        ),
        # Efficient cleanup of expired tokens
        Index(
            "idx_verification_tokens_expiry",
            "expires_at",
            postgresql_where=text("used_at IS NULL"),
        ),
        # Find active tokens for a player (for rate limiting, invalidation)
        Index(
            "idx_verification_tokens_player",
            "player_id",
            "token_type",
            postgresql_where=text("used_at IS NULL"),
        ),
    )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not used and not expired)."""
        return not self.is_used and not self.is_expired
