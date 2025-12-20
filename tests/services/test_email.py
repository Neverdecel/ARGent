"""Tests for EmailService."""

import hashlib
import hmac
import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from argent.services import OutboundMessage
from argent.services.email import EmailService, extract_reply_content


class TestExtractReplyContent:
    """Tests for extract_reply_content helper function."""

    def test_plain_text(self):
        """Test extracting from plain text without quotes."""
        body = "Hello, this is my message."
        result = extract_reply_content(body)
        assert result == "Hello, this is my message."

    def test_removes_quoted_lines(self):
        """Test removal of quoted lines starting with >."""
        body = """This is my reply.

> This is quoted text
> More quoted text"""
        result = extract_reply_content(body)
        assert result == "This is my reply."

    def test_removes_on_wrote_pattern(self):
        """Test removal of 'On ... wrote:' pattern and everything after."""
        body = """Thanks for the info!

On Mon, Dec 20, 2025 at 10:00 AM Ember wrote:
Here is the original message."""
        result = extract_reply_content(body)
        assert result == "Thanks for the info!"

    def test_removes_signature(self):
        """Test removal of email signature after --."""
        body = """This is my message.

--
Best regards,
John Doe"""
        result = extract_reply_content(body)
        assert result == "This is my message."

    def test_removes_original_message_header(self):
        """Test removal of ----- Original Message ----- pattern."""
        body = """My reply here.

----- Original Message -----
From: someone@example.com
To: me@example.com"""
        result = extract_reply_content(body)
        assert result == "My reply here."

    def test_empty_body(self):
        """Test handling of empty body."""
        assert extract_reply_content("") == ""
        assert extract_reply_content(None) == ""

    def test_complex_email(self):
        """Test complex email with multiple sections to strip."""
        body = """Thanks, I got it!

> Previous message
> More previous

On Mon, Dec 20 wrote:
> Even older message

--
Signature"""
        result = extract_reply_content(body)
        assert result == "Thanks, I got it!"


class TestEmailServiceSignature:
    """Tests for Mailgun webhook signature verification."""

    @pytest.fixture
    def service(self):
        """Create EmailService with mocked settings."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.mailgun_api_key = "test-api-key"
            mock_settings.return_value.mailgun_webhook_signing_key = ""
            mock_settings.return_value.mailgun_domain = "test.mailgun.org"
            mock_settings.return_value.email_from = "test@test.mailgun.org"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    def test_verify_signature_valid(self, service):
        """Test valid signature verification."""
        timestamp = "1234567890"
        token = "abc123"
        # Calculate expected signature using API key (no webhook key set)
        expected_signature = hmac.new(
            b"test-api-key",
            f"{timestamp}{token}".encode(),
            hashlib.sha256,
        ).hexdigest()

        result = service.verify_signature(
            payload=b"",
            signature=expected_signature,
            timestamp=timestamp,
            token=token,
        )
        assert result is True

    def test_verify_signature_invalid(self, service):
        """Test invalid signature rejection."""
        result = service.verify_signature(
            payload=b"",
            signature="invalid-signature",
            timestamp="1234567890",
            token="abc123",
        )
        assert result is False

    def test_verify_signature_missing_timestamp(self, service):
        """Test rejection when timestamp is missing."""
        result = service.verify_signature(
            payload=b"",
            signature="any-signature",
            timestamp=None,
            token="abc123",
        )
        assert result is False

    def test_verify_signature_missing_token(self, service):
        """Test rejection when token is missing."""
        result = service.verify_signature(
            payload=b"",
            signature="any-signature",
            timestamp="1234567890",
            token=None,
        )
        assert result is False

    def test_verify_webhook_payload_convenience_method(self, service):
        """Test the convenience method for verifying form data."""
        timestamp = "1234567890"
        token = "abc123"
        signature = hmac.new(
            b"test-api-key",
            f"{timestamp}{token}".encode(),
            hashlib.sha256,
        ).hexdigest()

        payload = {
            "timestamp": timestamp,
            "token": token,
            "signature": signature,
            "sender": "player@example.com",
            "body-plain": "Hello",
        }

        result = service.verify_webhook_payload(payload)
        assert result is True


class TestEmailServiceParseWebhook:
    """Tests for parsing Mailgun webhook payloads."""

    @pytest.fixture
    def service(self):
        """Create EmailService with mocked settings."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.mailgun_api_key = "test-api-key"
            mock_settings.return_value.mailgun_webhook_signing_key = ""
            mock_settings.return_value.mailgun_domain = "test.mailgun.org"
            mock_settings.return_value.email_from = "test@test.mailgun.org"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    @pytest.mark.asyncio
    async def test_parse_webhook_basic(self, service):
        """Test parsing basic webhook payload."""
        payload = {
            "sender": "player@example.com",
            "recipient": "ember@game.com",
            "subject": "Re: The Key",
            "body-plain": "I found something interesting.",
            "stripped-text": "I found something interesting.",
            "Message-Id": "<abc123@example.com>",
            "timestamp": "1734710400",
        }

        result = await service.parse_webhook(payload)

        assert result.sender_identifier == "player@example.com"
        assert result.content == "I found something interesting."
        assert result.subject == "Re: The Key"
        assert result.external_id == "<abc123@example.com>"
        assert result.channel.value == "email"

    @pytest.mark.asyncio
    async def test_parse_webhook_prefers_stripped_text(self, service):
        """Test that stripped-text is preferred over body-plain."""
        payload = {
            "sender": "player@example.com",
            "body-plain": "My reply\n\n> Quoted text\n> More quoted",
            "stripped-text": "My reply",
            "Message-Id": "<abc@example.com>",
            "timestamp": "1734710400",
        }

        result = await service.parse_webhook(payload)
        assert result.content == "My reply"

    @pytest.mark.asyncio
    async def test_parse_webhook_falls_back_to_body_plain(self, service):
        """Test fallback to body-plain when stripped-text is missing."""
        payload = {
            "sender": "player@example.com",
            "body-plain": "This is the full body.",
            "Message-Id": "<abc@example.com>",
            "timestamp": "1734710400",
        }

        result = await service.parse_webhook(payload)
        assert result.content == "This is the full body."


class TestEmailServiceSend:
    """Tests for sending emails via Mailgun."""

    @pytest.fixture
    def service(self):
        """Create EmailService with mocked settings."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.mailgun_api_key = "test-api-key"
            mock_settings.return_value.mailgun_webhook_signing_key = ""
            mock_settings.return_value.mailgun_domain = "test.mailgun.org"
            mock_settings.return_value.email_from = "ember@test.mailgun.org"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    @pytest.mark.asyncio
    async def test_send_disabled_returns_success(self):
        """Test that disabled email returns success without sending."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.email_enabled = False
            mock_settings.return_value.mailgun_api_key = ""
            mock_settings.return_value.mailgun_domain = ""
            mock_settings.return_value.email_from = ""
            mock_settings.return_value.mailgun_webhook_signing_key = ""

            service = EmailService()
            message = OutboundMessage(
                player_id=uuid4(),
                recipient="player@example.com",
                content="Hello!",
            )

            result = await service.send_message(message)

            assert result.success is True
            assert result.external_id == "disabled"

    @pytest.mark.asyncio
    async def test_send_message_success(self, service):
        """Test successful email send (mocked)."""
        from unittest.mock import MagicMock

        # Mock the HTTP client - response.json() is synchronous in httpx
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "<msg123@mailgun.org>"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            message = OutboundMessage(
                player_id=uuid4(),
                recipient="player@example.com",
                content="Hello from Ember!",
                subject="Important Message",
            )

            result = await service.send_message(message)

            assert result.success is True
            assert result.external_id == "<msg123@mailgun.org>"
            mock_client.post.assert_called_once()


# Integration tests - run with: pytest -m integration
@pytest.mark.integration
class TestEmailServiceIntegration:
    """Integration tests that actually send emails via Mailgun sandbox.

    These tests require valid Mailgun credentials in .env.local or environment.
    Run with: pytest -m integration tests/services/test_email.py
    """

    @pytest.fixture
    def mailgun_credentials(self):
        """Get Mailgun credentials from environment."""
        api_key = os.getenv("MAILGUN_API_KEY")
        domain = os.getenv("MAILGUN_DOMAIN")

        if not api_key or not domain:
            pytest.skip("Mailgun credentials not configured in environment")

        return api_key, domain

    @pytest.fixture
    def real_service(self, mailgun_credentials):
        """Create EmailService with real Mailgun sandbox credentials."""
        api_key, domain = mailgun_credentials

        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.mailgun_api_key = api_key
            mock_settings.return_value.mailgun_domain = domain
            mock_settings.return_value.mailgun_webhook_signing_key = ""
            mock_settings.return_value.email_from = f"Mailgun Sandbox <postmaster@{domain}>"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    @pytest.mark.asyncio
    async def test_send_real_email(self, real_service, mailgun_credentials):
        """Test sending a real email via Mailgun sandbox."""
        _, domain = mailgun_credentials

        message = OutboundMessage(
            player_id=uuid4(),
            recipient="argent-protocol@proton.me",
            content="This is a test email from ARGent communication services integration test.",
            subject="ARGent Integration Test",
        )

        result = await real_service.send_message(message)

        # Clean up
        await real_service.close()

        assert result.success is True, f"Failed to send: {result.error}"
        assert result.external_id is not None
        print(f"Email sent successfully! Message ID: {result.external_id}")

    @pytest.mark.asyncio
    async def test_send_raw_email(self, real_service):
        """Test sending email with send_raw method."""
        result = await real_service.send_raw(
            to_email="argent-protocol@proton.me",
            subject="ARGent Raw Send Test",
            text_content="This is a raw send test from ARGent.",
            html_content="<p>This is a <strong>raw send test</strong> from ARGent.</p>",
        )

        await real_service.close()

        assert result.success is True, f"Failed to send: {result.error}"
        assert result.external_id is not None
        print(f"Raw email sent successfully! Message ID: {result.external_id}")
