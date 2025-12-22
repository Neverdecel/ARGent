"""HTML page routes for onboarding flow."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argent.config import Settings, get_settings
from argent.database import get_db
from argent.models import Player

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pages"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR), auto_reload=True)


def _get_player_id_from_session(
    session_cookie: str | None,
    settings: Settings,
) -> str | None:
    """Extract player ID from session cookie.

    Returns the player ID string or None if invalid/missing.
    """
    if not session_cookie:
        return None
    try:
        from itsdangerous import URLSafeTimedSerializer

        serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")
        result: str = serializer.loads(session_cookie, max_age=60 * 60 * 24 * 7)
        return result
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    """Landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    email: str | None = None,
) -> HTMLResponse:
    """Registration page."""
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "prefill_email": email,
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    email: str | None = None,
) -> HTMLResponse:
    """Login page for returning players."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "prefill_email": email,
        },
    )


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(
    request: Request,
    error: str | None = None,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Verification status page."""
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if not player_id:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # Get player
    from uuid import UUID

    result = await db.execute(select(Player).where(Player.id == UUID(player_id)))
    player = result.scalar_one_or_none()
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # Map error codes to messages
    error_messages = {
        "invalid_email_token": "Invalid or expired verification link. Please request a new one.",
    }
    error_message = error_messages.get(error) if error else None

    return templates.TemplateResponse(
        "verify.html",
        {
            "request": request,
            "email": player.email,
            "phone": player.phone,
            "email_verified": player.email_verified,
            "phone_verified": player.phone_verified,
            "can_start_game": player.email_verified and player.phone_verified,
            "error": error_message,
        },
    )


@router.get("/verify/email/success", response_class=HTMLResponse)
async def verify_email_success_page(request: Request) -> HTMLResponse:
    """Email verification success page."""
    return templates.TemplateResponse("verify_email_success.html", {"request": request})


@router.get("/verify/phone", response_class=HTMLResponse)
async def verify_phone_page(
    request: Request,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Phone verification code entry page."""
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if not player_id:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # Get player
    from uuid import UUID

    result = await db.execute(select(Player).where(Player.id == UUID(player_id)))
    player = result.scalar_one_or_none()
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # If already verified, redirect to verify page
    if player.phone_verified:
        return RedirectResponse(url="/verify", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "verify_phone.html",
        {
            "request": request,
            "phone": player.phone,
        },
    )


@router.get("/start", response_class=HTMLResponse)
async def start_page(
    request: Request,
    argent_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Pre-game info and start button page."""
    # Get player from session
    player_id = _get_player_id_from_session(argent_session, settings)
    if not player_id:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # Get player
    from uuid import UUID

    result = await db.execute(select(Player).where(Player.id == UUID(player_id)))
    player = result.scalar_one_or_none()
    if not player:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    # Must have both verifications
    if not player.email_verified or not player.phone_verified:
        return RedirectResponse(url="/verify", status_code=status.HTTP_303_SEE_OTHER)

    # Check if web-only mode
    is_web_only = player.communication_mode == "web_only"

    # If game already started, show different message
    if player.game_started_at:
        return templates.TemplateResponse(
            "start.html",
            {
                "request": request,
                "game_already_started": True,
                "is_web_only": is_web_only,
            },
        )

    return templates.TemplateResponse(
        "start.html",
        {
            "request": request,
            "game_already_started": False,
            "is_web_only": is_web_only,
        },
    )
