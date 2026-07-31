import os
from dotenv import load_dotenv
load_dotenv()  # MUST be first — loads .env into os.environ before any service reads keys

import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

print("=== STARTING CreditIQ BACKEND (DEBUG MODE) ===")

# ---------------------------------------------------------
# 1. MINIMAL APP DEFINITION (Ensures Server Binds to Port)
# ---------------------------------------------------------

app = FastAPI(
    title="CreditIQ — AI Credit Intelligence Platform (Debug)",
    version="1.0.0",
)

# CORS configuration (changed to wildcard temporarily to eliminate CORS-related aborts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
def root():
    return {"status": "API running successfully (Debug Mode)"}

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0 (Debug)"}


# ---------------------------------------------------------
# 2. ISOLATED HEAVY IMPORTS AND ROUTERS
# ---------------------------------------------------------
# All Database and ML logic has been wrapped in a try/except 
# block and temporarily disabled to guarantee port binding.
# 
# INSTRUCTIONS: To reintroduce step-by-step, uncomment sections below 
# one by one, deploy, and check if it crashes.
# ---------------------------------------------------------

try:
    print("Attempting to load Heavy Dependencies (Bypassed for Debug)...")

    # === STEP A: Database Connections ===
    from database import engine, Base, SessionLocal, get_db
    from sqlalchemy.orm import Session
    from utils.demo_data import load_demo_data, reset_demo_data

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
    from routers import upload, analyze, fraud, scoring, cam, ews, health, ws, history, ews_ws, health_live, auth, draft
    
    app.include_router(upload.router, tags=["Upload"])
    app.include_router(analyze.router, tags=["Analyze"])
    app.include_router(fraud.router, tags=["Fraud"])
    app.include_router(scoring.router, tags=["Scoring"])
    app.include_router(cam.router, tags=["CAM"])
    app.include_router(ews.router, tags=["EWS"])
    app.include_router(history.router, tags=["History"])
    app.include_router(ws.router)
    app.include_router(auth.router)
    app.include_router(ews_ws.router)
    app.include_router(health_live.router)
    app.include_router(draft.router)

    print("Heavy components bypassed. Server ready to listen on $PORT.")

except Exception as e:
    print("=== CRITICAL STARTUP ERROR ===")
    print("Startup Error:", e)
    traceback.print_exc()
    print("================================")
    
