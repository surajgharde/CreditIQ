from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from services.external_apis import health_check_integrations

router = APIRouter(prefix="/api/health", tags=["Health"])

@router.get("/integrations")
async def get_integrations_health():
    """Returns the live connection status of all external APIs and services."""
    return health_check_integrations()

@router.get("/full")
async def get_full_health(db: Session = Depends(get_db)):
    """Comprehensive check including Database, Cache, and all AI Models."""
    status = health_check_integrations()
    
    components = status["integrations"]
    
    # Check Database explicitly
    try:
        db.execute(text("SELECT 1"))
        components["database"] = "Connected"
    except Exception as e:
        components["database"] = "Disconnected"
        
    score = 100
    for key, val in components.items():
        if val != "Connected" and val != "Active" and val != "Configured" and val != "Loaded in Memory" and val != "Persistent Engine Active":
            score -= 10
            
    status["overall_health_score"] = max(0, score)
    status["status"] = "HEALTHY" if score > 70 else "DEGRADED"
    
    return status
