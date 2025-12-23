"""Event handler implementations for story events."""

import importlib
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from argent.config import get_settings
from argent.database import async_session_maker
from argent.models.player import Player, PlayerKey
from argent.services.base import OutboundMessage
from argent.services.web_inbox import WebInboxService

logger = logging.getLogger(__name__)


async def execute_handler(
    handler_path: str,
    player_id: UUID,
    context: dict[str, Any],
) -> None:
    """Execute a handler by its dotted path."""
    module_path, func_name = handler_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    handler: Callable = getattr(module, func_name)

    await handler(player_id, context)


async def send_ember_first_contact(
    player_id: UUID,
    context: dict[str, Any],
) -> None:
    """Send Ember's first contact email with the key.

    Context should contain:
        - key: The player's key value
    """
    settings = get_settings()
    key = context.get("key", "")

    if not key:
        # Try to fetch key from database
        async with async_session_maker() as db:
            key_result = await db.execute(
                select(PlayerKey.key_value).where(PlayerKey.player_id == player_id)
            )
            key = key_result.scalar_one_or_none() or ""

    if not key:
        logger.error("No key found for player %s, cannot send Ember first contact", player_id)
        return

    async with async_session_maker() as db:
        # Get player
        player_result = await db.execute(select(Player).where(Player.id == player_id))
        player = player_result.scalar_one_or_none()
        if not player:
            logger.error("Player not found: %s", player_id)
            return

        if player.communication_mode == "web_only":
            await _send_key_to_web_inbox(db, player_id, key, settings)
        else:
            await _send_key_via_email(player.email, key, settings)

        await db.commit()


async def send_miro_first_contact(
    player_id: UUID,
    context: dict[str, Any],
) -> None:
    """Send Miro's first contact SMS."""
    settings = get_settings()

    async with async_session_maker() as db:
        # Get player
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one_or_none()
        if not player:
            logger.error("Player not found: %s", player_id)
            return

        if player.communication_mode == "web_only":
            await _send_miro_to_web_inbox(db, player_id, settings)
        else:
            await _send_miro_via_sms(player.phone, settings)

        await db.commit()


# Private helper functions


async def _send_key_to_web_inbox(
    db: Any,
    player_id: UUID,
    key: str,
    settings: Any,
) -> None:
    """Store 'The Key' message in web inbox for web-only players."""
    web_inbox_service = WebInboxService(db)
    session_id = f"ember-{uuid4()}"

    content: str
    subject: str

    if settings.gemini_api_key and settings.agent_response_enabled:
        try:
            from argent.agents.ember import EmberAgent

            agent = EmberAgent(
                gemini_api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
            response = await agent.generate_first_contact(key)
            content = response.content
            subject = response.subject or "You have a new message"

            logger.info("Generated Ember first contact via agent for player %s", player_id)

        except Exception as e:
            logger.warning("Failed to generate agent message, using fallback: %s", str(e))
            content, subject = _get_fallback_key_message(key)
    else:
        content, subject = _get_fallback_key_message(key)

    message = OutboundMessage(
        player_id=player_id,
        recipient="web-inbox",
        content=content,
        agent_id="ember",
        subject=subject,
        session_id=session_id,
    )

    await web_inbox_service.send_message(message)


async def _send_key_via_email(
    to_email: str,
    key: str,
    settings: Any,
) -> bool:
    """Send 'The Key' email that starts the ARG."""
    from argent.services.email import EmailService

    if not settings.email_enabled:
        logger.info("Email disabled - skipping The Key email")
        return True

    email_service = EmailService()

    subject = "You have a new message"
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
        from_email="unknown@noreply.localhost",
    )
    return result.success


def _get_fallback_key_message(key: str) -> tuple[str, str]:
    """Get the fallback hardcoded key message if agent is unavailable."""
    subject = "It's done"
    content = f"""Here's the access.

{key}

Use before Thursday. You know what to do.

Be careful.

- E
"""
    return content, subject


async def _send_miro_to_web_inbox(
    db: Any,
    player_id: UUID,
    settings: Any,
) -> None:
    """Store Miro message in web inbox."""
    web_inbox_service = WebInboxService(db)
    session_id = f"miro-{uuid4()}"

    content: str

    if settings.gemini_api_key and settings.agent_response_enabled:
        try:
            from argent.agents.miro import MiroAgent

            agent = MiroAgent(
                gemini_api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
            response = await agent.generate_first_contact()
            content = response.content
            logger.info("Generated Miro first contact for player %s", player_id)

        except Exception as e:
            logger.warning("Failed to generate Miro message: %s", str(e))
            content = _get_miro_fallback_message()
    else:
        content = _get_miro_fallback_message()

    message = OutboundMessage(
        player_id=player_id,
        recipient="web-inbox",
        content=content,
        agent_id="miro",
        subject=None,
        session_id=session_id,
    )

    await web_inbox_service.send_and_store(message, display_channel="sms")


async def _send_miro_via_sms(
    to_phone: str | None,
    settings: Any,
) -> bool:
    """Send Miro message via real SMS."""
    from argent.services.sms import SMSService

    if not settings.sms_enabled or not to_phone:
        logger.info("SMS disabled or no phone - skipping Miro SMS")
        return False

    sms_service = SMSService()

    content: str

    if settings.gemini_api_key and settings.agent_response_enabled:
        try:
            from argent.agents.miro import MiroAgent

            agent = MiroAgent(
                gemini_api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
            response = await agent.generate_first_contact()
            content = response.content
            logger.info("Generated Miro first contact via SMS")

        except Exception as e:
            logger.warning("Failed to generate Miro message: %s", str(e))
            content = _get_miro_fallback_message()
    else:
        content = _get_miro_fallback_message()

    result = await sms_service.send_sms(
        to_number=to_phone,
        body=content,
    )
    return result.success


def _get_miro_fallback_message() -> str:
    """Get the fallback Miro message if agent is unavailable."""
    return """hey.

heard you received something interesting recently. not sure if you know what you're holding, but I might be able to help you figure that out.

no pressure. just thought you should know you have options."""
