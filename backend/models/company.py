from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String, nullable=False)
    cin_number = Column(String, unique=True, index=True)
    gstin_number = Column(String, unique=True, index=True)
    pan_number = Column(String, index=True)
    loan_amount_requested = Column(Float)
    bs_file_path = Column(String)
    bank_file_path = Column(String)
    gst_file_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")
