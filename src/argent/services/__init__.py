"""External services for ARGent.

This module contains:
- Email service (Mailgun)
- SMS service (Twilio)
- Verification service (token generation and validation)
- Memory Bank service (TODO)
"""

from argent.services.base import (
    Attachment,
    BaseChannelService,
    Channel,
    CommunicationError,
    Direction,
    InboundMessage,
    OutboundMessage,
    SendError,
    SendResult,
    SignatureVerificationError,
    WebhookError,
)
from argent.services.email import EmailService, extract_reply_content, format_ember_email
from argent.services.sms import SMSService
from argent.services.verification import VerificationService, get_verification_service

__all__ = [
    # Base types
    "Attachment",
    "BaseChannelService",
    "Channel",
    "CommunicationError",
    "Direction",
    "InboundMessage",
    "OutboundMessage",
    "SendError",
    "SendResult",
    "SignatureVerificationError",
    "WebhookError",
    # Email
    "EmailService",
    "extract_reply_content",
    "format_ember_email",
    # SMS
    "SMSService",
    # Verification
    "VerificationService",
    "get_verification_service",
]
