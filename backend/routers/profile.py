"""
Profile settings, including the Telegram chat links that scope the bot.

A link binds one Telegram chat to one company. The bot then answers that chat
only about that company, so these endpoints are the control surface for who can
read which borrower's file over Telegram.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.company import Company
from models.telegram_link import TelegramLink
from services import telegram_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["Profile"])


def get_current_user_email(x_user_email: str = Header(None)) -> str:
    """Matches the convention already used by the drafts router."""
    return x_user_email or "admin@gmail.com"


class TelegramLinkCreate(BaseModel):
    chat_id: int = Field(..., description="Numeric Telegram chat ID, from /whoami")
    company_id: int
    label: str = Field("", max_length=120)


class TelegramLinkOut(BaseModel):
    id: int
    chat_id: int
    company_id: int
    company_name: str
    label: str
    is_active: bool


def _to_out(link: TelegramLink, company_name: str) -> TelegramLinkOut:
    return TelegramLinkOut(
        id=link.id,
        chat_id=link.chat_id,
        company_id=link.company_id,
        company_name=company_name,
        label=link.label or "",
        is_active=bool(link.is_active),
    )


@router.get("/telegram")
def list_telegram_links(db: Session = Depends(get_db)) -> dict:
    """Every chat link, plus the bot's configuration state."""
    rows = (
        db.query(TelegramLink, Company)
        .outerjoin(Company, TelegramLink.company_id == Company.id)
        .order_by(TelegramLink.id.desc())
        .all()
    )
    bot_username = None
    if telegram_service.is_configured():
        try:
            me = telegram_service.get_me()
            if me.get("ok"):
                bot_username = me["result"].get("username")
        except Exception as exc:  # noqa: BLE001
            # A dead token must not break the settings screen.
            logger.warning("Could not reach Telegram for getMe: %s", exc)

    return {
        "configured": telegram_service.is_configured(),
        "bot_username": bot_username,
        "operator_chat_count": len(telegram_service.allowed_chat_ids()),
        "links": [
            _to_out(link, company.company_name if company else "Unknown company").model_dump()
            for link, company in rows
        ],
    }


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)) -> dict:
    """Companies available to link, for the Profile dropdown."""
    rows = db.query(Company).order_by(Company.id.desc()).all()
    return {
        "companies": [
            {"id": c.id, "company_name": c.company_name, "cin_number": c.cin_number}
            for c in rows
        ]
    }


@router.post("/telegram", status_code=201)
def create_telegram_link(
    payload: TelegramLinkCreate,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email),
) -> dict:
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    existing = (
        db.query(TelegramLink).filter(TelegramLink.chat_id == payload.chat_id).first()
    )
    if existing:
        # One chat maps to one company. Re-pointing is an explicit update rather
        # than a second row, so a chat can never resolve to two companies.
        existing.company_id = payload.company_id
        existing.label = payload.label or existing.label
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return {
            "status": "updated",
            "link": _to_out(existing, company.company_name).model_dump(),
        }

    link = TelegramLink(
        chat_id=payload.chat_id,
        company_id=payload.company_id,
        label=payload.label or None,
        is_active=True,
        created_by=email,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"status": "created", "link": _to_out(link, company.company_name).model_dump()}


@router.patch("/telegram/{link_id}")
def toggle_telegram_link(
    link_id: int, active: bool, db: Session = Depends(get_db)
) -> dict:
    link = db.query(TelegramLink).filter(TelegramLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")
    link.is_active = active
    db.commit()
    return {"status": "updated", "id": link_id, "is_active": active}


@router.delete("/telegram/{link_id}")
def delete_telegram_link(link_id: int, db: Session = Depends(get_db)) -> dict:
    link = db.query(TelegramLink).filter(TelegramLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")
    db.delete(link)
    db.commit()
    return {"status": "deleted", "id": link_id}


@router.post("/telegram/{link_id}/test")
def test_telegram_link(link_id: int, db: Session = Depends(get_db)) -> dict:
    """Sends a confirmation message, so the operator knows the ID is right."""
    link = db.query(TelegramLink).filter(TelegramLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")
    if not telegram_service.is_configured():
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN is not set.")

    company = db.query(Company).filter(Company.id == link.company_id).first()
    name = company.company_name if company else "your company"
    try:
        telegram_service.send_message(
            link.chat_id,
            f"CreditIQ: this chat is now linked to {name}. "
            "Send /help to see what you can ask.",
        )
    except Exception as exc:  # noqa: BLE001
        # Surface the reason: an unstarted chat is the usual cause and the
        # operator needs to know the contact must message the bot first.
        detail = f"{type(exc).__name__}"
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                detail = response.json().get("description", detail)
            except Exception:  # noqa: BLE001
                pass
        raise HTTPException(
            status_code=502,
            detail=(
                f"Telegram rejected the message: {detail}. "
                "The contact must send the bot a message first — a bot cannot "
                "start a conversation."
            ),
        )
    return {"status": "sent", "chat_id": link.chat_id}
