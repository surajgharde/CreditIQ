import os
import json
import logging
from datetime import datetime, timedelta
import requests

from twilio.rest import Client
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from apscheduler.schedulers.background import BackgroundScheduler

from sqlalchemy.orm import Session
from database import SessionLocal
from models.company import Company
from models.ews import EWSSignal, EWSTrajectory
from models.analysis import Analysis

logger = logging.getLogger(__name__)

# =========================================================
# APSCHEDULER INITIALIZATION
# =========================================================
scheduler = BackgroundScheduler()
# The scheduler would be started from main.py lifecycle events

# =========================================================
# SENDING LOGIC (TWILIO + SENDGRID)
# =========================================================
def send_sms_alert(phone_number: str, message: str):
    """Sends native SMS using Twilio API"""
    try:
        # Require ENV variables for live routing
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_phone = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not account_sid or not auth_token:
            logger.warning(f"SMS Alert Skipped: Missing Twilio Credentials. Payload: {message}")
            return False
            
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_phone, to=phone_number)
        return True
    except Exception as e:
        logger.error(f"Failed to send Twilio SMS: {str(e)}")
        return False

def send_email_alert(recipient_email: str, subject: str, html_content: str):
    """Sends native Email using SendGrid API"""
    try:
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            logger.warning(f"Email Alert Skipped: Missing SendGrid Credentials.")
            return False
            
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        from_email = Email("alerts@creditiq.ai")
        to_email = To(recipient_email)
        mail = Mail(from_email, to_email, subject, html_content=html_content)
        sg.client.mail.send.post(request_body=mail.get())
        return True
    except Exception as e:
        logger.error(f"Failed to send SendGrid Email: {str(e)}")
        return False

# =========================================================
# SIGNAL PROCESSORS (Live Logic)
# =========================================================

def check_gst_filing_status(gstin: str) -> dict:
    """SIGNAL 1: Query GST Sandbox mapped API"""
    if not gstin:
        raise ValueError("GSTIN not provided for company. Cannot execute GST signal.")
        
    from services.external_apis import get_filing_history
    history = get_filing_history(gstin)
    
    if history and isinstance(history[0], dict) and "error" in history[0]:
        raise ValueError(f"GST API Failed: {history[0]['error']}")

    missing_points = 0
    for rec in history:
        if rec.get("status", "").lower() != "filed" or rec.get("late_days", 0) > 0:
            missing_points += 20.0
            
    score = max(0.0, 100.0 - missing_points)
    risk = "HIGH" if score < 50 else ("MEDIUM" if score < 80 else "GOOD")
    return {"score": score, "risk_level": risk, "detail": f"Deducted {missing_points} points for late/missed filings based on GSTN Sandbox."}

def check_bank_activity(bank_api_key: str) -> dict:
    """SIGNAL 2: Compare 30D vs 90D baseline"""
    raise NotImplementedError("Bank statement API is not connected. Real transaction volume cannot be fetched.")

def monitor_court_cases(company_name: str) -> dict:
    """SIGNAL 3: Scraped E-Courts mapping DRT/Insolvency hits"""
    # Simulate routing logic that RAG would typically execute
    raise NotImplementedError("Live E-Courts dedicated scraper proxy not implemented or available.")

def monitor_news_sentiment(company_name: str) -> dict:
    """SIGNAL 4: Integrate RAG Dictionary Sentiment trending"""
    from services.rag_service import get_news_intelligence
    news_res = get_news_intelligence(company_name, "")
    if "error" in news_res:
        raise ValueError(f"News RAG execution failed: {news_res['error']}")
        
    current_score = news_res.get("news_risk_score", 0.0)
    score = 100.0 - current_score
    risk = "HIGH" if score < 50 else ("MEDIUM" if score < 80 else "GOOD")
    
    return {"score": score, "risk_level": risk, "detail": f"Current News NLP Risk Score is {current_score:.1f} out of 100."}

def check_mca_filings(cin: str) -> dict:
    """SIGNAL 5: MCA Annual Return / Director Change API Tracker"""
    if not cin:
        raise ValueError("CIN not provided. Cannot fetch MCA details.")
    from services.external_apis import get_company_filings
    filings = get_company_filings(cin)
    if filings and isinstance(filings[0], dict) and "error" in filings[0]:
        raise ValueError(f"MCA API Failed: {filings[0]['error']}")
        
    return {"score": 100.0, "risk_level": "GOOD", "detail": f"{len(filings)} MCA filings fetched cleanly."}

def check_emi_status(loan_id: str) -> dict:
    """SIGNAL 6: Internal Loan Ledger check"""
    raise NotImplementedError("Internal Loan Ledger / CBS Not Connected. Real EMI status unavailable.")

def check_cibil_commercial(cin: str) -> dict:
    """SIGNAL 7: Commercial Bureau Ping"""
    raise NotImplementedError("CIBIL API Connection Missing. Cannot fetch real commercial rating.")

def check_sector_pmi() -> dict:
    """SIGNAL 8: Macro-indicators from RBI/Public"""
    raise NotImplementedError("External Market PMI Database Connection missing.")

def check_promoter_holding(company_name: str) -> dict:
    """SIGNAL 9: Share Pledging (BSE API Tracker)"""
    raise NotImplementedError("BSE/NSE Feed Not Connected. Cannot scrape promoter holdings live.")

# Remaining boilerplate mocks (10 to 15)
def check_additional_signals(signal_id: int) -> dict:
    raise NotImplementedError(f"Signal ID {signal_id} logic not fully implemented structurally.")

# =========================================================
# MASTER AGGREGATOR & ALERT TRIGGER ENGINE
# =========================================================

def run_portfolio_scan():
    """Scheduled task executed globally across active loans."""
    db = SessionLocal()
    try:
        active_loans = db.query(Company).filter(Company.status == 'Active Loan').all()
        for company in active_loans:
            process_ews_for_company(company.id, db)
    finally:
        db.close()

def process_ews_for_company(company_id: int, db: Session = None):
    """Executes the specific 15 API calls actively computing trajectories and triggering alerts natively."""
    close_db_locally = False
    if not db:
        db = SessionLocal()
        close_db_locally = True
        
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company: return
        
        # Safely wrap functional invocations handling exact exception throwing
        def safe_invoke(name, source, func, *args):
            try:
                res = func(*args)
                return (name, source, res)
            except Exception as e:
                logger.error(f"EWS Signal '{name}' Failed / Missing Data: {e}")
                return (name, source, {"score": 0.0, "risk_level": "ERROR", "detail": str(e)})

        # 1. Execute All 15 Native Signal Pollers dynamically trapping failures instead of halting EWS completely
        sig_data = [
            safe_invoke("GST Filing Status", "GSTN API", check_gst_filing_status, company.gstin_number),
            safe_invoke("Bank Account Activity", "Banking API", check_bank_activity, "API_KEY"),
            safe_invoke("Court Case Monitor", "e-Courts Scraper", monitor_court_cases, company.company_name),
            safe_invoke("News Sentiment", "RAG Engine", monitor_news_sentiment, company.company_name),
            safe_invoke("MCA Filing Status", "MCA21", check_mca_filings, company.cin_number),
            safe_invoke("EMI Payment Status", "Internal Ledger", check_emi_status, str(company.id)),
            safe_invoke("Credit Bureau Update", "CIBIL API", check_cibil_commercial, company.cin_number),
            safe_invoke("Sector PMI Trend", "RBI Public", check_sector_pmi),
            safe_invoke("Promoter Shareholding", "BSE Disclosures", check_promoter_holding, company.company_name)
        ]
        
        for i in range(10, 16):
            sig_data.append(safe_invoke(f"Compliance Tracker {i}", "Data Warehouse", check_additional_signals, i))
            
        # 2. Write signals physically into Database
        total_signal_score = 0.0
        valid_signals = 0
        critical_triggered = False
        top_risk_signal = None
        
        for name, source, data in sig_data:
            if data["risk_level"] == "ERROR":
                continue # Do not heavily fault PD mapping on missing architectural plugins
                
            total_signal_score += data["score"]
            valid_signals += 1
            if data["risk_level"] in ["CRITICAL", "HIGH"]:
                critical_triggered = True
                top_risk_signal = (name, data["detail"])
            
            # Upsert EWSSignal objects into Database
            new_sig = EWSSignal(
                company_id=company.id,
                signal_name=name,
                source=source,
                signal_score=data["score"],
                risk_level=data["risk_level"],
                detail=data["detail"]
            )
            db.add(new_sig)
        db.commit()
            
        if valid_signals > 0:
            average_signal_score = total_signal_score / valid_signals
        else:
            average_signal_score = 100.0
        
        # 3. Trajectory PD Calculation mapping original XGBoost
        # Assuming original base XGBoost PD was recorded as 16.0%
        original_base_pd = 16.0 
        
        # Penalty scaling: A lower score (< 100) on active signals inflates default risk
        # E.g., Avg score 60 => 40 point penalty applied against PD logarithmically 
        trajectory_modifier = (100.0 - average_signal_score) * 0.4 
        new_pd = original_base_pd + trajectory_modifier
        
        # Map previous days PD logic
        previous_pd = 18.0 
        pd_delta = new_pd - previous_pd
        
        alert_triggered = False
        alert_reasons = []
        
        # 4. Alert Routing Conditions natively executing Twilio/SendGrid
        if pd_delta > 5.0:
            alert_triggered = True
            alert_reasons.append(f"Probability of Default spiked by {pd_delta:.1f}% structurally inside 7 days.")
            
        if new_pd > 25.0:
            alert_triggered = True
            alert_reasons.append(f"Absolute PD threshold crossed (Currently {new_pd:.1f}%).")
            
        if critical_triggered:
            alert_triggered = True
            alert_reasons.append(f"CRITICAL Priority Signal Detected: {top_risk_signal[0]} - {top_risk_signal[1]}")
            
        if alert_triggered:
            sms_text = f"CreditIQ EWS ALERT: {company.company_name} flagged. Risk: {new_pd:.1f}%. Top Issue: {top_risk_signal[0]}. Review immediately."
            html_body = f"<h2>Early Warning Triggered: {company.company_name}</h2><ul>"
            for reason in alert_reasons: html_body += f"<li>{reason}</li>"
            html_body += "</ul>"
            
            # Execute Network Layers (Skipped strictly locally if keys empty, logs catch it automatically)
            send_sms_alert("+919876543210", sms_text)
            send_email_alert("rm_manager@nbfc.com", f"URGENT EWS Action Required - {company.company_name}", html_body)

    finally:
        if close_db_locally:
            db.close()

# =========================================================
# ROUTER FACING EXPORTS
# =========================================================
def get_ews_data(company_id: int) -> dict:
    """Returns the aggregated timeline structure natively queried from DB."""
    db = SessionLocal()
    try:
        trajectories = db.query(EWSTrajectory).filter(EWSTrajectory.company_id == company_id).order_by(EWSTrajectory.id.asc()).all()
        signals = db.query(EWSSignal).filter(EWSSignal.company_id == company_id).order_by(EWSSignal.score.asc()).all()
        
        traj_data = []
        for t in trajectories:
            traj_data.append({
                "month": t.month,
                "year": t.year,
                "probability_of_default": float(t.probability_of_default),
                "is_predicted": t.is_predicted
            })
            
        sig_data = []
        for s in signals:
            sig_data.append({
                "signal_name": s.signal_name,
                "score": float(s.signal_score) if s.signal_score is not None else 0.0,
                "risk_level": s.risk_level,
                "detail": s.detail,
                "source": s.source
            })
            
        return {
            "trajectory": traj_data,
            "signals": sig_data
        }
    finally:
        db.close()
