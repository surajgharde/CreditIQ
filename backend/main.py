from dotenv import load_dotenv
load_dotenv()  # MUST be first — loads .env into os.environ before any service reads keys

import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

print("=== STARTING CreditIQ BACKEND ===")

# ---------------------------------------------------------
# 1. APP DEFINITION
# ---------------------------------------------------------

app = FastAPI(
    title="CreditIQ — AI Credit Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    from routers import upload, analyze, fraud, scoring, cam, ews, ws, history, ews_ws, health_live, auth, draft


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

    print("All components loaded. Server ready to listen on $PORT.")

except Exception as e:
    print("=== CRITICAL STARTUP ERROR ===")
    print("Startup Error:", e)
    traceback.print_exc()
    print("================================")
    
