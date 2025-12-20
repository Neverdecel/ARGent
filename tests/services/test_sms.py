"""Tests for SMSService (Twilio)."""

import base64
import hashlib
import hmac
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from argent.services.sms import SMSService
from argent.services import OutboundMessage, Channel


class TestSMSServiceSignature:
    """Tests for Twilio webhook signature verification."""

    @pytest.fixture
    def service(self):
        """Create SMSService with mocked settings."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = "test-auth-token"
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = True
            yield SMSService()

    def test_compute_signature(self, service):
        """Test Twilio signature computation algorithm."""
        # Test with known values
        url = "https://example.com/webhook/twilio"
        params = {"Body": "Hello", "From": "+15559876543"}

        signature = service._compute_signature(url, params)

        # Signature should be base64-encoded HMAC-SHA1
        assert len(signature) > 0
        # Should be valid base64
        base64.b64decode(signature)

    def test_verify_webhook_request_valid(self, service):
        """Test valid signature verification."""
        url = "https://example.com/webhook/twilio"
        params = {"Body": "Hello", "From": "+15559876543"}

        # Compute the expected signature
        expected_signature = service._compute_signature(url, params)

        result = service.verify_webhook_request(
            url=url,
            params=params,
            signature=expected_signature,
        )
        assert result is True

    def test_verify_webhook_request_invalid(self, service):
        """Test invalid signature rejection."""
        result = service.verify_webhook_request(
            url="https://example.com/webhook/twilio",
            params={"Body": "Hello"},
            signature="invalid-signature",
        )
        assert result is False

    def test_verify_signature_empty_token_skips(self):
        """Test that empty auth token skips verification (with warning)."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = ""
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = True

            service = SMSService()
            result = service.verify_webhook_request(
                url="https://example.com",
                params={},
                signature="anything",
            )
            assert result is True  # No token configured, allows all

    def test_verify_signature_without_url(self, service):
        """Test that verification fails without URL."""
        result = service.verify_signature(
            payload=b"",
            signature="some-signature",
            url=None,
        )
        assert result is False


class TestSMSServiceParseWebhook:
    """Tests for parsing Twilio webhook payloads."""

    @pytest.fixture
    def service(self):
        """Create SMSService with mocked settings."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = "test-auth-token"
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = True
            yield SMSService()

    @pytest.mark.asyncio
    async def test_parse_webhook_text_message(self, service):
        """Test parsing a standard SMS message."""
        payload = {
            "MessageSid": "SM12345",
            "From": "+15559876543",
            "To": "+15551234567",
            "Body": "Hello Miro!",
            "NumMedia": "0",
        }

        result = await service.parse_webhook(payload)

        assert result.external_id == "SM12345"
        assert result.sender_identifier == "+15559876543"
        assert result.content == "Hello Miro!"
        assert result.channel == Channel.SMS
        assert len(result.attachments) == 0

    @pytest.mark.asyncio
    async def test_parse_webhook_mms_with_media(self, service):
        """Test parsing MMS with media attachments."""
        payload = {
            "MessageSid": "MM67890",
            "From": "+15559876543",
            "To": "+15551234567",
            "Body": "Check this out!",
            "NumMedia": "2",
            "MediaUrl0": "https://api.twilio.com/media/image1.jpg",
            "MediaContentType0": "image/jpeg",
            "MediaUrl1": "https://api.twilio.com/media/doc.pdf",
            "MediaContentType1": "application/pdf",
        }

        result = await service.parse_webhook(payload)

        assert result.content == "Check this out!"
        assert len(result.attachments) == 2
        assert result.attachments[0].url == "https://api.twilio.com/media/image1.jpg"
        assert result.attachments[0].content_type == "image/jpeg"
        assert result.attachments[1].url == "https://api.twilio.com/media/doc.pdf"
        assert result.attachments[1].content_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_parse_webhook_empty_body(self, service):
        """Test parsing message with no body (media only)."""
        payload = {
            "MessageSid": "MM11111",
            "From": "+15559876543",
            "To": "+15551234567",
            "Body": "",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/image.jpg",
            "MediaContentType0": "image/jpeg",
        }

        result = await service.parse_webhook(payload)

        assert result.content == ""
        assert result.sender_identifier == "+15559876543"
        assert len(result.attachments) == 1

    @pytest.mark.asyncio
    async def test_parse_webhook_preserves_raw_payload(self, service):
        """Test that raw payload is preserved."""
        payload = {
            "MessageSid": "SM99999",
            "From": "+15559876543",
            "To": "+15551234567",
            "Body": "Test",
            "NumMedia": "0",
            "AccountSid": "AC12345",
            "SmsStatus": "received",
        }

        result = await service.parse_webhook(payload)

        assert result.raw_payload == payload
        assert result.raw_payload["AccountSid"] == "AC12345"


class TestSMSServiceSend:
    """Tests for sending messages via Twilio."""

    @pytest.fixture
    def service(self):
        """Create SMSService with mocked settings."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = "test-auth-token"
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = True
            yield SMSService()

    @pytest.mark.asyncio
    async def test_send_disabled_returns_success(self):
        """Test that disabled SMS returns success without sending."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = "test-token"
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = False

            service = SMSService()
            message = OutboundMessage(
                player_id=uuid4(),
                recipient="+15559876543",
                content="Hello!",
            )

            result = await service.send_message(message)

            assert result.success is True
            assert result.external_id == "disabled"

    @pytest.mark.asyncio
    async def test_send_message_success(self, service):
        """Test successful message send."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sid": "SM12345",
            "status": "queued",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            message = OutboundMessage(
                player_id=uuid4(),
                recipient="+15559876543",
                content="Hello from Miro!",
            )

            result = await service.send_message(message)

            assert result.success is True
            assert result.external_id == "SM12345"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_sms_with_media(self, service):
        """Test sending MMS with media URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sid": "MM67890",
            "status": "queued",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                to_number="+15559876543",
                body="Check this image",
                media_url="https://example.com/image.jpg",
            )

            assert result.success is True
            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["MediaUrl"] == "https://example.com/image.jpg"

    @pytest.mark.asyncio
    async def test_send_sms_custom_from_number(self, service):
        """Test sending SMS from a different number."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"sid": "SM11111", "status": "queued"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                to_number="+15559876543",
                body="Hello",
                from_number="+15550001111",
            )

            assert result.success is True
            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["From"] == "+15550001111"

    @pytest.mark.asyncio
    async def test_send_rate_limited_is_retryable(self, service):
        """Test that rate limit error is marked as retryable."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        error = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = error

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                to_number="+15559876543",
                body="Hello",
            )

            assert result.success is False
            assert result.retryable is True

    @pytest.mark.asyncio
    async def test_send_api_error_not_retryable(self, service):
        """Test that 4xx errors (except 429) are not retryable."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid phone number"}
        error = httpx.HTTPStatusError("Bad request", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = error

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                to_number="invalid",
                body="Hello",
            )

            assert result.success is False
            assert result.retryable is False

    @pytest.mark.asyncio
    async def test_send_timeout_is_retryable(self, service):
        """Test that timeout errors are retryable."""
        import httpx

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                to_number="+15559876543",
                body="Hello",
            )

            assert result.success is False
            assert result.error == "Timeout"
            assert result.retryable is True


class TestSMSServiceChannel:
    """Tests for channel property."""

    @pytest.fixture
    def service(self):
        """Create SMSService with mocked settings."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = "test-auth-token"
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = True
            yield SMSService()

    def test_channel_is_sms(self, service):
        """Test that channel property returns SMS."""
        assert service.channel == Channel.SMS


class TestSMSServiceClientManagement:
    """Tests for HTTP client lifecycle."""

    @pytest.fixture
    def service(self):
        """Create SMSService with mocked settings."""
        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = "AC12345"
            mock_settings.return_value.twilio_auth_token = "test-auth-token"
            mock_settings.return_value.twilio_phone_number = "+15551234567"
            mock_settings.return_value.sms_enabled = True
            yield SMSService()

    @pytest.mark.asyncio
    async def test_close_closes_client(self, service):
        """Test that close() properly closes the HTTP client."""
        # First, create a client
        mock_response = MagicMock()
        mock_response.json.return_value = {"sid": "SM12345", "status": "queued"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_async_client.return_value = mock_client_instance

            # Trigger client creation
            await service.send_sms(to_number="+15559876543", body="test")

            # Now close
            await service.close()

            # Client should have been closed
            mock_client_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_client(self, service):
        """Test that close() works even if no client was created."""
        # Should not raise
        await service.close()


@pytest.mark.integration
class TestSMSServiceIntegration:
    """Integration tests that actually send SMS via Twilio.

    These tests require valid Twilio credentials in .env.local or environment.
    Run with: pytest -m integration tests/services/test_sms.py -v -s
    """

    @pytest.fixture
    def twilio_credentials(self):
        """Get Twilio credentials from environment."""
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        test_phone = os.getenv("TEST_PHONE_NUMBER")

        if not all([account_sid, auth_token, phone_number, test_phone]):
            pytest.skip("Twilio credentials not configured in environment")

        return account_sid, auth_token, phone_number, test_phone

    @pytest.fixture
    def real_service(self, twilio_credentials):
        """Create SMSService with real Twilio credentials."""
        account_sid, auth_token, phone_number, _ = twilio_credentials

        with patch("argent.services.sms.get_settings") as mock_settings:
            mock_settings.return_value.twilio_account_sid = account_sid
            mock_settings.return_value.twilio_auth_token = auth_token
            mock_settings.return_value.twilio_phone_number = phone_number
            mock_settings.return_value.sms_enabled = True
            yield SMSService()

    @pytest.mark.asyncio
    async def test_send_real_sms(self, real_service, twilio_credentials):
        """Test sending a real SMS via Twilio."""
        _, _, _, test_phone = twilio_credentials

        message = OutboundMessage(
            player_id=uuid4(),
            recipient=test_phone,
            content="ARGent integration test - Miro is online.",
        )

        result = await real_service.send_message(message)

        # Clean up
        await real_service.close()

        assert result.success is True, f"Failed to send: {result.error}"
        assert result.external_id is not None
        print(f"SMS sent successfully! Message SID: {result.external_id}")
