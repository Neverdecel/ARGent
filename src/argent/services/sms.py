"""SMS service using Twilio API."""

import base64
import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from argent.config import get_settings
from argent.services.base import (
    Attachment,
    BaseChannelService,
    Channel,
    InboundMessage,
    OutboundMessage,
    SendError,
    SendResult,
)

logger = logging.getLogger(__name__)


class SMSService(BaseChannelService):
    """Twilio-based SMS service for Miro agent."""

    TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def channel(self) -> Channel:
        return Channel.SMS

    @property
    def _api_url(self) -> str:
        return f"{self.TWILIO_API_BASE}/Accounts/{self._settings.twilio_account_sid}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=(
                    self._settings.twilio_account_sid,
                    self._settings.twilio_auth_token,
                ),
                timeout=30.0,
            )
        return self._client

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send SMS via Twilio API."""
        if not self._settings.sms_enabled:
            logger.info("SMS disabled, skipping send to %s", message.recipient)
            return SendResult(success=True, external_id="disabled")

        return await self.send_sms(
            to_number=message.recipient,
            body=message.content,
        )

    async def send_sms(
        self,
        to_number: str,
        body: str,
        from_number: str | None = None,
        media_url: str | None = None,
    ) -> SendResult:
        """
        Send SMS via Twilio API.

        Args:
            to_number: Recipient phone number (E.164 format: +1234567890)
            body: Message text (max 1600 chars, will be split if longer)
            from_number: Sender number (defaults to config)
            media_url: Optional URL for MMS media
        """
        if not self._settings.sms_enabled:
            logger.info("SMS disabled, skipping send to %s", to_number)
            return SendResult(success=True, external_id="disabled")

        client = await self._get_client()

        data: dict[str, str] = {
            "To": to_number,
            "From": from_number or self._settings.twilio_phone_number,
            "Body": body,
        }

        if media_url:
            data["MediaUrl"] = media_url

        try:
            response = await client.post(
                f"{self._api_url}/Messages.json",
                data=data,
            )
            response.raise_for_status()
            result = response.json()

            return SendResult(
                success=True,
                external_id=result.get("sid"),
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Twilio API error: {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_msg = error_body.get("message", error_msg)
            except Exception:
                pass

            logger.error("Failed to send SMS: %s", error_msg)

            # Rate limit (429) is retryable
            retryable = e.response.status_code == 429
            return SendResult(success=False, error=error_msg, retryable=retryable)

        except httpx.TimeoutException:
            logger.error("Twilio API timeout")
            return SendResult(success=False, error="Timeout", retryable=True)

        except Exception as e:
            logger.exception("Unexpected error sending SMS")
            raise SendError(str(e), retryable=False) from e

    async def parse_webhook(self, payload: dict[str, Any]) -> InboundMessage:
        """
        Parse Twilio inbound SMS webhook payload.

        Twilio sends form-encoded data with:
        - MessageSid: Unique message ID
        - From: Sender's phone number
        - To: Your Twilio number
        - Body: Message text
        - NumMedia: Number of media attachments
        - MediaUrl0, MediaUrl1, etc.: Media URLs
        """
        # Parse attachments if present
        attachments: list[Attachment] = []
        num_media = int(payload.get("NumMedia", 0))
        for i in range(num_media):
            media_url = payload.get(f"MediaUrl{i}")
            content_type = payload.get(f"MediaContentType{i}", "application/octet-stream")
            if media_url:
                attachments.append(
                    Attachment(
                        filename=f"media_{i}",
                        content_type=content_type,
                        url=media_url,
                    )
                )

        return InboundMessage(
            external_id=payload.get("MessageSid", ""),
            channel=Channel.SMS,
            sender_identifier=payload.get("From", ""),
            content=payload.get("Body", ""),
            attachments=attachments,
            timestamp=datetime.now(UTC),
            raw_payload=payload,
        )

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str | None = None,
        url: str | None = None,
    ) -> bool:
        """
        Verify Twilio webhook signature.

        Twilio uses X-Twilio-Signature header with HMAC-SHA1.
        The signature is computed over the full URL + sorted POST params.

        Args:
            payload: Not used directly (Twilio uses URL + form params)
            signature: Value from X-Twilio-Signature header
            url: Full webhook URL (required for verification)
        """
        if not url:
            logger.warning("URL required for Twilio signature verification")
            return False

        if not self._settings.twilio_auth_token:
            logger.warning("Twilio auth token not configured")
            return True  # Skip verification if not configured

        return signature == self._compute_signature(url, {})

    def verify_webhook_request(
        self,
        url: str,
        params: dict[str, str],
        signature: str,
    ) -> bool:
        """
        Verify Twilio webhook signature from request.

        Args:
            url: Full webhook URL (including https://)
            params: Form parameters from request
            signature: Value from X-Twilio-Signature header
        """
        if not self._settings.twilio_auth_token:
            logger.warning("Twilio auth token not configured, skipping verification")
            return True

        expected = self._compute_signature(url, params)
        return hmac.compare_digest(expected, signature)

    def _compute_signature(self, url: str, params: dict[str, str]) -> str:
        """
        Compute Twilio signature.

        Algorithm:
        1. Take full URL
        2. Sort POST params alphabetically
        3. Append each key-value pair to URL
        4. HMAC-SHA1 with auth token
        5. Base64 encode
        """
        # Build the data string: URL + sorted params
        data = url
        for key in sorted(params.keys()):
            data += key + params[key]

        # Compute HMAC-SHA1
        signature = hmac.new(
            self._settings.twilio_auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        return base64.b64encode(signature).decode("utf-8")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
