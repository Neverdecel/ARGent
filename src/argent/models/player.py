"""Player-related database models.

Schema based on DATA_ARCHITECTURE.md
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from argent.models.base import Base, TimestampMixin, UUIDMixin


class Player(Base, UUIDMixin, TimestampMixin):
    """Player identity and registration state."""

    __tablename__ = "players"

    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, unique=True)  # E.164 format: +1234567890
    timezone: Mapped[str] = mapped_column(Text, default="UTC")
    game_started_at: Mapped[datetime | None] = mapped_column()
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    keys: Mapped[list["PlayerKey"]] = relationship(back_populates="player")
    trust_scores: Mapped[list["PlayerTrust"]] = relationship(back_populates="player")
    milestones: Mapped[list["StoryMilestone"]] = relationship(back_populates="player")
    knowledge: Mapped[list["PlayerKnowledge"]] = relationship(back_populates="player")
    messages: Mapped[list["Message"]] = relationship(back_populates="player")


class PlayerKey(Base, UUIDMixin, TimestampMixin):
    """The cryptic key sent to players."""

    __tablename__ = "player_keys"

    player_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))
    key_value: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    access_limit: Mapped[int] = mapped_column(Integer, default=5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    first_accessed_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="keys")
    access_logs: Mapped[list["KeyAccessLog"]] = relationship(back_populates="key")


class KeyAccessLog(Base, UUIDMixin, TimestampMixin):
    """Log of every key access attempt."""

    __tablename__ = "key_access_log"

    player_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))
    key_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("player_keys.id"))
    accessed_at: Mapped[datetime] = mapped_column(default=datetime.now)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Relationships
    key: Mapped["PlayerKey"] = relationship(back_populates="access_logs")


class PlayerTrust(Base):
    """Current trust scores per agent (fast reads for triggers)."""

    __tablename__ = "player_trust"

    player_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), primary_key=True
    )
    agent_id: Mapped[str] = mapped_column(Text, primary_key=True)  # 'ember', 'miro'
    trust_score: Mapped[int] = mapped_column(Integer, default=0)  # -100 to 100
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_interaction_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="trust_scores")


class TrustEvent(Base, UUIDMixin, TimestampMixin):
    """Trust change log (audit trail + AI context)."""

    __tablename__ = "trust_events"

    player_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +10, -15, etc.
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # Natural language
    message_id: Mapped[Any | None] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"))

    __table_args__ = (
        Index(
            "idx_trust_events_player_recent", "player_id", "created_at", postgresql_using="btree"
        ),
    )


class PlayerKnowledge(Base, UUIDMixin, TimestampMixin):
    """What the player knows (as natural language sentences)."""

    __tablename__ = "player_knowledge"

    player_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)  # 'dashboard', 'key', 'ember', 'miro'
    source_agent: Mapped[str | None] = mapped_column(Text)
    learned_at: Mapped[datetime] = mapped_column(default=datetime.now)
    message_id: Mapped[Any | None] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"))

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="knowledge")

    __table_args__ = (
        Index("idx_knowledge_player_category", "player_id", "category", postgresql_using="btree"),
    )


class StoryMilestone(Base, TimestampMixin):
    """Milestones reached (for trigger evaluation)."""

    __tablename__ = "story_milestones"

    player_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), primary_key=True
    )
    milestone_id: Mapped[str] = mapped_column(Text, primary_key=True)
    reached_at: Mapped[datetime] = mapped_column(default=datetime.now)
    context: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="milestones")


class Message(Base, UUIDMixin, TimestampMixin):
    """Message metadata (NO content - content is in Memory Bank)."""

    __tablename__ = "messages"

    player_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"))
    agent_id: Mapped[str | None] = mapped_column(Text)  # NULL for system messages
    channel: Mapped[str] = mapped_column(Text, nullable=False)  # 'email', 'telegram', 'system'
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # 'inbound', 'outbound'

    # External provider message ID (Mailgun Message-Id or Telegram message_id)
    external_id: Mapped[str | None] = mapped_column(Text)

    # Reference to Memory Bank session
    session_id: Mapped[str | None] = mapped_column(Text)

    # Delivery tracking
    delivered_at: Mapped[datetime | None] = mapped_column()
    read_at: Mapped[datetime | None] = mapped_column()

    # Classification results (extracted insights)
    classified_at: Mapped[datetime | None] = mapped_column()
    classification: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_player_recent", "player_id", "created_at", postgresql_using="btree"),
    )
