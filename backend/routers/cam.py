import os
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models.analysis import Analysis
from models.company import Company
from models.fraud import FraudSignal
from services import cam_service
from routers.ws import manager

router = APIRouter()

class CAMRequest(BaseModel):
    field_observations: Optional[str] = ""

async def pump_ws_progress(analysis_id: int):
    try:
        # Pushes progress over WS out to 95%
        for pct in range(5, 96, 5):
            await asyncio.sleep(1)
            await manager.send_personal_message({
                "step_number": 7,
                "step_name": "Claude AI CAM Generation",
                "step_detail": f"Structuring document vectors... {pct}%",
                "percentage": pct,
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }, str(analysis_id))
    except asyncio.CancelledError:
        pass

@router.post("/api/cam/generate/{analysis_id}")
async def generate_cam_document(analysis_id: int, body: CAMRequest = CAMRequest(), db: Session = Depends(get_db)):
    field_observations = (body.field_observations or "").strip()
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    company = db.query(Company).filter(Company.id == analysis.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    # Start the background progress pumper
    progress_task = asyncio.create_task(pump_ws_progress(analysis_id))
    
    fraud_data = {}
    results_data = {}
    
    fraud_file = f"data/fraud_{analysis.id}.json"
    if os.path.exists(fraud_file):
        with open(fraud_file, "r") as f:
            fraud_data = json.load(f)
            
    results_file = f"data/results_{analysis.id}.json"
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            results_data = json.load(f)

    decision_info = results_data.get("recommendation", {})
    shap_info = results_data.get("shap", {})
    
    # Pack data strictly mapping what the Claude Engine needs
    analysis_data = {
        "company": {
            "company_name": company.company_name,
            "cin": company.cin_number,
            "gstin": company.gstin_number,
            "pan": company.pan_number,
            "loan_amount_requested": company.loan_amount_requested
        },
        "fraud": {
            "overall_fraud_risk": fraud_data.get("fraud_risk_level", "LOW"),
            "signals": fraud_data.get("signals", [])
        },
        "news": {
            "news_risk_score": analysis.news_risk_score,
            "top_signals": results_data.get("news_signals", [])
        },
        "shap": {
            "shap_chart_url": shap_info.get("shap_chart_url"),
            "shap_factors": shap_info.get("shap_factors", [])
        },
        "decision": {
            "probability_of_default": shap_info.get("final_pd", analysis.probability_of_default),
            "data_quality_score": analysis.data_quality_score,
            "decision": analysis.decision,
            "decision_reasoning": decision_info.get("decision_reasoning", ""),
            "conditions": decision_info.get("conditions", []),
            "recommended_loan_amount": analysis.recommended_loan_amount,
            "recommended_interest_rate": analysis.recommended_interest_rate
        }
    }
    
    try:
        # Call service physically blocking but running in safe asyncio thread
        cam_res = await asyncio.to_thread(cam_service.generate_cam, analysis_data, field_observations)
        
        # In a real app we'd save paths back to db if newly generated
        analysis.cam_document_path = cam_res.get("word_document_path")
        analysis.cam_pdf_path = cam_res.get("pdf_document_path")
        db.commit()
    finally:
        # Stop pumper
        progress_task.cancel()
        
    # Send absolute completion ping
    await manager.send_personal_message({
        "step_number": 7,
        "step_name": "Claude AI CAM Generation",
        "step_detail": "Complete.",
        "percentage": 100,
        "status": "completed",
        "timestamp": datetime.now().isoformat()
    }, str(analysis_id))
    
    return cam_res

@router.get("/api/cam/download/{analysis_id}")
def download_cam(
    analysis_id: int, 
    format: str = Query(..., description="Document format: 'word' or 'pdf'"),
    demo: str = Query(None, description="Demo Account No or PAN"),
    db: Session = Depends(get_db)
):
    import glob

    if demo:
        company_name = ""
        if demo in ['AAACB1234M', '45678219304']:
            company_name = "Tata_Consultancy_Services_Limited"
        elif demo in ['AAACM5678L', '58923104765']:
            company_name = "Tech_Mahindra_Limited"
        elif demo in ['AAACI6789N', '67289103452']:
            company_name = "Infosys_Limited"
            
        if company_name:
            ext = ".docx" if format.lower() == "word" else ".pdf"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx" else "application/pdf"
            pattern = f"docs/CreditIQ_CAM_{company_name}_*{ext}"
            files = glob.glob(pattern)
            if not files:
                pattern2 = f"docs/CreditIQ_CAM__{company_name}_*{ext}"
                files = glob.glob(pattern2)
                
            if files:
                files.sort(key=os.path.getmtime, reverse=True)
                file_path = files[0]
                filename = os.path.basename(file_path)
                return FileResponse(
                    path=file_path, 
                    media_type=media_type, 
                    filename=filename,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )

    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    company = db.query(Company).filter(Company.id == analysis.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    if format.lower() not in ["word", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'word' or 'pdf'.")
        
    # Generate filename dynamically based off Company mapping
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_company_name = company.company_name.replace(" ", "_").replace("/", "-")
    
    ext = ".docx" if format.lower() == "word" else ".pdf"
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx" else "application/pdf"
    filename = f"CreditIQ_CAM_{safe_company_name}_{date_str}{ext}"
    
    # If format is PDF but file doesn't exist, raise error and explain why.
    if format.lower() == "pdf" and (not analysis.cam_pdf_path or not os.path.exists(analysis.cam_pdf_path)):
         raise HTTPException(
             status_code=500, 
             detail="Physical PDF document not found on server. Ensure Microsoft Word is installed for native PDF conversion from the synthesized Word document."
         )
         
    file_path = analysis.cam_document_path if format.lower() == "word" else analysis.cam_pdf_path
    
    return FileResponse(
        path=file_path, 
        media_type=media_type, 
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/api/cam/preview/{analysis_id}")
def preview_cam(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    company = db.query(Company).filter(Company.id == analysis.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    # Load dynamic logic
    fraud_data = {}
    results_data = {}
    
    fraud_file = f"data/fraud_{analysis.id}.json"
    if os.path.exists(fraud_file):
        with open(fraud_file, "r") as f:
            fraud_data = json.load(f)
            
    results_file = f"data/results_{analysis.id}.json"
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            results_data = json.load(f)
            
    decision_info = results_data.get("recommendation", {})
    shap_info = results_data.get("shap", {})
    
    pd_val = shap_info.get("final_pd", analysis.probability_of_default)
    fraud_val = fraud_data.get("fraud_risk_level", "LOW")

    # Return actual findings extracted from the results JSON
    # This avoids hardcoded sentence templates and presents the objective truth of the analysis
    recommendation = results_data.get("recommendation", {}) if isinstance(results_data, dict) else {}
    shap = results_data.get("shap", {}) if isinstance(results_data, dict) else {}
    
    findings = [
        f"Probability of Default calculated at {pd_val:.1f}%",
        f"Fraud Risk Assessment: {fraud_val}",
        f"Model Decision: {analysis.decision or 'PENDING'}",
        f"Data Quality Score: {analysis.data_quality_score:.1f}/100"
    ]
    
    if recommendation.get("conditions"):
        findings.extend(recommendation.get("conditions", []))

    return {
        "executive_summary": recommendation.get("decision_reasoning", "Analysis results pending final review."),
        "decision": analysis.decision or "PENDING",
        "key_findings": findings,
        "fraud_summary": f"Integrity check returned risk level {fraud_val}. Specific evidence found in {len(fraud_data.get('signals', [])) if isinstance(fraud_data, dict) else 0} signals.",
        "credit_score_summary": f"XGBoost Model evaluated final PD at {pd_val:.1f}%. Top factor: {shap.get('shap_factors', ['None'])[0] if isinstance(shap, dict) and shap.get('shap_factors') else 'N/A'}."
    }
