"""Message dispatcher for routing to appropriate channel service.

Routes messages based on player communication_mode preference:
- immersive: Real email/SMS via Mailgun/Twilio
- web_only: Store in database for web inbox
"""

import logging
from typing import TYPE_CHECKING

from argent.models.player import Player
from argent.services.base import Channel, OutboundMessage, SendResult

if TYPE_CHECKING:
    from argent.services.email import EmailService
    from argent.services.sms import SMSService
    from argent.services.web_inbox import WebInboxService

logger = logging.getLogger(__name__)


class MessageDispatcher:
    """Routes outbound messages to the appropriate service based on player preference."""

    def __init__(
        self,
        email_service: "EmailService",
        sms_service: "SMSService",
        web_inbox_service: "WebInboxService",
    ) -> None:
        self._email = email_service
        self._sms = sms_service
        self._web_inbox = web_inbox_service

    async def send(
        self,
        player: Player,
        message: OutboundMessage,
        channel: Channel,
    ) -> SendResult:
        """Route message based on player communication mode.

        Args:
            player: The player to send to
            message: The message to send
            channel: The intended channel (EMAIL or SMS)

        Returns:
            SendResult indicating success/failure
        """
        # Web-only players get all messages in web inbox
        if player.communication_mode == "web_only":
            logger.info(
                "Routing %s message to web inbox for player %s",
                channel.value,
                player.id,
            )
            return await self._web_inbox.send_message(message)

        # Immersive mode: route to actual service
        if channel == Channel.EMAIL:
            return await self._email.send_message(message)
        elif channel == Channel.SMS:
            return await self._sms.send_message(message)
        elif channel == Channel.WEB:
            # Explicit web channel request
            return await self._web_inbox.send_message(message)
        else:
            logger.warning("Unknown channel %s, falling back to web inbox", channel)
            return await self._web_inbox.send_message(message)

    async def send_email(
        self,
        player: Player,
        message: OutboundMessage,
    ) -> SendResult:
        """Convenience method to send an email-style message."""
        return await self.send(player, message, Channel.EMAIL)

    async def send_sms(
        self,
        player: Player,
        message: OutboundMessage,
    ) -> SendResult:
        """Convenience method to send an SMS-style message."""
        return await self.send(player, message, Channel.SMS)

    async def close(self) -> None:
        """Clean up all services."""
        await self._email.close()
        await self._sms.close()
        await self._web_inbox.close()
