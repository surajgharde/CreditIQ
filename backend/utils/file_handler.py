import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from config import config

UPLOAD_FOLDER = getattr(config, "UPLOAD_FOLDER", None) or "uploads"
MAX_FILE_SIZE_MB = float(getattr(config, "MAX_FILE_SIZE", None) or 10.0)

def get_file_size_mb(file: UploadFile) -> float:
    file.file.seek(0, 2)
    size_in_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    return size_in_mb

def validate_pdf(file: UploadFile) -> bool:
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"File {file.filename} is not a valid PDF format.")
    
    if get_file_size_mb(file) > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds {MAX_FILE_SIZE_MB}MB limit.")
        
    return True

def generate_unique_filename(original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1]
    unique_id = str(uuid.uuid4())
    return f"{unique_id}_{original_filename}"

def save_upload_file(file: UploadFile) -> str:
    # 1. Validate the file is a PDF and <= 10MB
    validate_pdf(file)
    
    # 2. Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # 3. Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # 4. Save to disk
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    return file_path
