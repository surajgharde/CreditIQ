from dotenv import load_dotenv
load_dotenv()  # MUST be first — loads .env into os.environ before any service reads keys

import traceback
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import config

print("=== STARTING CreditIQ BACKEND ===")

# ---------------------------------------------------------
# 1. APP DEFINITION
# ---------------------------------------------------------

app = FastAPI(
    title="CreditIQ — AI Credit Intelligence Platform",
    version="1.0.0",
)

# Only the configured frontend origins. This was allow_origins=["*"] together
# with allow_credentials=True — a combination browsers reject outright, and one
# that states the intent to let any site on the internet call this API with the
# user's credentials attached. Set CORS_ORIGINS in .env for other deployments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
def root():
    return {"status": "API running successfully"}

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------
# 2. DATABASE, ML SERVICES AND ROUTERS
# ---------------------------------------------------------
# Wrapped in try/except so that a failure in the heavy ML/DB stack still
# leaves the app bound to $PORT and serving /health for the platform probe.
# ---------------------------------------------------------

try:
    print("Loading database and ML dependencies...")

    # === STEP A: Database Connections ===
    from database import engine, Base, SessionLocal
    from utils.demo_data import load_demo_data

    # Registers every model on Base.metadata — without this, create_all() only
    # creates the tables whose modules happen to have been imported already.
    import models  # noqa: F401

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_demo_data(db)
    finally:
        db.close()

    # === STEP B: ML Services & Routers ===
    from routers import upload, analyze, fraud, scoring, cam, ews, ws, history, ews_ws, health_live, auth, draft, chat, telegram, profile
    from routers.auth import get_current_user

    # Every router that touches borrower data requires a bearer token. Applied
    # at registration so a new endpoint added to any of these routers is
    # protected by default rather than by remembering to decorate it.
    #
    # Deliberately NOT in this list:
    #   auth      — /login has to be reachable to obtain a token
    #   telegram  — Telegram calls the webhook; it authenticates with
    #               TELEGRAM_WEBHOOK_SECRET instead
    #   ws, ews_ws, health_live — WebSocket handshakes cannot carry an
    #               Authorization header, so those endpoints authenticate the
    #               `token` query parameter themselves
    authenticated = [Depends(get_current_user)]

    app.include_router(upload.router, tags=["Upload"], dependencies=authenticated)
    app.include_router(analyze.router, tags=["Analyze"], dependencies=authenticated)
    app.include_router(fraud.router, tags=["Fraud"], dependencies=authenticated)
    app.include_router(scoring.router, tags=["Scoring"], dependencies=authenticated)
    app.include_router(cam.router, tags=["CAM"], dependencies=authenticated)
    app.include_router(ews.router, tags=["EWS"], dependencies=authenticated)
    app.include_router(history.router, tags=["History"], dependencies=authenticated)
    app.include_router(draft.router, dependencies=authenticated)
    app.include_router(chat.router, tags=["Chat"], dependencies=authenticated)
    app.include_router(profile.router, tags=["Profile"], dependencies=authenticated)

    app.include_router(auth.router)
    app.include_router(ws.router)
    app.include_router(ews_ws.router)
    app.include_router(health_live.router)
    app.include_router(telegram.router, tags=["Telegram"])

    print("All components loaded. Server ready to listen on $PORT.")

except Exception as e:
    print("=== CRITICAL STARTUP ERROR ===")
    print("Startup Error:", e)
    traceback.print_exc()
    print("================================")
    
