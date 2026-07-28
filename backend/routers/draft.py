from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models.draft import FormDraft
from pydantic import BaseModel

router = APIRouter(prefix="/api/analysis", tags=["Drafts"])

def get_current_user_email(x_user_email: str = Header(None)):
    if x_user_email:
        return x_user_email
    return "admin@gmail.com" # default fallback

class DraftCreate(BaseModel):
    company_name: str
    cin_number: str
    gstin_number: str
    pan_number: str
    loan_amount: float

@router.get("/latest")
def get_latest_draft(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    draft = db.query(FormDraft).filter(FormDraft.user_email == email).order_by(FormDraft.id.desc()).first()
    if not draft:
        return {"status": "success", "data": None}
    
    return {
        "status": "success",
        "data": {
            "company_name": draft.company_name,
            "cin": draft.cin_number,
            "gstin": draft.gstin_number,
            "pan": draft.pan_number,
            "amount": draft.loan_amount,
            "updated_at": draft.updated_at.isoformat() if draft.updated_at else draft.created_at.isoformat()
        }
    }

@router.post("/save")
def save_draft(
    draft_data: DraftCreate,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    draft = db.query(FormDraft).filter(FormDraft.user_email == email).first()
    if draft:
        draft.company_name = draft_data.company_name
        draft.cin_number = draft_data.cin_number
        draft.gstin_number = draft_data.gstin_number
        draft.pan_number = draft_data.pan_number
        draft.loan_amount = draft_data.loan_amount
    else:
        draft = FormDraft(
            user_email=email,
            company_name=draft_data.company_name,
            cin_number=draft_data.cin_number,
            gstin_number=draft_data.gstin_number,
            pan_number=draft_data.pan_number,
            loan_amount=draft_data.loan_amount
        )
        db.add(draft)
    
    db.commit()
    return {"status": "success", "message": "Draft saved successfully"}
