from sqlalchemy.orm import Session
from models.company import Company
from models.analysis import Analysis
from models.fraud import FraudSignal
from models.ews import EWSSignal
from datetime import datetime

def reset_demo_data(db: Session):
    # Wipe the specific ABC demo company and its data to a clean slate
    company = db.query(Company).filter(Company.cin_number == "U28990MH2015PTC123456").first()
    if company:
        analysis = db.query(Analysis).filter(Analysis.company_id == company.id).first()
        if analysis:
            db.query(FraudSignal).filter(FraudSignal.analysis_id == analysis.id).delete()
            db.delete(analysis)
        db.query(EWSSignal).filter(EWSSignal.company_id == company.id).delete()
        db.delete(company)
        db.commit()
    
    # Reload fresh
    load_demo_data(db)

def load_demo_data(db: Session):
    existing = db.query(Company).filter(Company.cin_number == "U28990MH2015PTC123456").first()
    if existing:
        return

    # Create Company Record
    company = Company(
        company_name="ABC Manufacturing Ltd",
        cin_number="U28990MH2015PTC123456",
        gstin_number="27AAAPZ1234F1Z5",
        pan_number="AAAPZ1234F",
        loan_amount_requested=300000000.0, # 30 Crore
        status="active"
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Create Analysis Record
    analysis = Analysis(
        company_id=company.id,
        data_quality_score=82.0,
        fraud_risk_level="HIGH",
        news_risk_score=72.0,
        probability_of_default=31.0,
        recommended_interest_rate=14.5,
        decision="CONDITIONAL",
        recommended_loan_amount=220000000.0, # 22 Crore
        analysis_status="completed",
        progress=100.0,
        cam_document_path="/docs/cam_abc.pdf",
        shap_chart_path="/graphs/shap_abc.png"
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Create Fraud Signal Records
    fraud1 = FraudSignal(
        analysis_id=analysis.id,
        signal_type="GST_MISMATCH",
        risk_level="HIGH",
        description="GSTR-2A shows 4.2 Crore but GSTR-3B claims 6.0 Crore. Fake ITC of 1.8 Crore detected.",
        evidence_amount=1800000.0, # 1.8 Crore as per prompt
        confidence_score=94.0,
        source="GSTN API cross-verification"
    )
    fraud2 = FraudSignal(
        analysis_id=analysis.id,
        signal_type="CIRCULAR_TRADING",
        risk_level="HIGH",
        description="Three entities rotating 4.2 Crore in closed loop. No real economic activity detected.",
        evidence_amount=4200000.0, # 4.2 Crore
        confidence_score=89.0,
        source="NetworkX Graph Analysis"
    )
    fraud3 = FraudSignal(
        analysis_id=analysis.id,
        signal_type="MCA_DIRECTOR",
        risk_level="HIGH",
        description="Promoter Rajesh Kumar DIN 01234567 was director of XYZ Pvt Ltd which defaulted 12 Crore in 2021. Currently disqualified under Section 164(2).",
        evidence_amount=12000000.0, # 12 Crore
        confidence_score=100.0,
        source="MCA Database"
    )
    db.add_all([fraud1, fraud2, fraud3])

    # Create 15 EWS Signals (3 RM alerts + 12 context signals)
    ews_signals = [
        EWSSignal(company_id=company.id, signal_name="Court Cases", signal_score=90.0, risk_level="CRITICAL", detail="New case filed March 2025", source="e-Courts", alert_sent=True, acknowledged=False),
        EWSSignal(company_id=company.id, signal_name="News Sentiment", signal_score=80.0, risk_level="HIGH", detail="CFO resignation + vendor delays", source="News API", alert_sent=True, acknowledged=False),
        EWSSignal(company_id=company.id, signal_name="Bank Activity", signal_score=60.0, risk_level="MEDIUM", detail="Cash balance dropped 40%", source="Bank Statement", alert_sent=True, acknowledged=False)
    ]
    
    dummy_signals = [
        ("GST Filing", 55.0, "MEDIUM", "September filing pending", "GSTN API"),
        ("Promoter Activity", 40.0, "LOW", "No new changes detected", "MCA"),
        ("EMI Status", 20.0, "GOOD", "All payments on time", "Internal DB"),
        ("Social Media", 35.0, "LOW", "Normal activity", "Twitter Analytics"),
        ("Employee Reviews", 42.0, "LOW", "Slight dip in rating", "Glassdoor API"),
        ("Utility Bills", 10.0, "GOOD", "Paid on time", "Provider Data"),
        ("EPF Filing", 15.0, "GOOD", "Regular deposits", "EPFO API"),
        ("Export Import", 25.0, "GOOD", "Stable shipment volume", "Customs Data"),
        ("Supplier Payments", 45.0, "LOW", "Slight delay, within terms", "Trade API"),
        ("Credit Ratings", 30.0, "LOW", "Stable rating", "CRISIL"),
        ("Legal Notices", 10.0, "GOOD", "None detected", "e-Courts"),
        ("Tax Defaults", 0.0, "GOOD", "No defaults", "IT Dept")
    ]
    
    for name, score, risk, detail, source in dummy_signals:
        ews_signals.append(EWSSignal(
            company_id=company.id,
            signal_name=name,
            signal_score=score,
            risk_level=risk,
            detail=detail,
            source=source,
            alert_sent=False,
            acknowledged=False
        ))
        
    db.add_all(ews_signals)
    db.commit()
