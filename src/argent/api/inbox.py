"""Web inbox API endpoints and page routes.

Provides:
- Page routes for inbox UI (HTML)
- API endpoints for inbox operations (JSON)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

if TYPE_CHECKING:
    from argent.agents.base import BaseAgent

import asyncio
import threading

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.config import Settings, get_settings
from argent.database import get_db
from argent.models import Player
from argent.models.player import Message, PlayerKnowledge, PlayerTrust
from argent.services.base import OutboundMessage
from argent.services.web_inbox import WebInboxService
from argent.story import load_character

logger = logging.getLogger(__name__)

router = APIRouter(tags=["inbox"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR), auto_reload=True)


# --- Pydantic Models ---


class MessageSummary(BaseModel):
    """Summary of a message for inbox list view."""

    model_config = {"from_attributes": True}

    id: UUID
    channel: str
    direction: str
    sender_name: str | None
    subject: str | None
    preview: str
    created_at: datetime
    read_at: datetime | None


class MessageDetail(BaseModel):
    """Full message content."""

    model_config = {"from_attributes": True}

    id: UUID
    channel: str
    direction: str
    sender_name: str | None
    subject: str | None
    content: str | None
    html_content: str | None
    created_at: datetime
    read_at: datetime | None
    session_id: str | None


class ConversationSummary(BaseModel):
    """Summary of a conversation thread."""

    session_id: str
    title: str
    message_count: int
    unread_count: int
    updated_at: datetime
    latest_preview: str


class ComposeRequest(BaseModel):
    """Request to compose a new message."""

    content: str
    subject: str | None = None
    session_id: str | None = None  # For replies
    agent_id: str | None = None  # For new messages (recipient)


class MarkReadRequest(BaseModel):
    """Request to mark message(s) as read."""

    message_id: UUID | None = None
    session_id: str | None = None  # Mark whole conversation


# --- Helper Functions ---


def _get_player_id_from_session(
    session_cookie: str | None,
    settings: Settings,
) -> str | None:
    """Extract player ID from session cookie."""
    if not session_cookie:
        return None
    try:
        from itsdangerous import URLSafeTimedSerializer

        serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")
        result: str = serializer.loads(session_cookie, max_age=60 * 60 * 24 * 7)
        return result
    except Exception:
        return None


async def _get_current_player(
    argent_session: str | None,
    db: AsyncSession,
    settings: Settings,
) -> Player | None:
    """Get current player from session cookie."""
    player_id = _get_player_id_from_session(argent_session, settings)
    if not player_id:
        return None

    result = await db.execute(select(Player).where(Player.id == UUID(player_id)))
    return result.scalar_one_or_none()


def _get_web_inbox_service(db: AsyncSession) -> WebInboxService:
    """Create WebInboxService instance."""
    return WebInboxService(db)


def _get_agent_avatar_url(agent_id: str | None) -> str | None:
    """Get the avatar URL for an agent."""
    if not agent_id:
        return None
    try:
        persona = load_character(agent_id)
        if persona.avatar:
            return f"/static/avatars/{persona.avatar}"
    except ValueError:
        pass
    return None


async def _get_session_agent_id(
    db: AsyncSession,
    player_id: UUID,
    session_id: str,
) -> str | None:
    """Determine which agent a conversation session belongs to.

    Looks at existing messages in the session to find the agent_id
    from outbound (agent) messages.
    """
    result = await db.execute(
        select(Message.agent_id)
        .where(Message.player_id == player_id)
        .where(Message.session_id == session_id)
        .where(Message.agent_id.isnot(None))
        .limit(1)
    )
    agent_id = result.scalar_one_or_none()
    return agent_id


async def _get_player_trust_score(
    db: AsyncSession,
    player_id: UUID,
    agent_id: str,
) -> int:
    """Get current trust score for a player with a specific agent."""
    result = await db.execute(
        select(PlayerTrust.trust_score)
        .where(PlayerTrust.player_id == player_id)
        .where(PlayerTrust.agent_id == agent_id)
    )
    score = result.scalar_one_or_none()
    return score or 0


async def _get_player_knowledge(
    db: AsyncSession,
    player_id: UUID,
) -> list[str]:
    """Get all facts the player has learned."""
    result = await db.execute(
        select(PlayerKnowledge.fact).where(PlayerKnowledge.player_id == player_id)
    )
    return [row[0] for row in result.all()]


async def _get_conversation_history(
    db: AsyncSession,
    player_id: UUID,
    session_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get recent conversation history for context.

    Returns messages in chronological order (oldest first).
    """
    result = await db.execute(
        select(Message)
        .where(Message.player_id == player_id)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())

    # Reverse to get chronological order
    messages.reverse()

    return [
        {
            "role": "user" if msg.direction == "inbound" else "assistant",
            "content": msg.content or "",
            "sender": msg.sender_name,
        }
        for msg in messages
    ]


# Agent instance cache (simple singleton pattern for MVP)
_agent_instances: dict = {}


def _get_agent(agent_id: str, settings: Settings) -> "BaseAgent | None":
    """Get or create an agent instance.

    Uses a simple cache to avoid recreating agents on every request.
    """
    if not settings.gemini_api_key:
        return None

    if agent_id not in _agent_instances:
        if agent_id == "ember":
            from argent.agents.ember import EmberAgent

            _agent_instances[agent_id] = EmberAgent(
                gemini_api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
        elif agent_id == "miro":
            from argent.agents.miro import MiroAgent

            _agent_instances[agent_id] = MiroAgent(
                gemini_api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )

    return _agent_instances.get(agent_id)


# --- Page Routes ---


@router.get("/hub", response_class=HTMLResponse)
async def hub_page(
    request: Request,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Hub page - choose between email and text channels."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    # Get unread counts for each channel
    inbox_service = _get_web_inbox_service(db)
    email_unread = await inbox_service.get_unread_count(player.id, channel_filter="email")
    sms_unread = await inbox_service.get_unread_count(player.id, channel_filter="sms")

    return templates.TemplateResponse(
        "hub.html",
        {
            "request": request,
            "player": player,
            "email_unread": email_unread,
            "sms_unread": sms_unread,
        },
    )


@router.get("/inbox", response_class=HTMLResponse)
async def inbox_page(
    request: Request,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Email inbox page - shows only email messages."""
    # Check if web inbox is enabled
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    # Get current player
    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # Only web_only mode players can access inbox
    if player.communication_mode != "web_only":
        # Redirect immersive mode players away
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    # Get email messages only
    inbox_service = _get_web_inbox_service(db)
    messages = await inbox_service.get_messages(player.id, channel_filter="email", limit=50)
    unread_count = await inbox_service.get_unread_count(player.id, channel_filter="email")

    # Add avatar URLs to messages
    messages_with_avatars = [
        {
            "id": msg.id,
            "channel": msg.channel,
            "direction": msg.direction,
            "sender_name": msg.sender_name,
            "subject": msg.subject,
            "content": msg.content,
            "created_at": msg.created_at,
            "read_at": msg.read_at,
            "session_id": msg.session_id,
            "avatar_url": _get_agent_avatar_url(msg.agent_id),
        }
        for msg in messages
    ]

    return templates.TemplateResponse(
        "inbox.html",
        {
            "request": request,
            "messages": messages_with_avatars,
            "unread_count": unread_count,
            "player": player,
        },
    )


@router.get("/text", response_class=HTMLResponse)
async def text_page(
    request: Request,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Text/SMS messages page - shows SMS conversations."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    # Get SMS conversations (grouped by session)
    inbox_service = _get_web_inbox_service(db)
    conversations = await inbox_service.get_conversations(player.id, channel_filter="sms")

    # Add avatar URLs to conversations
    conversations_with_avatars = []
    for conv in conversations:
        latest_msg = conv.get("latest_message")
        agent_id = latest_msg.agent_id if latest_msg else None
        conversations_with_avatars.append(
            {
                "session_id": conv["session_id"],
                "title": conv["title"],
                "message_count": conv["message_count"],
                "unread_count": conv["unread_count"],
                "updated_at": conv["updated_at"],
                "latest_preview": (latest_msg.content or "")[:80] if latest_msg else "",
                "avatar_url": _get_agent_avatar_url(agent_id),
            }
        )

    return templates.TemplateResponse(
        "text.html",
        {
            "request": request,
            "conversations": conversations_with_avatars,
            "player": player,
        },
    )


@router.get("/text/thread/{session_id}", response_class=HTMLResponse)
async def text_thread_page(
    request: Request,
    session_id: str,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """SMS conversation thread view - chat-style interface."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    inbox_service = _get_web_inbox_service(db)
    messages = await inbox_service.get_conversation_messages(player.id, session_id)

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Mark conversation as read
    await inbox_service.mark_conversation_read(player.id, session_id)
    await db.commit()

    # Determine conversation title from participants
    participants = {m.sender_name for m in messages if m.sender_name and m.sender_name != "You"}
    title = ", ".join(sorted(participants)) if participants else "Text Message"

    # Get avatar for the contact
    agent_id = next((m.agent_id for m in messages if m.agent_id), None)
    avatar_url = _get_agent_avatar_url(agent_id)

    # Messages in chronological order (oldest first for chat view)
    messages_data = [
        {
            "id": msg.id,
            "direction": msg.direction,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "created_at": msg.created_at,
        }
        for msg in messages
    ]

    return templates.TemplateResponse(
        "text_thread.html",
        {
            "request": request,
            "session_id": session_id,
            "title": title,
            "messages": messages_data,
            "player": player,
            "avatar_url": avatar_url,
        },
    )


@router.get("/inbox/conversation/{session_id}", response_class=HTMLResponse)
async def conversation_page(
    request: Request,
    session_id: str,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Conversation thread view - shows all messages in a conversation."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    inbox_service = _get_web_inbox_service(db)

    # Handle single messages (no session_id) - format: "single-{message_uuid}"
    if session_id.startswith("single-"):
        message_id_str = session_id[7:]  # Remove "single-" prefix
        try:
            message_id = UUID(message_id_str)
            message = await inbox_service.get_message(player.id, message_id)
            if not message:
                raise HTTPException(status_code=404, detail="Message not found")
            messages = [message]
            # Mark as read
            await inbox_service.mark_read(player.id, message_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="Invalid message ID") from err
    else:
        # Get messages in conversation
        messages = await inbox_service.get_conversation_messages(player.id, session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Mark conversation as read
        await inbox_service.mark_conversation_read(player.id, session_id)

    await db.commit()

    # Determine conversation title from participants
    participants = {m.sender_name for m in messages if m.sender_name and m.sender_name != "You"}
    title = ", ".join(sorted(participants)) if participants else "Conversation"

    # Add avatar URLs to messages
    messages_with_avatars = [
        {
            "id": msg.id,
            "channel": msg.channel,
            "direction": msg.direction,
            "sender_name": msg.sender_name,
            "subject": msg.subject,
            "content": msg.content,
            "html_content": msg.html_content,
            "created_at": msg.created_at,
            "read_at": msg.read_at,
            "session_id": msg.session_id,
            "avatar_url": _get_agent_avatar_url(msg.agent_id),
        }
        for msg in messages
    ]

    return templates.TemplateResponse(
        "conversation.html",
        {
            "request": request,
            "session_id": session_id,
            "title": title,
            "messages": messages_with_avatars,
            "player": player,
        },
    )


def _get_available_contacts() -> list[dict]:
    """Get list of agents the player can contact."""
    return [
        {"id": "ember", "name": "Ember Vance", "channel": "email"},
        {"id": "miro", "name": "Miro", "channel": "sms"},
    ]


@router.get("/inbox/compose", response_class=HTMLResponse)
async def compose_page(
    request: Request,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Compose new email page."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    # Get available contacts (agents player can email)
    contacts = _get_available_contacts()

    return templates.TemplateResponse(
        "compose.html",
        {
            "request": request,
            "player": player,
            "contacts": contacts,
        },
    )


@router.get("/inbox/thread/{message_id}", response_class=HTMLResponse)
async def thread_page(
    request: Request,
    message_id: UUID,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Gmail-style thread view - shows all messages in thread with clicked one expanded."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    inbox_service = _get_web_inbox_service(db)

    # Get the clicked message
    message = await inbox_service.get_message(player.id, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Get all messages in the same thread (session_id)
    if message.session_id:
        messages = await inbox_service.get_conversation_messages(player.id, message.session_id)
    else:
        # Single message, no thread
        messages = [message]

    # Mark the clicked message as read
    await inbox_service.mark_read(player.id, message_id)
    await db.commit()

    # Determine thread subject from first message with subject
    thread_subject = None
    for msg in messages:
        if msg.subject:
            thread_subject = msg.subject
            break

    # Determine conversation title from participants
    participants = {m.sender_name for m in messages if m.sender_name and m.sender_name != "You"}
    title = ", ".join(sorted(participants)) if participants else "Conversation"

    # Add avatar URLs and mark which message is focused
    # Reverse order: newest messages first
    messages_with_avatars = [
        {
            "id": msg.id,
            "channel": msg.channel,
            "direction": msg.direction,
            "sender_name": msg.sender_name,
            "subject": msg.subject,
            "content": msg.content,
            "html_content": msg.html_content,
            "created_at": msg.created_at,
            "read_at": msg.read_at,
            "session_id": msg.session_id,
            "avatar_url": _get_agent_avatar_url(msg.agent_id),
        }
        for msg in reversed(messages)
    ]

    return templates.TemplateResponse(
        "thread.html",
        {
            "request": request,
            "session_id": message.session_id or f"single-{message_id}",
            "title": title,
            "thread_subject": thread_subject,
            "messages": messages_with_avatars,
            "focused_message_id": message_id,
            "player": player,
        },
    )


# --- API Routes ---


@router.get("/api/inbox/conversations")
async def list_conversations(
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = 20,
) -> list[ConversationSummary]:
    """List conversation summaries for inbox."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)
    conversations = await inbox_service.get_conversations(player.id, limit=limit)

    return [
        ConversationSummary(
            session_id=str(conv["session_id"]),
            title=conv["title"],
            message_count=conv["message_count"],
            unread_count=conv["unread_count"],
            updated_at=conv["updated_at"],
            latest_preview=(conv["latest_message"].content or "")[:100],
        )
        for conv in conversations
    ]


@router.get("/api/inbox/conversations/{session_id}/messages")
async def get_conversation_messages(
    session_id: str,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[MessageDetail]:
    """Get all messages in a conversation."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)
    messages = await inbox_service.get_conversation_messages(player.id, session_id)

    return [
        MessageDetail(
            id=msg.id,
            channel=msg.channel,
            direction=msg.direction,
            sender_name=msg.sender_name,
            subject=msg.subject,
            content=msg.content,
            html_content=msg.html_content,
            created_at=msg.created_at,
            read_at=msg.read_at,
            session_id=msg.session_id,
        )
        for msg in messages
    ]


@router.get("/api/inbox/messages/{message_id}")
async def get_message(
    message_id: UUID,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageDetail:
    """Get a single message by ID."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)
    message = await inbox_service.get_message(player.id, message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return MessageDetail(
        id=message.id,
        channel=message.channel,
        direction=message.direction,
        sender_name=message.sender_name,
        subject=message.subject,
        content=message.content,
        html_content=message.html_content,
        created_at=message.created_at,
        read_at=message.read_at,
        session_id=message.session_id,
    )


@router.post("/api/inbox/messages/{message_id}/read")
async def mark_message_read(
    message_id: UUID,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    """Mark a message as read."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)
    success = await inbox_service.mark_read(player.id, message_id)
    await db.commit()

    return {"success": success}


def _run_agent_response_in_thread(
    player_id: UUID,
    session_id: str,
    agent_id: str,
    player_message: str,
    settings: Settings,
) -> None:
    """Run agent response generation in a separate thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _generate_agent_response_background(
                player_id, session_id, agent_id, player_message, settings
            )
        )
    finally:
        loop.close()


async def _generate_agent_response_background(
    player_id: UUID,
    session_id: str,
    agent_id: str,
    player_message: str,
    settings: Settings,
) -> None:
    """Background task to generate agent response.

    Creates its own database engine and session since we're running in
    a separate thread with its own event loop.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    # Create a fresh engine for this event loop
    bg_engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    bg_session_maker = async_sessionmaker(
        bg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with bg_session_maker() as db:
            agent = _get_agent(agent_id, settings)
            if not agent:
                logger.warning(
                    "No agent available for %s (API key may be missing)",
                    agent_id,
                )
                return

            from argent.agents.base import AgentContext

            # Build agent context
            trust_score = await _get_player_trust_score(db, player_id, agent_id)
            player_knowledge_facts = await _get_player_knowledge(db, player_id)
            history = await _get_conversation_history(db, player_id, session_id)

            context = AgentContext(
                player_id=player_id,
                session_id=session_id,
                player_message=player_message,
                conversation_history=history,
                player_trust_score=trust_score,
                player_knowledge=player_knowledge_facts,
            )

            # Generate response
            response = await agent.generate_response(context)

            # Store agent response
            inbox_service = _get_web_inbox_service(db)
            outbound_message = await inbox_service.send_and_store(
                OutboundMessage(
                    player_id=player_id,
                    recipient="",  # Not used for web inbox
                    content=response.content,
                    agent_id=agent_id,
                    subject=response.subject,
                    session_id=session_id,
                ),
                display_channel="email" if agent_id == "ember" else "sms",
            )

            # Extract trust and knowledge from the exchange
            from argent.services import classification, trust
            from argent.services import knowledge as knowledge_service

            extraction = await classification.extract_from_exchange(
                player_message=player_message,
                agent_response=response.content,
                agent_id=agent_id,
                conversation_context=history,
            )

            # Update trust score if there was a change
            if extraction.trust_delta != 0:
                await trust.update_trust(
                    db=db,
                    player_id=player_id,
                    agent_id=agent_id,
                    delta=extraction.trust_delta,
                    reason=extraction.trust_reason,
                    message_id=outbound_message.id if outbound_message else None,
                )

            # Store extracted knowledge
            if extraction.knowledge_items:
                await knowledge_service.add_knowledge(
                    db=db,
                    player_id=player_id,
                    facts=extraction.knowledge_items,
                    source_agent=agent_id,
                    message_id=outbound_message.id if outbound_message else None,
                )

            # Store classification on the message
            if outbound_message:
                outbound_message.classification = {
                    "trust_delta": extraction.trust_delta,
                    "trust_reason": extraction.trust_reason,
                    "knowledge": extraction.knowledge_items,
                    "player_intent": extraction.player_intent,
                    "confidence": extraction.confidence,
                }
                from datetime import UTC, datetime

                outbound_message.classified_at = datetime.now(UTC)

            await db.commit()

            logger.info(
                "Agent %s responded to player %s in session %s (trust_delta=%+d)",
                agent_id,
                player_id,
                session_id,
                extraction.trust_delta,
            )

    except Exception as e:
        logger.error(
            "Failed to generate agent response: %s",
            str(e),
            exc_info=True,
        )
    finally:
        # Clean up the background engine
        await bg_engine.dispose()


@router.post("/api/inbox/compose")
async def compose_message(
    request_body: ComposeRequest,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageDetail:
    """Compose and send a new message. Agent response is generated in background."""
    from uuid import uuid4

    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)

    # If no session_id but agent_id provided, this is a NEW conversation
    session_id = request_body.session_id
    agent_id = request_body.agent_id

    if not session_id and agent_id:
        # Create new session_id for new conversation
        session_id = f"{agent_id}-{uuid4()}"
        logger.info(
            "Creating new conversation session %s with agent %s",
            session_id,
            agent_id,
        )

    # Store the player's message
    message = await inbox_service.store_player_message(
        player_id=player.id,
        content=request_body.content,
        subject=request_body.subject,
        session_id=session_id,
    )

    # Commit player message immediately so it's visible
    await db.commit()

    # Schedule agent response generation in background using asyncio.create_task
    # This runs truly in the background without blocking the response
    if settings.agent_response_enabled and session_id:
        # For replies, look up the agent from existing messages
        if not agent_id:
            agent_id = await _get_session_agent_id(db, player.id, session_id)

        if agent_id:
            # Run in separate thread to truly decouple from request
            thread = threading.Thread(
                target=_run_agent_response_in_thread,
                args=(player.id, session_id, agent_id, request_body.content, settings),
                daemon=True,
            )
            thread.start()
            logger.info(
                "Started background thread for agent response in session %s",
                session_id,
            )
        else:
            logger.debug(
                "No agent found for session %s - skipping response",
                session_id,
            )

    return MessageDetail(
        id=message.id,
        channel=message.channel,
        direction=message.direction,
        sender_name=message.sender_name,
        subject=message.subject,
        content=message.content,
        html_content=message.html_content,
        created_at=message.created_at,
        read_at=message.read_at,
        session_id=message.session_id,
    )


@router.get("/api/inbox/unread-count")
async def get_unread_count(
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    """Get count of unread messages."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)
    count = await inbox_service.get_unread_count(player.id)

    return {"unread_count": count}
