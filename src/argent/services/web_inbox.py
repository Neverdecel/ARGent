"""Web inbox service for non-immersive mode.

Instead of sending via external providers (Mailgun/Twilio), this service
stores messages directly in the database for viewing in the web UI.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.models.player import Message
from argent.services.base import (
    BaseChannelService,
    Channel,
    Direction,
    InboundMessage,
    OutboundMessage,
    SendResult,
)

logger = logging.getLogger(__name__)


class WebInboxService(BaseChannelService):
    """Database-backed inbox for non-immersive mode.

    Messages are stored directly in the database instead of being sent
    via external email/SMS providers. The web UI reads from this store.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def channel(self) -> Channel:
        return Channel.WEB

    async def send_message(
        self, message: OutboundMessage, display_channel: str = "email"
    ) -> SendResult:
        """Store message in database for web inbox display.

        Args:
            message: The message to store
            display_channel: How to display this message - 'email' or 'sms'
        """
        # Generate a unique ID for this message
        message_id = uuid4()

        # Determine sender name from agent_id
        sender_name = self._get_sender_name(message.agent_id)

        # Create the message record
        # Use display_channel for the channel field so filtering works
        db_message = Message(
            id=message_id,
            player_id=message.player_id,
            agent_id=message.agent_id,
            channel=display_channel,  # 'email' or 'sms' for display/filtering
            direction=Direction.OUTBOUND.value,
            external_id=f"web-{message_id}",
            session_id=message.session_id,  # For conversation threading
            subject=message.subject,
            content=message.content,
            html_content=message.html_content,
            sender_name=sender_name,
            delivered_at=datetime.now(UTC),
        )

        self._db.add(db_message)
        await self._db.flush()

        logger.info(
            "Stored web inbox message %s from %s to player %s",
            message_id,
            sender_name,
            message.player_id,
        )

        return SendResult(
            success=True,
            external_id=f"web-{message_id}",
        )

    async def store_player_message(
        self,
        player_id: UUID,
        content: str,
        channel_type: str = "email",
        subject: str | None = None,
        session_id: str | None = None,
    ) -> Message:
        """Store a message sent by the player via web UI.

        Args:
            player_id: The player's ID
            content: Message content
            channel_type: 'email' or 'sms' for UI context
            subject: Email subject (optional)
            session_id: Session ID for conversation threading

        Returns:
            The created Message object
        """
        message_id = uuid4()

        db_message = Message(
            id=message_id,
            player_id=player_id,
            agent_id=None,  # Player message, no agent
            channel=Channel.WEB.value,
            direction=Direction.INBOUND.value,
            external_id=f"web-player-{message_id}",
            session_id=session_id,
            subject=subject,
            content=content,
            html_content=None,
            sender_name="You",  # Player's perspective
            delivered_at=datetime.now(UTC),
            read_at=datetime.now(UTC),  # Player's own message is "read"
        )

        self._db.add(db_message)
        await self._db.flush()

        logger.info(
            "Stored player message %s from player %s",
            message_id,
            player_id,
        )

        return db_message

    async def get_messages(
        self,
        player_id: UUID,
        channel_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a player's inbox.

        Args:
            player_id: The player's ID
            channel_filter: Optional filter by channel ('email' or 'sms')
            limit: Max messages to return
            offset: Pagination offset

        Returns:
            List of messages ordered by creation time (newest first)
        """
        query = select(Message).where(Message.player_id == player_id)

        if channel_filter:
            query = query.where(Message.channel == channel_filter)

        query = query.order_by(Message.created_at.desc()).limit(limit).offset(offset)

        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_conversations(
        self,
        player_id: UUID,
        limit: int = 20,
        channel_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get conversation summaries for inbox view.

        Groups messages by session_id and returns the latest message
        from each conversation.

        Args:
            player_id: The player's ID
            limit: Max conversations to return
            channel_filter: Optional 'email' or 'sms' to filter by channel

        Returns:
            List of conversation summaries with latest message preview
        """
        # Get all messages for player, grouped by session
        query = (
            select(Message)
            .where(Message.player_id == player_id)
            .order_by(Message.created_at.desc())
        )

        result = await self._db.execute(query)
        messages = list(result.scalars().all())

        # Group by session_id
        conversations: dict[str | None, list[Message]] = {}
        for msg in messages:
            session_key = msg.session_id or f"single-{msg.id}"
            if session_key not in conversations:
                conversations[session_key] = []
            conversations[session_key].append(msg)

        # Build summaries
        summaries = []
        for session_id, session_messages in conversations.items():
            latest = session_messages[0]  # Already sorted by created_at desc
            unread_count = sum(1 for m in session_messages if m.read_at is None)

            # Determine conversation channel from first message
            # Default to 'email' for legacy messages stored as 'web'
            conv_channel = latest.channel
            if conv_channel == "web":
                conv_channel = "email"

            # Apply channel filter
            if channel_filter and conv_channel != channel_filter:
                continue

            # Determine conversation title from participants
            participants = {m.sender_name for m in session_messages if m.sender_name}
            participants.discard("You")
            title = ", ".join(sorted(participants)) if participants else "Unknown"

            summaries.append(
                {
                    "session_id": session_id,
                    "title": title,
                    "channel": conv_channel,
                    "latest_message": latest,
                    "message_count": len(session_messages),
                    "unread_count": unread_count,
                    "updated_at": latest.created_at,
                }
            )

        # Sort by latest message time and limit
        summaries.sort(key=lambda x: x["updated_at"], reverse=True)  # type: ignore[arg-type, return-value]
        return summaries[:limit]

    async def get_conversation_messages(
        self,
        player_id: UUID,
        session_id: str,
    ) -> list[Message]:
        """Get all messages in a conversation thread.

        Args:
            player_id: The player's ID (for security check)
            session_id: The session/conversation ID

        Returns:
            List of messages in chronological order
        """
        query = (
            select(Message)
            .where(Message.player_id == player_id)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )

        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_message(
        self,
        player_id: UUID,
        message_id: UUID,
    ) -> Message | None:
        """Get a single message by ID.

        Args:
            player_id: The player's ID (for security check)
            message_id: The message ID

        Returns:
            The message if found and owned by player, else None
        """
        query = (
            select(Message).where(Message.id == message_id).where(Message.player_id == player_id)
        )

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def mark_read(
        self,
        player_id: UUID,
        message_id: UUID,
    ) -> bool:
        """Mark a message as read.

        Returns:
            True if message was updated, False if not found
        """
        message = await self.get_message(player_id, message_id)
        if not message:
            return False

        if message.read_at is None:
            message.read_at = datetime.now(UTC)
            await self._db.flush()

        return True

    async def mark_conversation_read(
        self,
        player_id: UUID,
        session_id: str,
    ) -> int:
        """Mark all messages in a conversation as read.

        Returns:
            Number of messages marked as read
        """
        messages = await self.get_conversation_messages(player_id, session_id)
        count = 0

        now = datetime.now(UTC)
        for msg in messages:
            if msg.read_at is None:
                msg.read_at = now
                count += 1

        if count > 0:
            await self._db.flush()

        return count

    async def get_unread_count(
        self, player_id: UUID, channel_filter: str | None = None
    ) -> int:
        """Get count of unread messages for a player.

        Args:
            player_id: The player's ID
            channel_filter: Optional filter by channel ('email' or 'sms')
        """
        query = (
            select(Message)
            .where(Message.player_id == player_id)
            .where(Message.read_at.is_(None))
            .where(Message.direction == Direction.OUTBOUND.value)  # Only agent messages
        )

        if channel_filter:
            query = query.where(Message.channel == channel_filter)

        result = await self._db.execute(query)
        return len(list(result.scalars().all()))

    async def parse_webhook(self, payload: dict[str, Any]) -> InboundMessage:
        """Parse webhook - not used for web inbox, messages come via API."""
        raise NotImplementedError("WebInboxService doesn't use webhooks")

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str | None = None,
    ) -> bool:
        """Verify signature - not used for web inbox."""
        raise NotImplementedError("WebInboxService doesn't use webhooks")

    async def close(self) -> None:
        """Clean up resources - nothing to close for web inbox."""
        pass

    def _get_sender_name(self, agent_id: str | None) -> str:
        """Get display name for an agent."""
        if agent_id == "ember":
            return "Ember"
        elif agent_id == "miro":
            return "Miro"
        elif agent_id == "system":
            return "System"
        elif agent_id:
            return agent_id.title()
        else:
            return "Unknown"
