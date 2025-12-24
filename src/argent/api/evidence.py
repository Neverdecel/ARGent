"""Evidence dashboard routes.

The in-fiction corporate portal where players access leaked documents
using their cryptic key. The URL IS the key: /access/<key>
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from argent.database import get_db
from argent.services import evidence

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evidence"])

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR), auto_reload=True)


@router.get("/access/{key}", response_class=HTMLResponse)
async def access_evidence(
    request: Request,
    key: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Access the evidence dashboard using a key.

    The key IS the URL - if you have the key, you have the URL.
    Players discover this through cryptic hints from agents.

    Args:
        request: FastAPI request
        key: The player's cryptic key (format: XXXX-XXXX-XXXX-XXXX)
        db: Database session

    Returns:
        Dashboard content if valid, access denied page otherwise
    """
    # Validate key exists
    player_key = await evidence.validate_key(db, key)

    if player_key is None:
        # Invalid key - log attempt and show error
        logger.warning("Invalid key access attempt: %s", key[:9] + "..." if len(key) > 9 else key)
        return templates.TemplateResponse(
            "evidence.html",
            {
                "request": request,
                "access_granted": False,
                "error_type": "invalid",
                "error_message": "ACCESS DENIED: Credential not recognized",
            },
            status_code=403,
        )

    # Check access limit
    if not await evidence.check_access_limit(player_key):
        # Limit exhausted - log and show error
        await evidence.log_access(db, player_key, success=False, request=request)
        await db.commit()

        logger.info("Key access limit exhausted: %s", key[:9] + "...")
        return templates.TemplateResponse(
            "evidence.html",
            {
                "request": request,
                "access_granted": False,
                "error_type": "exhausted",
                "error_message": "ACCESS DENIED: Credential expired",
            },
            status_code=403,
        )

    # Valid access - log, increment, record knowledge
    await evidence.log_access(db, player_key, success=True, request=request)
    await evidence.increment_access(db, player_key)
    await evidence.record_dashboard_knowledge(db, player_key.player_id)

    # Get remaining accesses for display
    remaining = await evidence.get_remaining_accesses(player_key)

    await db.commit()

    logger.info(
        "Dashboard access granted: player=%s remaining=%d",
        player_key.player_id,
        remaining,
    )

    # TODO: Emit key_used event for story triggers

    return templates.TemplateResponse(
        "evidence.html",
        {
            "request": request,
            "access_granted": True,
            "remaining_accesses": remaining,
            "first_access": player_key.access_count == 1,
        },
    )
