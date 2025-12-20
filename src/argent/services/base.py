"""Base abstractions for communication channel services."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID


class Channel(str, Enum):
    """Communication channels matching the messages.channel column."""

    EMAIL = "email"
    SMS = "sms"
    SYSTEM = "system"


class Direction(str, Enum):
    """Message direction matching the messages.direction column."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class Attachment:
    """File attachment for messages."""

    filename: str
    content_type: str
    url: str | None = None  # For download
    data: bytes | None = None  # Inline data
    size: int | None = None


@dataclass
class OutboundMessage:
    """Data for sending a message."""

    player_id: UUID
    recipient: str  # Email address or Telegram chat_id
    content: str
    agent_id: str | None = None  # 'ember' or 'miro'
    subject: str | None = None  # For email
    html_content: str | None = None  # HTML version for email
    attachments: list[Attachment] = field(default_factory=list)
    reply_to_external_id: str | None = None  # Thread reference


@dataclass
class InboundMessage:
    """Parsed incoming message from webhook."""

    external_id: str  # Mailgun message-id or Twilio MessageSid
    channel: Channel
    sender_identifier: str  # email address or phone number
    content: str
    subject: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    """Result of sending a message."""

    success: bool
    external_id: str | None = None  # Provider message ID
    error: str | None = None
    retryable: bool = False


class CommunicationError(Exception):
    """Base exception for communication services."""

    pass


class SendError(CommunicationError):
    """Failed to send message."""

    def __init__(self, message: str, retryable: bool = True) -> None:
        self.retryable = retryable
        super().__init__(message)


class WebhookError(CommunicationError):
    """Failed to process webhook."""

    pass


class SignatureVerificationError(WebhookError):
    """Invalid webhook signature."""

    pass


class BaseChannelService(ABC):
    """Abstract base class for communication channel services."""

    @property
    @abstractmethod
    def channel(self) -> Channel:
        """Return the channel type."""
        ...

    @abstractmethod
    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a message through this channel."""
        ...

    @abstractmethod
    async def parse_webhook(self, payload: dict[str, Any]) -> InboundMessage:
        """Parse incoming webhook payload into InboundMessage."""
        ...

    @abstractmethod
    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str | None = None,
    ) -> bool:
        """Verify webhook signature for security."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (close HTTP clients, etc.)."""
        ...
