from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base

class EWSSignal(Base):
    __tablename__ = "ews_signals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    signal_name = Column(String)
    signal_score = Column(Float)
    risk_level = Column(String)
    detail = Column(String)
    source = Column(String)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    alert_sent = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)

class EWSTrajectory(Base):
    __tablename__ = "ews_trajectory"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    month = Column(String)
    year = Column(String)
    probability_of_default = Column(Float)
    is_predicted = Column(Boolean, default=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
