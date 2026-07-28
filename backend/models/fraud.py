from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class FraudSignal(Base):
    __tablename__ = "fraud_signals"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    signal_type = Column(String)
    risk_level = Column(String)
    description = Column(String)
    evidence_amount = Column(Float)
    confidence_score = Column(Float)
    source = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
