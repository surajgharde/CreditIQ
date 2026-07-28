from fastapi import APIRouter, Form, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.company import Company
from models.analysis import Analysis
from utils.file_handler import save_upload_file, get_file_size_mb

router = APIRouter()

@router.post("/api/upload")
async def upload_files(
    company_name: str = Form(...),
    cin_number: str = Form(...),
    gstin_number: str = Form(...),
    pan_number: str = Form(...),
    loan_amount: float = Form(...),
    balance_sheet: UploadFile = File(...),
    bank_statement: UploadFile = File(...),
    gst_filing: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Save the uploaded files to disk
        bs_path   = save_upload_file(balance_sheet)
        bs_size   = get_file_size_mb(balance_sheet)
        bank_path = save_upload_file(bank_statement)
        bank_size = get_file_size_mb(bank_statement)
        gst_path  = save_upload_file(gst_filing)
        gst_size  = get_file_size_mb(gst_filing)

        # --- UPSERT: reuse existing company record if CIN already exists ---
        existing = db.query(Company).filter(Company.cin_number == cin_number).first()

        if existing:
            # Update file paths and loan amount in case they changed
            existing.bs_file_path         = bs_path
            existing.bank_file_path       = bank_path
            existing.gst_file_path        = gst_path
            existing.loan_amount_requested = loan_amount
            existing.status               = "pending"
            db.commit()
            db.refresh(existing)
            company = existing
        else:
            company = Company(
                company_name=company_name,
                cin_number=cin_number,
                gstin_number=gstin_number,
                pan_number=pan_number,
                loan_amount_requested=loan_amount,
                bs_file_path=bs_path,
                bank_file_path=bank_path,
                gst_file_path=gst_path,
                status="pending"
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        # Always create a fresh analysis for each submission
        new_analysis = Analysis(
            company_id=company.id,
            analysis_status="pending"
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

        return {
            "success": True,
            "company_id": company.id,
            "analysis_id": new_analysis.id,
            "message": "Files uploaded successfully",
            "uploaded_files": [
                {"name": balance_sheet.filename, "size_mb": round(bs_size, 2)},
                {"name": bank_statement.filename, "size_mb": round(bank_size, 2)},
                {"name": gst_filing.filename,     "size_mb": round(gst_size, 2)},
            ],
            "next_step": f"Call analyze endpoint with analysis_id {new_analysis.id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

