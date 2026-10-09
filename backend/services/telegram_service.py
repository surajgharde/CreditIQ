"""
Telegram bot for CreditIQ.

Serves analysis status and decision summaries, and relays free-text questions
to the multilingual assistant. The bot token is read from the environment only.

Access control is two-tier and default-deny:

  * A chat linked to a company (telegram_links, managed from the Profile page)
    is answered ONLY about that company. A borrower contact can never see
    another borrower's file.
  * A chat ID listed in TELEGRAM_ALLOWED_CHAT_IDS is an operator chat and sees
    every company.

A chat that is neither is served no data at all.
"""
import os
import logging
from typing import Optional

import requests
from sqlalchemy.orm import Session

from models.analysis import Analysis
from models.company import Company
from models.fraud import FraudSignal
from models.telegram_link import TelegramLink

logger = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
REQUEST_TIMEOUT = 20


def bot_token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()


def is_configured() -> bool:
    return bool(bot_token())


def allowed_chat_ids() -> set:
    """Operator chat IDs, from the environment. These see every company."""
    raw = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
    ids = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            logger.warning("Ignoring non-numeric TELEGRAM_ALLOWED_CHAT_IDS entry: %r", part)
    return ids


def _api(method: str, payload: dict) -> dict:
    token = bot_token()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Add it to backend/.env (see .env.example)."
        )
    response = requests.post(
        f"{API_ROOT}/bot{token}/{method}", json=payload, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def send_message(chat_id: int, text: str, parse_mode: Optional[str] = None) -> dict:
    """Sends a message. Telegram caps a single message at 4096 characters."""
    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return _api("sendMessage", payload)


def get_me() -> dict:
    token = bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    r = requests.get(f"{API_ROOT}/bot{token}/getMe", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _money(value) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "not set"
    if num >= 1_00_00_000:
        return f"Rs. {num / 1_00_00_000:.2f} Cr"
    if num >= 1_00_000:
        return f"Rs. {num / 1_00_000:.2f} Lakh"
    return f"Rs. {num:,.0f}"


def _pct(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "not set"


DECISION_ICON = {
    "APPROVE": "[APPROVED]",
    "REJECT": "[REJECTED]",
    "CONDITIONAL": "[CONDITIONAL]",
}


# ---------------------------------------------------------------------------
# Scope resolution
# ---------------------------------------------------------------------------

OPERATOR = "operator"
COMPANY = "company"
DENIED = "denied"


def resolve_scope(db: Session, chat_id: int) -> tuple:
    """
    Decides what a chat may see. Returns (kind, company_id).

    Operator chats come from TELEGRAM_ALLOWED_CHAT_IDS and are unscoped.
    Everyone else needs an active telegram_links row and is then confined to
    that one company. Unknown chats get nothing.
    """
    if chat_id in allowed_chat_ids():
        return OPERATOR, None

    link = (
        db.query(TelegramLink)
        .filter(TelegramLink.chat_id == chat_id, TelegramLink.is_active.is_(True))
        .first()
    )
    if link:
        return COMPANY, link.company_id
    return DENIED, None


def _company_name(db: Session, company_id) -> str:
    company = db.query(Company).filter(Company.id == company_id).first()
    return company.company_name if company else "Unknown borrower"


# ---------------------------------------------------------------------------
# Command handlers
#
# Every handler takes company_id. When it is not None the query is filtered to
# that company, so a scoped chat cannot read another borrower's analysis even
# by guessing an id.
# ---------------------------------------------------------------------------

def _cmd_list(db: Session, company_id=None) -> str:
    query = db.query(Analysis, Company).join(Company, Analysis.company_id == Company.id)
    if company_id is not None:
        query = query.filter(Analysis.company_id == company_id)
    rows = query.order_by(Analysis.id.desc()).limit(10).all()

    if not rows:
        if company_id is not None:
            return f"No analyses on record yet for {_company_name(db, company_id)}."
        return "No analyses on record yet."

    if company_id is not None:
        lines = [f"Analyses for {_company_name(db, company_id)}:"]
    else:
        lines = ["Recent analyses:"]

    for analysis, company in rows:
        decision = (analysis.decision or analysis.analysis_status or "pending").upper()
        if company_id is not None:
            lines.append(f"#{analysis.id} - {decision}")
        else:
            lines.append(f"#{analysis.id} - {company.company_name} - {decision}")

    lines.append("\nUse /decision <id> for detail.")
    return "\n".join(lines)


def _scoped_analysis(db: Session, analysis_id: int, company_id):
    """Looks up an analysis inside the caller's scope, or returns None."""
    query = db.query(Analysis).filter(Analysis.id == analysis_id)
    if company_id is not None:
        query = query.filter(Analysis.company_id == company_id)
    return query.first()


def _cmd_status(db: Session, arg: str, company_id=None) -> str:
    if not arg.isdigit():
        return "Usage: /status <analysis id>. Use /list to see available ids."
    analysis = _scoped_analysis(db, int(arg), company_id)
    if not analysis:
        # Deliberately worded the same whether the id does not exist or belongs
        # to another company — a different message would confirm it exists.
        return f"No analysis #{arg} available to you."

    lines = [
        f"Analysis #{analysis.id} - {_company_name(db, analysis.company_id)}",
        f"Status: {(analysis.analysis_status or 'unknown').upper()}",
        f"Progress: {float(analysis.progress or 0):.0f}%",
        f"Data quality: {_pct(analysis.data_quality_score)}",
    ]
    if analysis.failure_reason:
        lines.append(f"Failure: {analysis.failure_reason[:300]}")
    if analysis.cam_pdf_path or analysis.cam_document_path:
        lines.append("CAM: generated")
    # A zero data-quality score means nothing was extracted, so any decision on
    # this record rests on fallback constants rather than real financials.
    if (analysis.data_quality_score or 0) <= 0 and analysis.decision:
        lines.append(
            "\nWarning: no financial data was extracted for this analysis, so the "
            "decision is not based on real statements. Re-run it."
        )
    return "\n".join(lines)


def _cmd_decision(db: Session, arg: str, company_id=None) -> str:
    if not arg.isdigit():
        return "Usage: /decision <analysis id>. Use /list to see available ids."
    analysis = _scoped_analysis(db, int(arg), company_id)
    if not analysis:
        return f"No analysis #{arg} available to you."
    if not analysis.decision:
        return (
            f"Analysis #{analysis.id} has no decision yet "
            f"(status: {(analysis.analysis_status or 'unknown').upper()}). "
            f"Try /status {analysis.id}."
        )

    company = db.query(Company).filter(Company.id == analysis.company_id).first()
    name = company.company_name if company else "Unknown borrower"
    decision = (analysis.decision or "PENDING").upper()

    lines = [
        f"{DECISION_ICON.get(decision, '[' + decision + ']')} Analysis #{analysis.id}",
        f"Borrower: {name}",
        "",
        f"Probability of default: {_pct(analysis.probability_of_default)}",
        f"Facility requested: {_money(company.loan_amount_requested) if company else 'not set'}",
        f"Facility recommended: {_money(analysis.recommended_loan_amount)}",
        f"Indicative rate: {_pct(analysis.recommended_interest_rate)}",
        "",
        f"Fraud risk: {(analysis.fraud_risk_level or 'not assessed').upper()}",
        f"News risk score: {_pct(analysis.news_risk_score)}",
        f"Data quality: {_pct(analysis.data_quality_score)}",
    ]

    signals = (
        db.query(FraudSignal)
        .filter(FraudSignal.analysis_id == analysis.id)
        .limit(5)
        .all()
    )
    if signals:
        lines.append("\nFraud signals:")
        for sig in signals:
            amount = f" - {_money(sig.evidence_amount)}" if sig.evidence_amount else ""
            lines.append(f"- {sig.signal_type or 'signal'} ({sig.risk_level or '-'}){amount}")

    if (analysis.data_quality_score or 0) <= 0:
        lines.append(
            "\nWarning: no financial data was extracted for this analysis. The figures "
            "above rest on fallback constants, not real statements."
        )

    lines.append("\nPrototype output. Not a credit sanction.")
    return "\n".join(lines)


def _cmd_latest(db: Session, company_id) -> str:
    """Most recent analysis for a linked chat, so no id has to be known."""
    analysis = (
        db.query(Analysis)
        .filter(Analysis.company_id == company_id)
        .order_by(Analysis.id.desc())
        .first()
    )
    if not analysis:
        return f"No analyses on record yet for {_company_name(db, company_id)}."
    if analysis.decision:
        return _cmd_decision(db, str(analysis.id), company_id)
    return _cmd_status(db, str(analysis.id), company_id)


def _cmd_ask(question: str, company_name: Optional[str] = None) -> str:
    """Relays to the same assistant logic the web chat panel uses."""
    if not question.strip():
        return "Usage: /ask <question>. Example: /ask how is the PD calculated?"

    message = question.strip()
    if company_name:
        # Keep the assistant on this borrower's file. Note this steers the model
        # but is not itself an access control — the data commands above are
        # filtered in SQL, which is what actually confines a linked chat.
        message = (
            f"{message}\n\n(Context: the person asking is associated with "
            f"{company_name} and may only be told about that company. Do not "
            f"discuss any other borrower.)"
        )

    try:
        from routers.chat import ChatRequest, chat as chat_endpoint

        result = chat_endpoint(ChatRequest(message=message, lang="auto"))
        return result.reply
    except Exception as exc:  # noqa: BLE001
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            return f"Assistant unavailable: {exc.detail}"
        logger.exception("Telegram /ask failed")
        return f"Assistant unavailable: {type(exc).__name__}"


def _help_text(kind: str, company_name: Optional[str]) -> str:
    if kind == COMPANY:
        return (
            f"CreditIQ assistant - {company_name}\n\n"
            "/latest - your most recent assessment\n"
            "/list - your analyses\n"
            "/status <id> - pipeline progress\n"
            "/decision <id> - decision summary\n"
            "/ask <question> - ask about risk, fraud or your report\n"
            "/whoami - show your chat ID\n"
            "/help - this message\n\n"
            f"This chat is linked to {company_name} and shows only that company's "
            "information.\n\n"
            "Decisions shown here are produced by a prototype system and are not "
            "credit sanctions."
        )
    return (
        "CreditIQ assistant (operator)\n\n"
        "/list - most recent analyses across all borrowers\n"
        "/status <id> - pipeline progress for one analysis\n"
        "/decision <id> - decision summary with risk detail\n"
        "/ask <question> - ask about risk, fraud or CAM wording\n"
        "/whoami - show your chat ID\n"
        "/help - this message\n\n"
        "Decisions shown here are produced by a prototype system and are not credit "
        "sanctions."
    )


def handle_update(update: dict, db: Session) -> Optional[str]:
    """
    Processes one Telegram update and sends the reply.
    Returns the reply text (for logging and tests), or None when nothing was sent.
    """
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None or not text:
        return None

    parts = text.split(maxsplit=1)
    command = parts[0].split("@")[0].lower()  # strip @botname in group chats
    argument = parts[1] if len(parts) > 1 else ""

    # /whoami works for anyone so a new contact can report their own id to the
    # operator. It reveals nothing about any borrower.
    if command == "/whoami":
        reply = (
            f"Your chat ID is {chat_id}.\n\n"
            "Send it to your CreditIQ contact to have this chat linked to your "
            "company."
        )
        send_message(chat_id, reply)
        return reply

    kind, company_id = resolve_scope(db, chat_id)

    if kind == DENIED:
        logger.warning("Telegram request from unlinked chat %s", chat_id)
        reply = (
            "This chat is not linked to a company, so no information can be "
            "shared.\n\nSend /whoami and give that ID to your CreditIQ contact "
            "to get access."
        )
        send_message(chat_id, reply)
        return reply

    company_name = _company_name(db, company_id) if kind == COMPANY else None

    if command in ("/start", "/help"):
        reply = _help_text(kind, company_name)
    elif command == "/list":
        reply = _cmd_list(db, company_id)
    elif command == "/latest":
        if kind == COMPANY:
            reply = _cmd_latest(db, company_id)
        else:
            reply = "/latest is for company-linked chats. Use /list instead."
    elif command == "/status":
        reply = _cmd_status(db, argument.strip(), company_id)
    elif command == "/decision":
        reply = _cmd_decision(db, argument.strip(), company_id)
    elif command == "/ask":
        reply = _cmd_ask(argument, company_name)
    elif command.startswith("/"):
        reply = f"Unknown command {command}.\n\n{_help_text(kind, company_name)}"
    else:
        # Plain text is treated as a question.
        reply = _cmd_ask(text, company_name)

    send_message(chat_id, reply)
    return reply


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def broadcast_alert(text: str, db: Session = None, company_id=None) -> int:
    """
    Pushes an alert and returns the number delivered.

    With company_id and a session, it reaches that company's linked chats plus
    the operator chats. Without them, operator chats only. Safe to call when
    unconfigured.
    """
    if not is_configured():
        logger.info("Telegram alert skipped: TELEGRAM_BOT_TOKEN not set")
        return 0

    targets = set(allowed_chat_ids())
    if db is not None and company_id is not None:
        links = (
            db.query(TelegramLink)
            .filter(
                TelegramLink.company_id == company_id,
                TelegramLink.is_active.is_(True),
            )
            .all()
        )
        targets.update(link.chat_id for link in links)

    delivered = 0
    for chat_id in targets:
        try:
            send_message(chat_id, text)
            delivered += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram alert to %s failed: %s", chat_id, exc)
    return delivered
