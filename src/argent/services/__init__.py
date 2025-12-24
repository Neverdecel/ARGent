"""External services for ARGent.

This module contains:
- Email service (Mailgun)
- SMS service (Twilio)
- Web inbox service (non-immersive mode)
- Message dispatcher (routes based on player preference)
- Verification service (token generation and validation)
- Classification service (trust/knowledge extraction)
- Trust service (trust score management)
- Knowledge service (player knowledge management)
"""

from argent.services import classification, knowledge, trust
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
from argent.services.dispatcher import MessageDispatcher
from argent.services.email import EmailService, extract_reply_content, format_ember_email
from argent.services.sms import SMSService
from argent.services.verification import VerificationService, get_verification_service
from argent.services.web_inbox import WebInboxService

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
    # Web Inbox
    "WebInboxService",
    # Dispatcher
    "MessageDispatcher",
    # Verification
    "VerificationService",
    "get_verification_service",
    # Classification/Extraction
    "classification",
    "trust",
    "knowledge",
]
