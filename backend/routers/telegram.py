"""
Telegram webhook endpoint.

Telegram pushes updates here when a webhook is registered. For local
development without a public HTTPS URL, run backend/telegram_bot.py instead,
which long-polls the same handler.
"""
import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from database import get_db
from services import telegram_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


@router.get("/health")
def telegram_health() -> dict:
    """Configuration state, without revealing the token."""
    return {
        "configured": telegram_service.is_configured(),
        "authorised_chats": len(telegram_service.allowed_chat_ids()),
        "webhook_secret_set": bool(os.getenv("TELEGRAM_WEBHOOK_SECRET")),
    }


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str = Header(None),
) -> dict:
    """
    Receives one update from Telegram.

    The URL is effectively public, so when TELEGRAM_WEBHOOK_SECRET is set the
    header Telegram sends must match it. Always set it in production.
    """
    if not telegram_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_BOT_TOKEN is not set on the server.",
        )

    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if secret and x_telegram_bot_api_secret_token != secret:
        logger.warning("Rejected Telegram webhook call with bad secret token")
        raise HTTPException(status_code=403, detail="Invalid webhook secret token.")

    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body is not valid JSON.")

    try:
        telegram_service.handle_update(update, db)
    except Exception:
        # Returning 200 regardless: a non-200 makes Telegram retry the same
        # update repeatedly, which would loop on a deterministic bug.
        logger.exception("Telegram update handling failed")

    return {"ok": True}
