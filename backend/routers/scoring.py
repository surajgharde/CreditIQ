import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from models.analysis import Analysis
from models.company import Company
from models.fraud import FraudSignal

router = APIRouter()

@router.get("/api/results/{analysis_id}")
def get_analysis_results(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    if analysis.analysis_status.lower() == "failed":
        raise HTTPException(
            status_code=400, 
            detail=f"Analysis failed: {analysis.failure_reason or 'Unknown error. Check backend logs'}"
        )
        
    if analysis.analysis_status.lower() != "completed":
        raise HTTPException(status_code=400, detail="Analysis is still in progress. Please check back in a few seconds.")
        
    company = db.query(Company).filter(Company.id == analysis.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    fraud_signals_db = db.query(FraudSignal).filter(FraudSignal.analysis_id == analysis.id).all()
    
    signals = []
    for sig in fraud_signals_db:
        signals.append({
            "type": sig.signal_type,
            "risk_level": sig.risk_level,
            "description": sig.description,
            "evidence_amount": sig.evidence_amount,
            "confidence_score": sig.confidence_score,
            "source": sig.source
        })

    import json
    import os
    dashboard_data = {}
    json_path = f"data/results_{analysis.id}.json"
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            dashboard_data = json.load(f)
            
    base_risk = dashboard_data.get("shap", {}).get("base_risk", 16.0)
    final_pd = analysis.probability_of_default or 31.0
    
    return {
        "company": {
            "company_name": company.company_name,
            "cin_number": company.cin_number,
            "gstin_number": company.gstin_number,
            "loan_amount_requested": company.loan_amount_requested
        },
        "decision": {
            "decision": analysis.decision,
            "recommended_loan_amount": analysis.recommended_loan_amount,
            "recommended_interest_rate": analysis.recommended_interest_rate,
            "probability_of_default": analysis.probability_of_default,
            "data_quality_score": analysis.data_quality_score
        },
        "fraud": {
            "overall_fraud_risk": analysis.fraud_risk_level,
            "total_signals_found": len(signals),
            "signals": signals
        },
        "shap": {
            "shap_chart_url": f"/api/shap-chart/{analysis.id}",
            "shap_factors": dashboard_data.get("shap", {}).get("shap_factors", []),
            "base_risk": base_risk,
            "final_pd": final_pd
        },
        "news": {
            "news_risk_score": analysis.news_risk_score,
            "top_signals": dashboard_data.get("news_signals", [])
        },
        "recommendation": dashboard_data.get("recommendation", {
            "decision_reasoning": "Analysis generated via automated ML pipeline.",
            "conditions": [],
            "loan_tenure": 3,
            "interest_rate_breakdown": f"Base Rate + Risk Premium"
        })
    }

@router.get("/api/shap-chart/{analysis_id}")
def get_shap_chart(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    if analysis.analysis_status.lower() == "failed":
        raise HTTPException(
            status_code=400, 
            detail=f"Analysis failed: {analysis.failure_reason or 'Unknown error. Check backend logs'}"
        )
        
    if analysis.analysis_status.lower() != "completed":
        raise HTTPException(status_code=400, detail="SHAP chart is not yet available as analysis is still in progress.")
        
    chart_path = analysis.shap_chart_path
    
    if not chart_path:
        raise HTTPException(status_code=404, detail="SHAP chart path is empty")
        
    # Safely resolve the physical disk path from the logical relative URL format.
    # The scoring_service stores it as "/graphs/<uuid>.png"
    import os
    clean_path = chart_path.lstrip('/') if chart_path.startswith('/') else chart_path
    physical_disk_path = os.path.join(os.getcwd(), clean_path)
    
    if not os.path.exists(physical_disk_path):
        raise HTTPException(status_code=404, detail=f"SHAP chart file not physically found at {physical_disk_path}")
        
    return FileResponse(physical_disk_path, media_type="image/png")
