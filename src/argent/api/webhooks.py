"""Webhook endpoints for receiving inbound messages."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.config import Settings, get_settings
from argent.database import get_db
from argent.models import Message, Player
from argent.services import Channel, Direction, EmailService, SMSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


# Service dependencies
def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService()


def get_sms_service() -> SMSService:
    """Get SMS service instance."""
    return SMSService()


@router.post("/mailgun")
async def mailgun_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """
    Handle inbound email from Mailgun.

    Mailgun sends form-encoded POST with signature verification.
    """
    if not settings.email_enabled:
        return {"status": "disabled"}

    # Get form data
    form_data = await request.form()
    payload = dict(form_data.items())

    # Verify signature
    if not email_service.verify_webhook_payload(payload):
        logger.warning("Invalid Mailgun webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Parse inbound message
    try:
        inbound = await email_service.parse_webhook(payload)
    except Exception as e:
        logger.exception("Failed to parse Mailgun webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {e}",
        ) from e

    # Find player by email
    player = await _find_player_by_email(db, inbound.sender_identifier)
    if not player:
        logger.info("Email from unknown sender: %s", inbound.sender_identifier)
        # Return 200 to prevent Mailgun retries and enumeration
        return {"status": "ignored", "reason": "unknown_sender"}

    # Create message metadata record
    message = await _create_message_record(
        db=db,
        player_id=player.id,
        channel=Channel.EMAIL,
        direction=Direction.INBOUND,
        external_id=inbound.external_id,
    )

    # Queue background processing (agent response)
    background_tasks.add_task(
        _process_inbound_message,
        message_id=message.id,
        content=inbound.content,
        channel=Channel.EMAIL,
    )

    return {"status": "received", "message_id": str(message.id)}


@router.post("/twilio")
async def twilio_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_twilio_signature: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
    sms_service: SMSService = Depends(get_sms_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Handle inbound SMS from Twilio.

    Twilio sends form-encoded POST with X-Twilio-Signature header.
    Must return TwiML response (empty is fine for no auto-reply).
    """
    if not settings.sms_enabled:
        # Return empty TwiML
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    # Get form data
    form_data = await request.form()
    payload = {key: str(value) for key, value in form_data.items()}

    # Verify signature
    # Note: For proper verification, we need the full URL including https
    # In production, pass the actual webhook URL
    webhook_url = str(request.url)
    if x_twilio_signature and not sms_service.verify_webhook_request(
        url=webhook_url,
        params=payload,
        signature=x_twilio_signature,
    ):
        logger.warning("Invalid Twilio webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Parse inbound message
    try:
        inbound = await sms_service.parse_webhook(payload)
    except Exception as e:
        logger.exception("Failed to parse Twilio webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {e}",
        ) from e

    # Ignore empty messages
    if not inbound.sender_identifier:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    # Find player by phone number
    player = await _find_player_by_phone(db, inbound.sender_identifier)
    if not player:
        logger.info("SMS from unknown number: %s", inbound.sender_identifier)
        # Return empty TwiML (no auto-reply to unknown numbers)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    # Create message metadata record
    message = await _create_message_record(
        db=db,
        player_id=player.id,
        channel=Channel.SMS,
        direction=Direction.INBOUND,
        external_id=inbound.external_id,
    )

    # Queue background processing
    background_tasks.add_task(
        _process_inbound_message,
        message_id=message.id,
        content=inbound.content,
        channel=Channel.SMS,
    )

    # Return empty TwiML - agent will respond asynchronously
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )


# Helper functions


async def _find_player_by_email(db: AsyncSession, email: str) -> Player | None:
    """Find player by email address."""
    result = await db.execute(select(Player).where(Player.email == email))
    return result.scalar_one_or_none()


async def _find_player_by_phone(db: AsyncSession, phone: str) -> Player | None:
    """Find player by phone number."""
    result = await db.execute(select(Player).where(Player.phone == phone))
    return result.scalar_one_or_none()


async def _create_message_record(
    db: AsyncSession,
    player_id: UUID,
    channel: Channel,
    direction: Direction,
    external_id: str,
    agent_id: str | None = None,
) -> Message:
    """Create message metadata record in database."""
    message = Message(
        player_id=player_id,
        agent_id=agent_id,
        channel=channel.value,
        direction=direction.value,
        external_id=external_id,
    )
    db.add(message)
    await db.flush()  # Get ID without committing
    return message


async def _process_inbound_message(
    message_id: UUID,
    content: str,
    channel: Channel,
) -> None:
    """
    Background task to process inbound message.

    This is a placeholder - actual implementation will:
    1. Store content in Memory Bank
    2. Route to appropriate agent (Ember/Miro)
    3. Generate and send response
    """
    # TODO: Implement with Story Engine integration
    logger.info(
        "Processing message %s from %s: %s",
        message_id,
        channel.value,
        content[:100] if content else "(empty)",
    )
