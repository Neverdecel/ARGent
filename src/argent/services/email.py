"""Email service using Mailgun API."""

import hashlib
import hmac
import logging
import re
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
    SignatureVerificationError,
)

logger = logging.getLogger(__name__)


class EmailService(BaseChannelService):
    """Mailgun-based email service for Ember agent."""

    MAILGUN_API_BASE = "https://api.mailgun.net/v3"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def channel(self) -> Channel:
        return Channel.EMAIL

    @property
    def _api_url(self) -> str:
        return f"{self.MAILGUN_API_BASE}/{self._settings.mailgun_domain}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=("api", self._settings.mailgun_api_key),
                timeout=30.0,
            )
        return self._client

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send email via Mailgun API."""
        if not self._settings.email_enabled:
            logger.info("Email disabled, skipping send to %s", message.recipient)
            return SendResult(success=True, external_id="disabled")

        # Build email data
        data: dict[str, Any] = {
            "from": self._settings.email_from,
            "to": message.recipient,
            "text": message.content,
        }

        if message.subject:
            data["subject"] = message.subject

        if message.html_content:
            data["html"] = message.html_content

        # Add threading headers if replying
        if message.reply_to_external_id:
            data["h:In-Reply-To"] = message.reply_to_external_id
            data["h:References"] = message.reply_to_external_id

        return await self._send_email(data, message.attachments)

    async def send_raw(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: str | None = None,
        from_email: str | None = None,
        attachments: list[Attachment] | None = None,
        reply_to_message_id: str | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> SendResult:
        """
        Low-level send method with full control.

        Args:
            to_email: Recipient email
            subject: Email subject
            text_content: Plain text body
            html_content: HTML body (optional)
            from_email: Sender email (defaults to config)
            attachments: List of file attachments
            reply_to_message_id: Message-ID for threading
            custom_headers: Additional headers
        """
        if not self._settings.email_enabled:
            logger.info("Email disabled, skipping send to %s", to_email)
            return SendResult(success=True, external_id="disabled")

        data: dict[str, Any] = {
            "from": from_email or self._settings.email_from,
            "to": to_email,
            "subject": subject,
            "text": text_content,
        }

        if html_content:
            data["html"] = html_content

        if reply_to_message_id:
            data["h:In-Reply-To"] = reply_to_message_id
            data["h:References"] = reply_to_message_id

        if custom_headers:
            for key, value in custom_headers.items():
                data[f"h:{key}"] = value

        return await self._send_email(data, attachments)

    async def _send_email(
        self,
        data: dict[str, Any],
        attachments: list[Attachment] | None = None,
    ) -> SendResult:
        """Internal method to send email via Mailgun."""
        client = await self._get_client()

        try:
            if attachments:
                # Use multipart form for attachments
                files = []
                for att in attachments:
                    if att.data:
                        files.append(
                            ("attachment", (att.filename, att.data, att.content_type))
                        )
                response = await client.post(
                    f"{self._api_url}/messages",
                    data=data,
                    files=files,
                )
            else:
                response = await client.post(
                    f"{self._api_url}/messages",
                    data=data,
                )

            response.raise_for_status()
            result = response.json()

            return SendResult(
                success=True,
                external_id=result.get("id"),
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Mailgun API error: {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_msg = error_body.get("message", error_msg)
            except Exception:
                pass

            logger.error("Failed to send email: %s", error_msg)

            # Rate limit is retryable
            retryable = e.response.status_code == 429
            return SendResult(success=False, error=error_msg, retryable=retryable)

        except httpx.TimeoutException:
            logger.error("Mailgun API timeout")
            return SendResult(success=False, error="Timeout", retryable=True)

        except Exception as e:
            logger.exception("Unexpected error sending email")
            raise SendError(str(e), retryable=False) from e

    async def parse_webhook(self, payload: dict[str, Any]) -> InboundMessage:
        """
        Parse Mailgun inbound webhook payload.

        Mailgun sends form-encoded data with:
        - sender: From email
        - recipient: To email
        - subject: Email subject
        - body-plain: Plain text content
        - body-html: HTML content (optional)
        - stripped-text: Reply content without quoted text
        - Message-Id: Original message ID
        - timestamp: Unix timestamp
        - token: Verification token
        - signature: HMAC signature
        """
        # Use stripped-text if available (removes quoted replies)
        content = payload.get("stripped-text") or payload.get("body-plain", "")
        content = extract_reply_content(content)

        # Parse timestamp
        timestamp_str = payload.get("timestamp", "")
        try:
            timestamp = datetime.fromtimestamp(int(timestamp_str))
        except (ValueError, TypeError):
            timestamp = datetime.now(UTC)

        # Parse attachments if present
        attachments: list[Attachment] = []
        attachment_count = int(payload.get("attachment-count", 0))
        for i in range(1, attachment_count + 1):
            att_data = payload.get(f"attachment-{i}")
            if att_data and hasattr(att_data, "filename"):
                attachments.append(
                    Attachment(
                        filename=att_data.filename,
                        content_type=att_data.content_type or "application/octet-stream",
                        data=att_data.file.read() if hasattr(att_data, "file") else None,
                    )
                )

        return InboundMessage(
            external_id=payload.get("Message-Id", ""),
            channel=Channel.EMAIL,
            sender_identifier=payload.get("sender", ""),
            content=content,
            subject=payload.get("subject"),
            attachments=attachments,
            timestamp=timestamp,
            raw_payload=payload,
        )

    def verify_signature(
        self,
        payload: bytes,  # Not used for Mailgun
        signature: str,
        timestamp: str | None = None,
        token: str | None = None,
    ) -> bool:
        """
        Verify Mailgun webhook signature.

        Mailgun uses: HMAC-SHA256(timestamp + token, signing_key)
        """
        if not timestamp or not token:
            return False

        # Use webhook signing key if set, otherwise fall back to API key
        signing_key = (
            self._settings.mailgun_webhook_signing_key
            or self._settings.mailgun_api_key
        )

        expected = hmac.new(
            signing_key.encode(),
            f"{timestamp}{token}".encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def verify_webhook_payload(self, payload: dict[str, Any]) -> bool:
        """
        Convenience method to verify webhook from parsed form data.

        Args:
            payload: Parsed form data from Mailgun webhook
        """
        timestamp = str(payload.get("timestamp", ""))
        token = str(payload.get("token", ""))
        signature = str(payload.get("signature", ""))

        return self.verify_signature(b"", signature, timestamp, token)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


def extract_reply_content(body: str) -> str:
    """
    Extract just the reply portion from an email.

    Removes:
    - Quoted previous messages (lines starting with >)
    - Email signatures (after -- or common signature patterns)
    - "On [date], [person] wrote:" headers
    """
    if not body:
        return ""

    lines = body.split("\n")
    result_lines: list[str] = []
    in_signature = False

    for line in lines:
        stripped = line.strip()

        # Check for signature delimiter
        if stripped == "--" or stripped == "-- ":
            in_signature = True
            continue

        if in_signature:
            continue

        # Skip quoted lines
        if stripped.startswith(">"):
            continue

        # Check for "On ... wrote:" pattern (start of quoted section)
        if re.match(r"^On .+ wrote:$", stripped):
            break

        # Check for common reply headers
        if re.match(r"^-+\s*Original Message\s*-+$", stripped, re.IGNORECASE):
            break

        if re.match(r"^From:\s+.+$", stripped) and len(result_lines) > 0:
            # Likely start of forwarded/quoted email headers
            break

        result_lines.append(line)

    # Clean up trailing whitespace
    while result_lines and not result_lines[-1].strip():
        result_lines.pop()

    return "\n".join(result_lines).strip()


def format_ember_email(
    content: str,
    player_name: str | None = None,
) -> tuple[str, str]:
    """
    Format message content as Ember's email style.

    Returns:
        Tuple of (html_content, plain_text_content)
    """
    # Plain text is just the content
    plain_text = content

    # HTML with minimal styling (Ember is anxious, not fancy)
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Georgia, serif; font-size: 14px; line-height: 1.6; color: #333;">
    {content.replace(chr(10), '<br>')}
</body>
</html>"""

    return html, plain_text
