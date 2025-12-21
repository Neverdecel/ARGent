"""Onboarding API endpoints for player registration and verification."""

import logging
import re
import secrets
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.config import Settings, get_settings
from argent.database import get_db
from argent.models import Player, PlayerKey
from argent.services import EmailService, SMSService
from argent.services.verification import VerificationService, get_verification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["onboarding"])

# E.164 phone number format: +[country code][number]
E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")

# Cookie settings
SESSION_COOKIE_NAME = "argent_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


# Request/Response models


class RegisterRequest(BaseModel):
    """Registration request body."""

    email: EmailStr
    phone: str
    timezone: str = "UTC"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone is in E.164 format."""
        if not E164_PATTERN.match(v):
            raise ValueError("Phone must be in E.164 format (e.g., +1234567890)")
        return v


class PhoneVerifyRequest(BaseModel):
    """Phone verification request body."""

    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate code is 6 digits."""
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Code must be 6 digits")
        return v


class VerificationStatusResponse(BaseModel):
    """Verification status response."""

    email: str
    phone: str
    email_verified: bool
    phone_verified: bool
    can_start_game: bool


class RegisterResponse(BaseModel):
    """Registration response."""

    success: bool
    message: str
    redirect: str


class VerifyResponse(BaseModel):
    """Verification response."""

    success: bool
    message: str


# Session helpers


def _create_session_serializer(settings: Settings) -> URLSafeTimedSerializer:
    """Create a serializer for session cookies."""
    return URLSafeTimedSerializer(settings.secret_key, salt="session")


def _create_session_cookie(
    response: Response,
    player_id: UUID,
    settings: Settings,
) -> None:
    """Set a signed session cookie with the player ID."""
    serializer = _create_session_serializer(settings)
    session_data = serializer.dumps(str(player_id))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_data,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
    )


def _get_player_id_from_session(
    session_cookie: str | None,
    settings: Settings,
) -> UUID | None:
    """Extract player ID from session cookie."""
    if not session_cookie:
        return None
    try:
        serializer = _create_session_serializer(settings)
        player_id_str = serializer.loads(session_cookie, max_age=SESSION_MAX_AGE)
        return UUID(player_id_str)
    except (BadSignature, ValueError):
        return None


# Service dependencies


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService()


def get_sms_service() -> SMSService:
    """Get SMS service instance."""
    return SMSService()


# Endpoints


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    verification_service: VerificationService = Depends(get_verification_service),
    email_service: EmailService = Depends(get_email_service),
    sms_service: SMSService = Depends(get_sms_service),
    settings: Settings = Depends(get_settings),
) -> RegisterResponse:
    """
    Register a new player.

    Creates player record, generates verification tokens, and sends
    verification email and SMS.
    """
    # Check if email already exists
    existing = await db.execute(select(Player).where(Player.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if phone already exists
    existing = await db.execute(select(Player).where(Player.phone == request.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )

    # Create player
    player = Player(
        email=request.email,
        phone=request.phone,
        timezone=request.timezone,
        email_verified=False,
        phone_verified=False,
    )
    db.add(player)
    await db.flush()

    # Generate verification tokens
    email_token = await verification_service.create_email_token(player.id)
    phone_code = await verification_service.create_phone_code(player.id)

    # Send verification email
    verification_url = f"{settings.base_url}/api/verify/email/{email_token}"
    email_sent = await _send_verification_email(
        email_service=email_service,
        to_email=request.email,
        verification_url=verification_url,
        settings=settings,
    )
    if not email_sent:
        logger.warning("Failed to send verification email to %s", request.email)

    # Send verification SMS
    sms_sent = await _send_verification_sms(
        sms_service=sms_service,
        to_phone=request.phone,
        code=phone_code,
        settings=settings,
    )
    if not sms_sent:
        logger.warning("Failed to send verification SMS to %s", request.phone)

    # Set session cookie
    _create_session_cookie(response, player.id, settings)

    logger.info("Player registered: %s", player.id)

    return RegisterResponse(
        success=True,
        message="Registration successful. Please check your email and phone.",
        redirect="/verify",
    )


@router.get("/verify/email/{token}")
async def verify_email(
    token: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    verification_service: VerificationService = Depends(get_verification_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Verify email address via click-link.

    Redirects to success page on valid token, error page on invalid.
    """
    player_id = await verification_service.verify_email_token(token)

    if player_id is None:
        # Redirect to verify page with error
        response.status_code = status.HTTP_303_SEE_OTHER
        response.headers["Location"] = "/verify?error=invalid_email_token"
        return response

    # Update player email_verified
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if player:
        player.email_verified = True
        await db.flush()
        logger.info("Email verified for player: %s", player_id)

        # Set session cookie if not already set
        _create_session_cookie(response, player_id, settings)

    # Redirect to success page
    response.status_code = status.HTTP_303_SEE_OTHER
    response.headers["Location"] = "/verify/email/success"
    return response


@router.post("/verify/phone", response_model=VerifyResponse)
async def verify_phone(
    request: PhoneVerifyRequest,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    verification_service: VerificationService = Depends(get_verification_service),
    settings: Settings = Depends(get_settings),
) -> VerifyResponse:
    """
    Verify phone number via 6-digit code.
    """
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if player_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please register again.",
        )

    # Verify the code
    is_valid = await verification_service.verify_phone_code(player_id, request.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    # Update player phone_verified
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if player:
        player.phone_verified = True
        await db.flush()
        logger.info("Phone verified for player: %s", player_id)

    return VerifyResponse(
        success=True,
        message="Phone verified successfully",
    )


@router.post("/verify/phone/resend", response_model=VerifyResponse)
async def resend_phone_code(
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    verification_service: VerificationService = Depends(get_verification_service),
    sms_service: SMSService = Depends(get_sms_service),
    settings: Settings = Depends(get_settings),
) -> VerifyResponse:
    """
    Resend phone verification code.

    Rate limited to one code per 60 seconds.
    """
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if player_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please register again.",
        )

    # Check rate limit
    can_resend, seconds_remaining = await verification_service.can_resend_phone_code(player_id)
    if not can_resend:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {seconds_remaining} seconds before requesting a new code",
        )

    # Get player phone number
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player or not player.phone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found",
        )

    # Generate new code
    phone_code = await verification_service.create_phone_code(player_id)

    # Send SMS
    sms_sent = await _send_verification_sms(
        sms_service=sms_service,
        to_phone=player.phone,
        code=phone_code,
        settings=settings,
    )

    if not sms_sent:
        logger.warning("Failed to resend verification SMS to %s", player.phone)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send SMS. Please try again.",
        )

    return VerifyResponse(
        success=True,
        message="Verification code sent",
    )


@router.get("/verification-status", response_model=VerificationStatusResponse)
async def verification_status(
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VerificationStatusResponse:
    """
    Get current verification status for the player.
    """
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if player_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in",
        )

    # Get player
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found",
        )

    return VerificationStatusResponse(
        email=player.email,
        phone=player.phone or "",
        email_verified=player.email_verified,
        phone_verified=player.phone_verified,
        can_start_game=player.email_verified and player.phone_verified,
    )


@router.post("/start-game", response_model=VerifyResponse)
async def start_game(
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> VerifyResponse:
    """
    Start the game for the player.

    Requires both email and phone to be verified.
    Creates a player key and sends "The Key" email.
    """
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if player_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in",
        )

    # Get player
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found",
        )

    # Check verification status
    if not player.email_verified or not player.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Both email and phone must be verified to start the game",
        )

    # Check if game already started
    if player.game_started_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game already started",
        )

    # Generate player key
    key_value = _generate_player_key()
    player_key = PlayerKey(
        player_id=player.id,
        key_value=key_value,
    )
    db.add(player_key)

    # Mark game as started
    player.game_started_at = datetime.now(UTC)
    await db.flush()

    # Send "The Key" email
    email_sent = await _send_the_key_email(
        email_service=email_service,
        to_email=player.email,
        key=key_value,
        settings=settings,
    )
    if not email_sent:
        logger.warning("Failed to send The Key email to %s", player.email)

    logger.info("Game started for player: %s", player_id)

    return VerifyResponse(
        success=True,
        message="The game has begun. Check your email.",
    )


# Helper functions


def _generate_player_key() -> str:
    """Generate a unique player key.

    Format: XXXX-XXXX-XXXX-XXXX (hex characters)
    """
    raw = secrets.token_hex(8)  # 16 hex chars
    return "-".join([raw[i : i + 4].upper() for i in range(0, 16, 4)])


async def _send_verification_email(
    email_service: EmailService,
    to_email: str,
    verification_url: str,
    settings: Settings,
) -> bool:
    """Send verification email."""
    if not settings.email_enabled:
        logger.info("Email disabled - skipping verification email")
        return True

    subject = "Verify your identity"
    text_content = f"""You requested access to ARGent.

Click the link below to verify your email address:

{verification_url}

This link expires in 24 hours.

If you did not request this, ignore this email.

---
ARGent
"""
    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Georgia, serif; color: #e0e0e0; background: #1a1a1a; padding: 20px;">
<p>You requested access to ARGent.</p>
<p>Click the button below to verify your email address:</p>
<p style="margin: 30px 0;">
    <a href="{verification_url}"
       style="background: #4a4a4a; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
       Verify Email
    </a>
</p>
<p style="color: #888; font-size: 14px;">This link expires in 24 hours.</p>
<p style="color: #888; font-size: 14px;">If you did not request this, ignore this email.</p>
<hr style="border: none; border-top: 1px solid #333; margin: 30px 0;">
<p style="color: #666; font-size: 12px;">ARGent</p>
</body>
</html>
"""

    result = await email_service.send_raw(
        to_email=to_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        from_email=settings.email_from,
    )
    return result.success


async def _send_verification_sms(
    sms_service: SMSService,
    to_phone: str,
    code: str,
    settings: Settings,
) -> bool:
    """Send verification SMS."""
    if not settings.sms_enabled:
        logger.info("SMS disabled - skipping verification SMS")
        return True

    message = f"Your ARGent verification code is: {code}\n\nThis code expires in 10 minutes."

    result = await sms_service.send_sms(
        to_number=to_phone,
        body=message,
    )
    return result.success


async def _send_the_key_email(
    email_service: EmailService,
    to_email: str,
    key: str,
    settings: Settings,
) -> bool:
    """Send 'The Key' email that starts the ARG.

    This is the cryptic email that kicks off the game.
    """
    if not settings.email_enabled:
        logger.info("Email disabled - skipping The Key email")
        return True

    subject = "You have a new message"

    # The cryptic email from Ember's perspective (misdirected)
    text_content = f"""
---

This wasn't meant for you.

But since you're here... I need you to understand something.
There's a key. It unlocks something important.

{key}

Use before Thursday. Or don't. I can't tell you what to do.

Just... be careful who you talk to about this.

- E

---

If you received this in error, please delete it immediately.
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Courier New', monospace; color: #c0c0c0; background: #0a0a0a; padding: 40px; max-width: 600px;">
<div style="border-left: 2px solid #333; padding-left: 20px;">
<p style="color: #888;">---</p>
<p>This wasn't meant for you.</p>
<p>But since you're here... I need you to understand something.<br>
There's a key. It unlocks something important.</p>
<p style="font-size: 18px; background: #1a1a1a; padding: 15px; font-family: monospace; letter-spacing: 2px; color: #00ff88;">
{key}
</p>
<p>Use before Thursday. Or don't. I can't tell you what to do.</p>
<p>Just... be careful who you talk to about this.</p>
<p style="margin-top: 30px;">- E</p>
<p style="color: #888;">---</p>
</div>
<p style="color: #555; font-size: 11px; margin-top: 40px; font-style: italic;">
If you received this in error, please delete it immediately.
</p>
</body>
</html>
"""

    result = await email_service.send_raw(
        to_email=to_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        from_email="unknown@noreply.localhost",  # Mysterious sender
    )
    return result.success
