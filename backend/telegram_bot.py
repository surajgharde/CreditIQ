"""
Telegram long-polling runner for local development.

Telegram webhooks need a public HTTPS URL, which a laptop does not have. This
script polls getUpdates instead and feeds each update to the same handler the
webhook endpoint uses, so behaviour is identical either way.

    cd backend
    python telegram_bot.py

Stop with Ctrl+C. Do not run this at the same time as a registered webhook —
Telegram allows only one delivery method at a time (the script clears any
existing webhook on startup).
"""
import os
import sys
import time
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal  # noqa: E402
from services import telegram_service  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("telegram_bot")

POLL_TIMEOUT = 30  # seconds held open by Telegram per getUpdates call


def clear_webhook(token: str) -> None:
    """getUpdates is refused while a webhook is registered."""
    try:
        requests.post(
            f"{telegram_service.API_ROOT}/bot{token}/deleteWebhook",
            json={"drop_pending_updates": False},
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not clear webhook: %s", exc)


def main() -> int:
    token = telegram_service.bot_token()
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set. Add it to backend/.env (see .env.example)."
        )
        return 1

    try:
        me = telegram_service.get_me()
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not reach Telegram: %s", exc)
        return 1

    if not me.get("ok"):
        logger.error("Telegram rejected the token: %s", me)
        return 1

    username = me["result"].get("username")
    logger.info("Connected as @%s", username)

    allowed = telegram_service.allowed_chat_ids()
    if allowed:
        logger.info("Authorised chat IDs: %s", ", ".join(str(i) for i in sorted(allowed)))
    else:
        logger.warning(
            "TELEGRAM_ALLOWED_CHAT_IDS is empty — the bot will serve no credit data. "
            "Message the bot with /whoami to get your chat ID, add it to backend/.env, "
            "then restart."
        )

    clear_webhook(token)
    logger.info("Polling for updates. Press Ctrl+C to stop.")

    offset = None
    backoff = 1
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT}
            if offset is not None:
                params["offset"] = offset
            response = requests.get(
                f"{telegram_service.API_ROOT}/bot{token}/getUpdates",
                params=params,
                timeout=POLL_TIMEOUT + 15,
            )
            response.raise_for_status()
            payload = response.json()
            backoff = 1

            for update in payload.get("result", []):
                # Advance the offset before handling so a failing update is not
                # replayed forever.
                offset = update["update_id"] + 1
                db = SessionLocal()
                try:
                    chat = (update.get("message") or {}).get("chat") or {}
                    text = (update.get("message") or {}).get("text") or ""
                    logger.info("chat %s: %s", chat.get("id"), text[:80])
                    telegram_service.handle_update(update, db)
                except Exception:
                    logger.exception("Failed to handle update %s", update.get("update_id"))
                finally:
                    db.close()

        except KeyboardInterrupt:
            logger.info("Stopped.")
            return 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("Poll failed (%s). Retrying in %ss.", exc, backoff)
            time.sleep(backoff)
            backoff = min(60, backoff * 2)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
