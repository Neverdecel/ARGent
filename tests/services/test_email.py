"""Tests for EmailService."""

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
    """Tests for Resend webhook signature verification (placeholder)."""

    @pytest.fixture
    def service(self):
        """Create EmailService with mocked settings."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.resend_api_key = "re_test_key"
            mock_settings.return_value.email_from = "test@resend.dev"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    def test_verify_signature_valid(self, service):
        """Test signature verification returns True (placeholder for Resend)."""
        result = service.verify_signature(
            payload=b"",
            signature="any-signature",
            timestamp="1234567890",
            token="abc123",
        )
        # Resend verification is a placeholder that always returns True
        assert result is True

    def test_verify_webhook_payload_convenience_method(self, service):
        """Test the convenience method returns True (placeholder)."""
        payload = {
            "email_id": "test123",
            "from": "player@example.com",
            "text": "Hello",
        }

        result = service.verify_webhook_payload(payload)
        assert result is True


class TestEmailServiceParseWebhook:
    """Tests for parsing Resend webhook payloads."""

    @pytest.fixture
    def service(self):
        """Create EmailService with mocked settings."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.resend_api_key = "re_test_key"
            mock_settings.return_value.email_from = "test@resend.dev"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    @pytest.mark.asyncio
    async def test_parse_webhook_basic(self, service):
        """Test parsing basic Resend webhook payload."""
        payload = {
            "email_id": "abc123",
            "from": "player@example.com",
            "subject": "Re: The Key",
            "text": "I found something interesting.",
        }

        result = await service.parse_webhook(payload)

        assert result.sender_identifier == "player@example.com"
        assert result.content == "I found something interesting."
        assert result.subject == "Re: The Key"
        assert result.external_id == "abc123"
        assert result.channel.value == "email"

    @pytest.mark.asyncio
    async def test_parse_webhook_empty_fields(self, service):
        """Test parsing webhook with missing optional fields."""
        payload = {
            "email_id": "abc123",
        }

        result = await service.parse_webhook(payload)
        assert result.external_id == "abc123"
        assert result.sender_identifier == ""
        assert result.content == ""


class TestEmailServiceSend:
    """Tests for sending emails via Resend."""

    @pytest.fixture
    def service(self):
        """Create EmailService with mocked settings."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.resend_api_key = "re_test_key"
            mock_settings.return_value.email_from = "ember@resend.dev"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    @pytest.mark.asyncio
    async def test_send_disabled_returns_success(self):
        """Test that disabled email returns success without sending."""
        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.email_enabled = False
            mock_settings.return_value.resend_api_key = ""
            mock_settings.return_value.email_from = ""

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
        mock_response.json.return_value = {"id": "resend_msg_123"}
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
            assert result.external_id == "resend_msg_123"
            mock_client.post.assert_called_once()


# Integration tests - run with: pytest -m integration
@pytest.mark.integration
class TestEmailServiceIntegration:
    """Integration tests that actually send emails via Resend.

    These tests require valid Resend credentials in .env.local or environment.
    Run with: pytest -m integration tests/services/test_email.py
    """

    @pytest.fixture
    def resend_credentials(self):
        """Get Resend credentials from environment."""
        api_key = os.getenv("RESEND_API_KEY")

        if not api_key:
            pytest.skip("Resend credentials not configured in environment")

        return api_key

    @pytest.fixture
    def real_service(self, resend_credentials):
        """Create EmailService with real Resend credentials."""
        api_key = resend_credentials

        with patch("argent.services.email.get_settings") as mock_settings:
            mock_settings.return_value.resend_api_key = api_key
            mock_settings.return_value.email_from = "ARGent <onboarding@resend.dev>"
            mock_settings.return_value.email_enabled = True
            yield EmailService()

    @pytest.mark.asyncio
    async def test_send_real_email(self, real_service):
        """Test sending a real email via Resend."""
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
