import json
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis import Analysis
from models.company import Company
from models.fraud import FraudSignal

router = APIRouter()

@router.get("/api/history")
def get_analysis_history(db: Session = Depends(get_db)):
    # Fetch all analyses joined with company data
    results = db.query(Analysis, Company).join(
        Company, Analysis.company_id == Company.id
    ).order_by(Analysis.id.desc()).all()
    
    formatted_history = []
    
    for analysis, company in results:
        formatted_history.append({
            "analysis_id": analysis.id,
            "company_name": company.company_name,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else "",
            "status": analysis.analysis_status,
            "failure_reason": analysis.failure_reason,
            "decision": analysis.decision,
            "probability_of_default": analysis.probability_of_default,
            "fraud_risk_level": analysis.fraud_risk_level,
        })
        
    return formatted_history
