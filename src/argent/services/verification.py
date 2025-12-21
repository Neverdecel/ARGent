"""Verification token service for email and phone verification.

This service handles:
- Token generation (email: 32-byte URL-safe, phone: 6-digit code)
- Token validation and consumption
- Rate limiting for SMS resends
- Token cleanup for expired tokens
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.config import get_settings
from argent.database import get_db
from argent.models.verification import TokenType, VerificationToken

# Token specifications
EMAIL_TOKEN_BYTES = 32
EMAIL_TOKEN_EXPIRY_HOURS = 24
PHONE_CODE_LENGTH = 6
PHONE_CODE_EXPIRY_MINUTES = 10
PHONE_RESEND_COOLDOWN_SECONDS = 60


def _hash_token(token: str) -> str:
    """Hash a token using SHA256."""
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_email_token() -> str:
    """Generate a cryptographically secure URL-safe email token."""
    return secrets.token_urlsafe(EMAIL_TOKEN_BYTES)


def _generate_phone_code() -> str:
    """Generate a 6-digit numeric verification code."""
    # Use secrets for cryptographic randomness
    code = secrets.randbelow(10**PHONE_CODE_LENGTH)
    return str(code).zfill(PHONE_CODE_LENGTH)


class VerificationService:
    """Service for managing verification tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def create_email_token(self, player_id: UUID) -> str:
        """Create a new email verification token.

        Returns the raw token (to be sent in email). The hashed version is stored.
        """
        # Invalidate any existing email tokens for this player
        await self._invalidate_tokens(player_id, TokenType.EMAIL)

        # Generate new token
        raw_token = _generate_email_token()
        hashed_token = _hash_token(raw_token)

        # Calculate expiry
        expires_at = datetime.now(UTC) + timedelta(hours=EMAIL_TOKEN_EXPIRY_HOURS)

        # Create token record
        token = VerificationToken(
            player_id=player_id,
            token_type=TokenType.EMAIL.value,
            token_value=hashed_token,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()

        return raw_token

    async def create_phone_code(self, player_id: UUID) -> str:
        """Create a new phone verification code.

        Returns the 6-digit code (to be sent via SMS). Stored as plain text.
        """
        # Invalidate any existing phone tokens for this player
        await self._invalidate_tokens(player_id, TokenType.PHONE)

        # Generate new code
        code = _generate_phone_code()

        # Calculate expiry
        expires_at = datetime.now(UTC) + timedelta(minutes=PHONE_CODE_EXPIRY_MINUTES)

        # Create token record
        token = VerificationToken(
            player_id=player_id,
            token_type=TokenType.PHONE.value,
            token_value=code,  # Store plain - 6-digit with short expiry is acceptable
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()

        return code

    async def verify_email_token(self, raw_token: str) -> UUID | None:
        """Verify an email token and return the player_id if valid.

        Returns None if token is invalid, expired, or already used.
        Consumes the token on success.
        """
        hashed_token = _hash_token(raw_token)
        now = datetime.now(UTC)

        # Find valid token
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.token_type == TokenType.EMAIL.value,
                VerificationToken.token_value == hashed_token,
                VerificationToken.used_at.is_(None),
                VerificationToken.expires_at > now,
            )
        )
        token = result.scalar_one_or_none()

        if token is None:
            return None

        # Mark as used
        token.used_at = now
        await self.db.flush()

        return token.player_id

    async def verify_phone_code(self, player_id: UUID, code: str) -> bool:
        """Verify a phone code for a specific player.

        Returns True if code is valid. Consumes the token on success.
        """
        now = datetime.now(UTC)

        # Find valid token for this player
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.player_id == player_id,
                VerificationToken.token_type == TokenType.PHONE.value,
                VerificationToken.token_value == code,
                VerificationToken.used_at.is_(None),
                VerificationToken.expires_at > now,
            )
        )
        token = result.scalar_one_or_none()

        if token is None:
            return False

        # Mark as used
        token.used_at = now
        await self.db.flush()

        return True

    async def can_resend_phone_code(self, player_id: UUID) -> tuple[bool, int]:
        """Check if player can request a new phone code.

        Returns (can_resend, seconds_until_allowed).
        Rate limited to one code per PHONE_RESEND_COOLDOWN_SECONDS.
        """
        now = datetime.now(UTC)
        cooldown_cutoff = now - timedelta(seconds=PHONE_RESEND_COOLDOWN_SECONDS)

        # Find most recent phone token for this player
        result = await self.db.execute(
            select(VerificationToken)
            .where(
                VerificationToken.player_id == player_id,
                VerificationToken.token_type == TokenType.PHONE.value,
            )
            .order_by(VerificationToken.created_at.desc())
            .limit(1)
        )
        token = result.scalar_one_or_none()

        if token is None:
            return True, 0

        if token.created_at > cooldown_cutoff:
            # Still in cooldown
            seconds_remaining = int(
                (token.created_at - cooldown_cutoff).total_seconds()
            )
            return False, seconds_remaining

        return True, 0

    async def get_active_tokens_count(
        self, player_id: UUID, token_type: TokenType
    ) -> int:
        """Get the count of active (unused, unexpired) tokens for a player."""
        now = datetime.now(UTC)

        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.player_id == player_id,
                VerificationToken.token_type == token_type.value,
                VerificationToken.used_at.is_(None),
                VerificationToken.expires_at > now,
            )
        )
        return len(result.scalars().all())

    async def _invalidate_tokens(
        self, player_id: UUID, token_type: TokenType
    ) -> int:
        """Invalidate all active tokens of a type for a player.

        Returns the number of tokens invalidated.
        """
        now = datetime.now(UTC)

        # Find all active tokens
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.player_id == player_id,
                VerificationToken.token_type == token_type.value,
                VerificationToken.used_at.is_(None),
            )
        )
        tokens = result.scalars().all()

        # Mark all as used
        for token in tokens:
            token.used_at = now

        await self.db.flush()
        return len(tokens)

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens from the database.

        This should be called periodically by a background job.
        Returns the number of tokens deleted.
        """
        now = datetime.now(UTC)

        # Find all expired or used tokens older than 24 hours
        cutoff = now - timedelta(hours=24)
        result = await self.db.execute(
            select(VerificationToken).where(
                (VerificationToken.expires_at < now)
                | (
                    VerificationToken.used_at.is_not(None)
                    & (VerificationToken.used_at < cutoff)
                )
            )
        )
        tokens = result.scalars().all()

        for token in tokens:
            await self.db.delete(token)

        await self.db.flush()
        return len(tokens)


def get_verification_service(db: AsyncSession = Depends(get_db)) -> VerificationService:
    """Dependency factory for VerificationService."""
    return VerificationService(db)
