from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    data_quality_score = Column(Float)
    fraud_risk_level = Column(String)
    news_risk_score = Column(Float)
    probability_of_default = Column(Float)
    recommended_interest_rate = Column(Float)
    decision = Column(String)
    recommended_loan_amount = Column(Float)
    shap_chart_path = Column(String)
    cam_document_path = Column(String)
    cam_pdf_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analysis_status = Column(String, default="processing")
    progress = Column(Float, default=0.0)
    failure_reason = Column(String, nullable=True)
