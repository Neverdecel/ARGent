"""Tests for webhook endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from argent.api.webhooks import get_email_service, get_sms_service
from argent.config import get_settings
from argent.database import get_db
from argent.main import app
from argent.services import Channel, InboundMessage


class TestMailgunWebhook:
    """Tests for Mailgun inbound webhook endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session that returns no player."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        return mock_session

    @pytest.fixture
    def mock_email_service_valid_sig(self):
        """Mock email service that accepts any signature."""
        service = MagicMock()
        service.verify_webhook_payload.return_value = True
        service.parse_webhook = AsyncMock(
            return_value=InboundMessage(
                external_id="<test@example.com>",
                channel=Channel.EMAIL,
                sender_identifier="unknown@example.com",
                content="Hello",
                subject="Test",
            )
        )
        return service

    @pytest.fixture
    def mock_email_service_invalid_sig(self):
        """Mock email service that rejects signature."""
        service = MagicMock()
        service.verify_webhook_payload.return_value = False
        return service

    @pytest.fixture
    def mock_settings_email_enabled(self):
        """Mock settings with email enabled."""
        settings = MagicMock()
        settings.email_enabled = True
        return settings

    @pytest.fixture
    def mock_settings_email_disabled(self):
        """Mock settings with email disabled."""
        settings = MagicMock()
        settings.email_enabled = False
        return settings

    @pytest.mark.asyncio
    async def test_mailgun_webhook_invalid_signature(
        self, mock_db, mock_email_service_invalid_sig, mock_settings_email_enabled
    ):
        """Test rejection of invalid Mailgun signature."""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_email_service] = lambda: mock_email_service_invalid_sig
        app.dependency_overrides[get_settings] = lambda: mock_settings_email_enabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/mailgun",
                    data={
                        "sender": "player@example.com",
                        "body-plain": "Hello",
                        "timestamp": "1234567890",
                        "token": "test-token",
                        "signature": "invalid-signature",
                    },
                )
                assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mailgun_webhook_unknown_sender(
        self, mock_db, mock_email_service_valid_sig, mock_settings_email_enabled
    ):
        """Test handling of email from unknown sender."""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_email_service] = lambda: mock_email_service_valid_sig
        app.dependency_overrides[get_settings] = lambda: mock_settings_email_enabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/mailgun",
                    data={
                        "sender": "unknown@example.com",
                        "body-plain": "Hello",
                        "timestamp": "123",
                        "token": "abc",
                        "signature": "xyz",
                    },
                )

                # Should return 200 to prevent retries
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ignored"
                assert data["reason"] == "unknown_sender"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mailgun_webhook_disabled(self, mock_settings_email_disabled):
        """Test that disabled email service returns disabled status."""
        app.dependency_overrides[get_settings] = lambda: mock_settings_email_disabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/mailgun",
                    data={
                        "sender": "player@example.com",
                        "body-plain": "Hello",
                        "timestamp": "123",
                        "token": "abc",
                        "signature": "xyz",
                    },
                )

                assert response.status_code == 200
                assert response.json()["status"] == "disabled"
        finally:
            app.dependency_overrides.clear()


class TestTwilioWebhook:
    """Tests for Twilio SMS webhook endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session that returns no player."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        return mock_session

    @pytest.fixture
    def mock_sms_service_valid(self):
        """Mock SMS service that accepts signature."""
        service = MagicMock()
        service.verify_webhook_request.return_value = True
        service.parse_webhook = AsyncMock(
            return_value=InboundMessage(
                external_id="SM12345",
                channel=Channel.SMS,
                sender_identifier="+15559876543",
                content="Hello Miro",
            )
        )
        return service

    @pytest.fixture
    def mock_sms_service_invalid(self):
        """Mock SMS service that rejects signature."""
        service = MagicMock()
        service.verify_webhook_request.return_value = False
        return service

    @pytest.fixture
    def mock_sms_service_no_sender(self):
        """Mock SMS service with empty sender."""
        service = MagicMock()
        service.verify_webhook_request.return_value = True
        service.parse_webhook = AsyncMock(
            return_value=InboundMessage(
                external_id="SM12345",
                channel=Channel.SMS,
                sender_identifier="",
                content="",
            )
        )
        return service

    @pytest.fixture
    def mock_settings_sms_enabled(self):
        """Mock settings with SMS enabled."""
        settings = MagicMock()
        settings.sms_enabled = True
        return settings

    @pytest.fixture
    def mock_settings_sms_disabled(self):
        """Mock settings with SMS disabled."""
        settings = MagicMock()
        settings.sms_enabled = False
        return settings

    @pytest.mark.asyncio
    async def test_twilio_webhook_invalid_signature(
        self, mock_db, mock_sms_service_invalid, mock_settings_sms_enabled
    ):
        """Test rejection with invalid Twilio signature."""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_sms_service] = lambda: mock_sms_service_invalid
        app.dependency_overrides[get_settings] = lambda: mock_settings_sms_enabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/twilio",
                    data={
                        "MessageSid": "SM12345",
                        "From": "+15559876543",
                        "To": "+15551234567",
                        "Body": "Hello",
                        "NumMedia": "0",
                    },
                    headers={"X-Twilio-Signature": "invalid-signature"},
                )
                assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_twilio_webhook_unknown_number(
        self, mock_db, mock_sms_service_valid, mock_settings_sms_enabled
    ):
        """Test handling of SMS from unknown phone number."""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_sms_service] = lambda: mock_sms_service_valid
        app.dependency_overrides[get_settings] = lambda: mock_settings_sms_enabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/twilio",
                    data={
                        "MessageSid": "SM12345",
                        "From": "+15559876543",
                        "To": "+15551234567",
                        "Body": "Hello Miro",
                        "NumMedia": "0",
                    },
                    headers={"X-Twilio-Signature": "valid-signature"},
                )

                # Should return 200 with empty TwiML
                assert response.status_code == 200
                assert "application/xml" in response.headers["content-type"]
                assert "<Response>" in response.text
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_twilio_webhook_no_sender(
        self, mock_db, mock_sms_service_no_sender, mock_settings_sms_enabled
    ):
        """Test handling of message without sender."""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_sms_service] = lambda: mock_sms_service_no_sender
        app.dependency_overrides[get_settings] = lambda: mock_settings_sms_enabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/twilio",
                    data={
                        "MessageSid": "SM12345",
                        "From": "",
                        "To": "+15551234567",
                        "Body": "",
                        "NumMedia": "0",
                    },
                    headers={"X-Twilio-Signature": "valid-signature"},
                )

                # Should return empty TwiML
                assert response.status_code == 200
                assert "<Response>" in response.text
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_twilio_webhook_disabled(self, mock_settings_sms_disabled):
        """Test that disabled SMS service returns empty TwiML."""
        app.dependency_overrides[get_settings] = lambda: mock_settings_sms_disabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/twilio",
                    data={
                        "MessageSid": "SM12345",
                        "From": "+15559876543",
                        "To": "+15551234567",
                        "Body": "Hello",
                        "NumMedia": "0",
                    },
                )

                assert response.status_code == 200
                assert "application/xml" in response.headers["content-type"]
                assert "<Response></Response>" in response.text
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_twilio_webhook_no_signature_header(
        self, mock_db, mock_sms_service_valid, mock_settings_sms_enabled
    ):
        """Test that missing signature header allows through (signature check skipped)."""
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_sms_service] = lambda: mock_sms_service_valid
        app.dependency_overrides[get_settings] = lambda: mock_settings_sms_enabled

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/twilio",
                    data={
                        "MessageSid": "SM12345",
                        "From": "+15559876543",
                        "To": "+15551234567",
                        "Body": "Hello",
                        "NumMedia": "0",
                    },
                    # No X-Twilio-Signature header
                )

                # Should still work (signature verification only happens if header present)
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
