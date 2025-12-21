"""Web inbox API endpoints and page routes.

Provides:
- Page routes for inbox UI (HTML)
- API endpoints for inbox operations (JSON)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.config import Settings, get_settings
from argent.database import get_db
from argent.models import Player
from argent.services.web_inbox import WebInboxService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["inbox"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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


# --- Page Routes ---


@router.get("/inbox", response_class=HTMLResponse)
async def inbox_page(
    request: Request,
    channel: str | None = None,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Main inbox page - shows conversation list."""
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

    # Get conversations
    inbox_service = _get_web_inbox_service(db)
    conversations = await inbox_service.get_conversations(player.id, channel_filter=channel)
    unread_count = await inbox_service.get_unread_count(player.id)

    return templates.TemplateResponse(
        "inbox.html",
        {
            "request": request,
            "conversations": conversations,
            "unread_count": unread_count,
            "player": player,
            "channel_filter": channel,
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
        except ValueError:
            raise HTTPException(status_code=404, detail="Invalid message ID")
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

    return templates.TemplateResponse(
        "conversation.html",
        {
            "request": request,
            "session_id": session_id,
            "title": title,
            "messages": messages,
            "player": player,
        },
    )


@router.get("/inbox/compose", response_class=HTMLResponse)
async def compose_page(
    request: Request,
    reply_to: str | None = None,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Compose new message page."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    if player.communication_mode != "web_only":
        return RedirectResponse(url="/start", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "compose.html",
        {
            "request": request,
            "reply_to_session": reply_to,
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


@router.post("/api/inbox/compose")
async def compose_message(
    request_body: ComposeRequest,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageDetail:
    """Compose and send a new message (queued for agent processing)."""
    if not settings.web_inbox_enabled:
        raise HTTPException(status_code=404, detail="Web inbox not enabled")

    player = await _get_current_player(argent_session, db, settings)
    if not player:
        raise HTTPException(status_code=401, detail="Not authenticated")

    inbox_service = _get_web_inbox_service(db)

    # Store the player's message
    message = await inbox_service.store_player_message(
        player_id=player.id,
        content=request_body.content,
        subject=request_body.subject,
        session_id=request_body.session_id,
    )
    await db.commit()

    # TODO: Queue background task for agent response
    # This will be handled by the story engine when implemented
    logger.info(
        "Player %s sent message in session %s - agent response pending",
        player.id,
        request_body.session_id,
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
