"""Email service using Resend API."""

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
)

logger = logging.getLogger(__name__)


class EmailService(BaseChannelService):
    """Resend-based email service."""

    RESEND_API_BASE = "https://api.resend.com"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def channel(self) -> Channel:
        return Channel.EMAIL

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self._settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send email via Resend API."""
        if not self._settings.email_enabled:
            logger.info("Email disabled, skipping send to %s", message.recipient)
            return SendResult(success=True, external_id="disabled")

        data: dict[str, Any] = {
            "from": self._settings.email_from,
            "to": [message.recipient],
            "text": message.content,
        }

        if message.subject:
            data["subject"] = message.subject

        if message.html_content:
            data["html"] = message.html_content

        if message.reply_to_external_id:
            data["headers"] = {
                "In-Reply-To": message.reply_to_external_id,
                "References": message.reply_to_external_id,
            }

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
            "to": [to_email],
            "subject": subject,
            "text": text_content,
        }

        if html_content:
            data["html"] = html_content

        headers: dict[str, str] = {}
        if reply_to_message_id:
            headers["In-Reply-To"] = reply_to_message_id
            headers["References"] = reply_to_message_id

        if custom_headers:
            headers.update(custom_headers)

        if headers:
            data["headers"] = headers

        return await self._send_email(data, attachments)

    async def _send_email(
        self,
        data: dict[str, Any],
        attachments: list[Attachment] | None = None,
    ) -> SendResult:
        """Internal method to send email via Resend."""
        client = await self._get_client()

        # Add attachments if present
        if attachments:
            data["attachments"] = [
                {
                    "filename": att.filename,
                    "content": att.data.decode() if att.data else "",
                }
                for att in attachments
                if att.data
            ]

        try:
            response = await client.post(
                f"{self.RESEND_API_BASE}/emails",
                json=data,
            )

            response.raise_for_status()
            result = response.json()

            logger.info("Email sent via Resend: %s", result.get("id"))
            return SendResult(
                success=True,
                external_id=result.get("id"),
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Resend API error: {e.response.status_code}"
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
            logger.error("Resend API timeout")
            return SendResult(success=False, error="Timeout", retryable=True)

        except Exception as e:
            logger.exception("Unexpected error sending email")
            raise SendError(str(e), retryable=False) from e

    async def parse_webhook(self, payload: dict[str, Any]) -> InboundMessage:
        """
        Parse Resend inbound webhook payload.

        Note: Resend webhooks are for delivery events, not inbound emails.
        For inbound email handling, you'd need a different service or
        forward to a different endpoint.
        """
        # Basic implementation - Resend doesn't handle inbound emails the same way
        return InboundMessage(
            external_id=payload.get("email_id", ""),
            channel=Channel.EMAIL,
            sender_identifier=payload.get("from", ""),
            content=payload.get("text", ""),
            subject=payload.get("subject"),
            attachments=[],
            timestamp=datetime.now(UTC),
            raw_payload=payload,
        )

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str | None = None,
        token: str | None = None,
    ) -> bool:
        """
        Verify Resend webhook signature.

        Resend uses svix for webhooks - implementation depends on webhook setup.
        For now, return True as placeholder.
        """
        # TODO: Implement proper svix signature verification if using webhooks
        return True

    def verify_webhook_payload(self, payload: dict[str, Any]) -> bool:
        """Verify webhook from parsed data."""
        return True

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
    {content.replace(chr(10), "<br>")}
</body>
</html>"""

    return html, plain_text
