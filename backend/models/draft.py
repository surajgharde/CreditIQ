from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base

class FormDraft(Base):
    __tablename__ = "form_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True) # Associated with logged in user
    company_name = Column(String)
    cin_number = Column(String)
    gstin_number = Column(String)
    pan_number = Column(String)
    loan_amount = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
