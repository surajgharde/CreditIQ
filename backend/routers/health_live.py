"""
Real-Time Backend Health Monitor
GET  /api/health/live    — instant live check of every component
WS   /ws/health          — streams live health every 15 seconds
"""
import os
import time
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from database import engine, SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────────────────────────────────────────
# INDIVIDUAL COMPONENT CHECKERS
# ──────────────────────────────────────────────────────

def check_database() -> dict:
    t0 = time.time()
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "connected", "response_time_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)[:100], "response_time_ms": None}


def check_redis() -> dict:
    t0 = time.time()
    try:
        import redis as _redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = _redis.from_url(url, socket_connect_timeout=3)
        r.ping()
        return {"status": "connected", "response_time_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)[:100], "response_time_ms": None}


def check_chromadb() -> dict:
    try:
        from services.external_apis import chroma_collection, CHROMA_CONNECTED
        if CHROMA_CONNECTED and chroma_collection:
            count = chroma_collection.count()
            return {"status": "connected", "document_count": count}
        return {"status": "disconnected", "document_count": 0}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)[:100]}


def check_cohere() -> dict:
    t0 = time.time()
    try:
        import cohere
        api_key = os.getenv("COHERE_API_KEY", "")
        if not api_key:
            return {"status": "no_key", "response_time_ms": None}
        co = cohere.ClientV2(api_key=api_key)
        resp = co.chat(
            model="command-r-08-2024",
            messages=[{"role": "user", "content": "Say OK in one word."}]
        )
        answer = resp.message.content[0].text.strip()
        return {
            "status": "connected",
            "response_time_ms": round((time.time() - t0) * 1000, 1),
            "test_response": answer[:20],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:100], "response_time_ms": None}


def check_xgboost() -> dict:
    t0 = time.time()
    try:
        import xgboost as xgb
        import numpy as np
        model_path = os.path.join(os.getcwd(), "models", "credit_model.json")
        if not os.path.exists(model_path):
            # Try alternate paths
            for candidate in ["credit_model.json", "model.json", "xgb_model.json"]:
                fp = os.path.join(os.getcwd(), candidate)
                if os.path.exists(fp):
                    model_path = fp
                    break
            else:
                return {"status": "model_file_missing", "prediction_time_ms": None}
        model = xgb.Booster()
        model.load_model(model_path)
        dummy = xgb.DMatrix(np.zeros((1, 15)))
        _ = model.predict(dummy)
        return {"status": "loaded", "prediction_time_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100], "prediction_time_ms": None}


def check_finbert() -> dict:
    t0 = time.time()
    try:
        from services.external_apis import get_sentiment
        result = get_sentiment("Company is profitable and growing.")
        if "error" in result:
            return {"status": "failed", "error": result["error"][:80], "inference_time_ms": None}
        return {
            "status": "loaded",
            "classification": result.get("classification"),
            "inference_time_ms": round((time.time() - t0) * 1000, 1),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:100], "inference_time_ms": None}


def check_gstn_api() -> dict:
    t0 = time.time()
    try:
        url = os.getenv("GSTN_API_URL", "https://sandbox.api.gstn.org")
        import requests
        r = requests.get(f"{url}/v2/returns/history/29ABCDE1234F1Z5", timeout=5)
        reachable = r.status_code in [200, 401, 403, 404]  # any response = reachable
        return {"status": "reachable" if reachable else "unreachable", "http_code": r.status_code,
                "response_time_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)[:80], "response_time_ms": None}


def check_mca_api() -> dict:
    t0 = time.time()
    try:
        url = os.getenv("MCA_API_URL", "https://api.thecompaniesapi.com/v1")
        key = os.getenv("MCA_API_KEY", "")
        import requests
        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(f"{url}/companies/U12345MH2001PTC123456", headers=headers, timeout=5)
        reachable = r.status_code in [200, 401, 403, 404]
        return {"status": "reachable" if reachable else "unreachable", "http_code": r.status_code,
                "response_time_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)[:80], "response_time_ms": None}


def check_twilio() -> dict:
    try:
        from twilio.rest import Client
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        if not sid or not token:
            return {"status": "no_credentials"}
        client = Client(sid, token)
        balance = client.api.accounts(sid).balance.fetch()
        return {"status": "connected", "balance": f"{balance.currency} {balance.balance}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}


def check_scraper() -> dict:
    t0 = time.time()
    try:
        import requests
        r = requests.get(
            "https://news.google.com/rss/search?q=India+NBFC+credit&hl=en-IN&gl=IN&ceid=IN:en",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        if r.status_code == 200 and "<rss" in r.text[:500]:
            return {
                "status": "working",
                "last_successful_scrape": datetime.now().isoformat(),
                "response_time_ms": round((time.time() - t0) * 1000, 1),
            }
        return {"status": "degraded", "http_code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)[:80], "response_time_ms": None}


# ──────────────────────────────────────────────────────
# MASTER HEALTH CHECK
# ──────────────────────────────────────────────────────

def run_all_checks() -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database":     check_database(),
            "redis":        check_redis(),
            "chromadb":     check_chromadb(),
            "cohere_ai":    check_cohere(),
            "xgboost":      check_xgboost(),
            "finbert":      check_finbert(),
            "gstn_api":     check_gstn_api(),
            "mca_api":      check_mca_api(),
            "twilio":       check_twilio(),
            "scraper":      check_scraper(),
        }
    }


# ──────────────────────────────────────────────────────
# REST ENDPOINT
# ──────────────────────────────────────────────────────

@router.get("/api/health/live")
async def live_health():
    """Real-time health check of every backend component."""
    result = await asyncio.to_thread(run_all_checks)
    
    comps = result["components"]
    ok_count = sum(
        1 for v in comps.values()
        if isinstance(v, dict) and v.get("status") in ["connected", "loaded", "working", "reachable"]
    )
    total = len(comps)
    result["overall_score"] = round((ok_count / total) * 100, 1)
    result["status"] = "HEALTHY" if ok_count >= total * 0.8 else "DEGRADED"
    return result


# ──────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT  ws://localhost:8000/ws/health
# ──────────────────────────────────────────────────────

@router.websocket("/ws/health")
async def health_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Health WebSocket connected.")
    try:
        while True:
            result = await asyncio.to_thread(run_all_checks)
            comps = result["components"]
            ok_count = sum(
                1 for v in comps.values()
                if isinstance(v, dict) and v.get("status") in ["connected", "loaded", "working", "reachable"]
            )
            result["overall_score"] = round((ok_count / len(comps)) * 100, 1)
            result["status"] = "HEALTHY" if ok_count >= len(comps) * 0.8 else "DEGRADED"
            result["type"] = "health_update"
            await websocket.send_json(result)
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        logger.info("Health WebSocket disconnected.")
    except Exception as e:
        logger.error(f"Health WebSocket error: {e}")
