#!/usr/bin/env python
"""Diagnostic script to test main.py imports"""
import sys
import traceback
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

print("=" * 60)
print("DIAGNOSTIC REPORT")
print("=" * 60)
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path[:3]}")

try:
    print("\n[1/6] Loading .env...")
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ .env loaded")
    
    print("\n[2/6] Importing config...")
    from config import config
    print(f"✓ config imported: DATABASE_URL={config.DATABASE_URL}")
    
    print("\n[3/6] Importing database...")
    from database import engine, Base, SessionLocal
    print(f"✓ database imported")
    
    print("\n[4/6] Importing routers...")
    from routers import upload, analyze, fraud, scoring, cam, ews, health, ws, history, ews_ws, health_live
    print(f"✓ All routers imported")
    
    print("\n[5/6] Creating FastAPI app...")
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    from utils.demo_data import load_demo_data
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            load_demo_data(db)
        finally:
            db.close()
        yield
    
    app = FastAPI(lifespan=lifespan)
    print(f"✓ FastAPI app created")
    
    print("\n[6/6] Importing main module...")
    import main
    print(f"✓ main module imported")
    print(f"✓ main.app exists: {hasattr(main, 'app')}")
    
    print("\n" + "=" * 60)
    print("SUCCESS - All imports working!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ ERROR at step:")
    print(f"{type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
