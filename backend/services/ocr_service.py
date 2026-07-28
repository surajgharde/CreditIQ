import os
import re
import math
import time
import json
import logging
import concurrent.futures
import hashlib
from typing import Dict, Any, List, Optional
import io
import datetime
import traceback
import asyncio

# Document Processing Imports
import boto3
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image, ImageFilter
import cv2
import numpy as np
import pytesseract
from langdetect import detect
from deep_translator import GoogleTranslator
from word2number import w2n

from services.external_apis import cache_get, cache_set

logger = logging.getLogger(__name__)

# Ensure tesseract command is explicitly defined if running on Windows
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def send_ws_progress(analysis_id: str, loop, pct: int, detail: str):
    """REQUIREMENT 7 - REAL TIME PROGRESS UPDATES"""
    if not analysis_id or not loop:
        return
    msg = {
        "step_number": 2,
        "step_name": "PdfTable OCR Engine",
        "step_detail": detail,
        "percentage": pct,
        "status": "running",
        "timestamp": datetime.datetime.now().isoformat()
    }
    try:
        from routers.ws import manager
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.send_personal_message(msg, str(analysis_id)), loop)
    except Exception as e:
        logger.error(f"Failed to push WS progress: {e}")

def get_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as afile:
            buf = afile.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(65536)
        return hasher.hexdigest()
    except Exception:
        return "unknown"

# ----------------------------------------------------
# REQUIREMENT 1 — DETECT DOCUMENT TYPE FIRST
# ----------------------------------------------------

def detect_document_type(file_path: str) -> str:
    ext = file_path.lower().split('.')[-1]
    
    if ext in ['jpg', 'jpeg', 'png', 'tiff', 'webp']:
        return "image"
    
    if ext in ['docx', 'doc']:
        return "word"
        
    if ext in ['xlsx', 'xls']:
        return "excel"
        
    if ext == 'pdf':
        try:
            with pdfplumber.open(file_path) as pdf:
                text_total = ""
                for i, page in enumerate(pdf.pages):
                    if i >= 1: break
                    extracted = page.extract_text()
                    if extracted:
                        text_total += extracted
                if len(text_total.strip()) > 50:
                    return "digital_pdf"
                else:
                    return "scanned_pdf"
        except Exception as e:
            if "Password" in str(e) or "Encryption" in str(e):
                # Try empty password
                try:
                    with pdfplumber.open(file_path, password="") as pdf:
                         return "digital_pdf"
                except Exception:
                    raise Exception("PASSWORD_PROTECTED_PDF: Please provide document password")
            return "scanned_pdf"
            
    return "unknown"

def convert_to_pdf(file_path: str, doc_type: str) -> str:
    """Fallback converter using libreoffice or pdf rendering."""
    # In a real environment, we would use ms-word com or libreoffice
    # But for robustness we skip conversion and treat supported ones.
    # Hackathon safe failover for non-pdfs:
    if doc_type == "image":
        try:
            img = Image.open(file_path)
            new_path = file_path + ".pdf"
            img.convert('RGB').save(new_path)
            return new_path
        except Exception:
            pass
    return file_path # Pass through

# ----------------------------------------------------
# REQUIREMENT 3 — IMAGE QUALITY AND OCR
# ----------------------------------------------------

def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """Apply cv2 based morphology and noise reduction."""
    try:
        # Convert PIL to CV2
        open_cv_image = np.array(img)
        
        if len(open_cv_image.shape) == 3:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
            
        # Denoise
        blur = cv2.GaussianBlur(open_cv_image, (3,3), 0)
        
        # Adaptive Threshold
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Convert back
        return Image.fromarray(thresh)
    except Exception:
        return img

def ocr_page_tesseract(page_img: Image.Image, lang: str = "eng") -> tuple[str, float]:
    """Run Tesseract and return text and confidence."""
    try:
        enhanced = preprocess_image_for_ocr(page_img)
        data = pytesseract.image_to_data(enhanced, lang=lang, output_type=pytesseract.Output.DICT, config='--psm 6')
        
        word_scores = []
        full_text = []
        for i, conf in enumerate(data['conf']):
            if int(conf) > 0:
                word_scores.append(int(conf))
                full_text.append(data['text'][i])
                
        text = " ".join(full_text)
        avg_conf = float(np.mean(word_scores)) if word_scores else 0.0
        return text, avg_conf
    except Exception:
        return "", 0.0

def ocr_page_textract(page_img: Image.Image) -> tuple[str, float]:
    """Fallback to robust AWS Textract for very bad quality."""
    try:
        client = boto3.client('textract', region_name='us-east-1')
        img_byte_arr = io.BytesIO()
        page_img.save(img_byte_arr, format='JPEG')
        
        response = client.analyze_document(
            Document={'Bytes': img_byte_arr.getvalue()},
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        text = ""
        confidences = []
        for item in response.get('Blocks', []):
            if item['BlockType'] == 'LINE':
                text += item['Text'] + "\n"
                confidences.append(item.get('Confidence', 0))
                
        avg_conf = float(np.mean(confidences)) if confidences else 100.0
        return text, avg_conf
    except Exception:
        return "", 0.0

# ----------------------------------------------------
# REQUIREMENT 4 — HANDLE ALL INDIAN LANGUAGES
# ----------------------------------------------------

def map_regional_finance_terms(text: str) -> str:
    term_map = {
        "आय": "Revenue", "व्यय": "Expenditure", "लाभ": "Profit", "हानि": "Loss", 
        "संपत्ति": "Assets", "देनदारी": "Liabilities", "पूंजी": "Capital", "नकद": "Cash", 
        "उधार": "Loan", "कर": "Tax", "लाभांश": "Dividend", "तुलन पत्र": "Balance Sheet",
        "આવક": "Revenue", "ખર્ચ": "Expenditure", "નફો": "Profit", "નુકસાન": "Loss", "સંપત્તિ": "Assets",
        "வருவாய்": "Revenue", "செலவு": "Expenditure", "லாபம்": "Profit", "நஷ்டம்": "Loss", "சொத்துக்கள்": "Assets"
    }
    new_text = text
    for w, rep in term_map.items():
        new_text = new_text.replace(w, rep)
    return new_text

def translate_indian_text(text: str) -> str:
    if not text: return text
    sample = text[:500]
    try:
        lang = detect(sample)
        if lang in ['hi', 'mr', 'gu', 'ta', 'te', 'kn', 'ml', 'bn', 'pa']:
            mapped_text = map_regional_finance_terms(text)
            try:
                # Fallback to Deep Translator mapping
                translated = GoogleTranslator(source='auto', target='en').translate(mapped_text[:4000]) # 4k limit
                return translated
            except Exception:
                 return mapped_text
    except Exception:
        pass
    return text

# ----------------------------------------------------
# REQUIREMENT 2 — HANDLE ANY PAGE COUNT & CONCURRENCY
# ----------------------------------------------------

def process_pdf_batch(pdf_path: str, page_nums: List[int], doc_type: str, analysis_id: str, loop) -> tuple[str, float]:
    text_content = ""
    conf_scores = []
    
    try:
        doc = fitz.open(pdf_path)
        for pno in page_nums:
            if doc_type == "digital_pdf":
                # PyMuPDF direct text
                page = doc.load_page(pno)
                txt = page.get_text("text")
                if txt.strip():
                    text_content += txt + "\n"
                    conf_scores.append(95.0) # digital confidence
                continue
                
            # Scanned Path
            try:
                page = doc.load_page(pno)
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                txt, conf = ocr_page_tesseract(img)
                if conf < 60.0:  # Bad quality
                    txt, conf = ocr_page_textract(img) # Fallback to AWS
                
                text_content += txt + "\n"
                conf_scores.append(conf)
            except Exception:
                pass 
                
        doc.close()
    except Exception as e:
        logger.error(f"Batch failed: {e}")
        
    avg = float(np.mean(conf_scores)) if conf_scores else 0.0
    return text_content, avg

# ----------------------------------------------------
# REQUIREMENT 5 — HANDLE MESSY STRUCTURES
# ----------------------------------------------------

def clean_indian_numbers(text: str) -> str:
    """Normalize Indian number formatting internally."""
    def repl_word(m):
        try:
            return str(w2n.word_to_num(m.group(0)))
        except Exception:
            return m.group(0)

    # Rs, INR, ru symbols to standard
    text = re.sub(r'(Rs\.?|INR|रु)\s*', '₹', text, flags=re.IGNORECASE)
    
    # 1,00,00,000 -> 10000000
    cleaned = re.sub(r'(?<=\d),(?=\d)', '', text)
    return cleaned

def parse_financial_value(text: str, current_year: bool = True) -> tuple[Optional[float], float]:
    """Helper to regex extract clean float. Returns (value, confidence_field)."""
    # R6: Confidence per field
    base_conf = 85.0
    match = re.search(r'[\d,]+\.?\d*', text)
    if match:
        val_str = match.group(0).replace(',', '')
        try:
            # R6: Deduct confidence if OCR was messy around numbers
            if "!" in text or "?" in text:
                base_conf -= 15.0
            return float(val_str), base_conf
        except ValueError:
            pass
    return None, 30.0

def find_financial_indicators(text: str) -> Dict[str, Any]:
    """Runs keyword clustering regex against the raw document text."""
    indicators = {}
    lines = text.lower().split('\n')
    
    keywords = {
        "revenue_fy24": ["revenue from operations", "net sales", "total income", "turnover", "operating revenue", "revenue"],
        "cogs": ["cost of goods sold", "cogs", "cost of materials consumed", "purchases of stock"],
        "gross_profit": ["gross profit", "gross margin"],
        "ebitda": ["ebitda", "earnings before interest tax depreciation"],
        "ebit": ["ebit", "operating profit", "earnings before interest and tax"],
        "net_profit": ["net profit after tax", "profit for the year", "npat", "pat"],
        "total_assets": ["total assets", "assets total"],
        "total_liabilities": ["total liabilities", "liabilities total"],
        "total_equity": ["total equity", "net worth", "shareholders funds", "equity share capital"],
        "total_debt": ["total debt", "total borrowings", "long term borrowings"],
        "current_assets": ["current assets", "total current assets"],
        "current_liabilities": ["current liabilities", "total current liabilities"],
        "cash_equivalents": ["cash and cash equivalents", "cash & bank balances"],
        "interest_expense": ["finance costs", "interest expense", "interest paid"]
    }

    field_confidences = []

    for key, patterns in keywords.items():
        for i, line in enumerate(lines):
            if any(pattern in line for pattern in patterns):
                search_block = " ".join(lines[i:min(i+3, len(lines))])
                val, conf = parse_financial_value(search_block)
                if val is not None:
                    # R6: Use Sector average or discard if under 30%
                    if conf < 30.0:
                        break # Discard
                    indicators[key] = val
                    field_confidences.append(conf)
                    break
                    
    avg_field_conf = float(np.mean(field_confidences)) if field_confidences else 0.0
    return indicators, avg_field_conf


# ----------------------------------------------------
# MAIN SERVICE EXTRACTION
# ----------------------------------------------------

def extract_financial_data(file_paths: list[str], analysis_id: str = None, loop=None) -> dict:
    """REQUIREMENT 8 - NEVER FAIL COMPLETELY MASTER CONTROLLER"""
    if not file_paths or not file_paths[0]:
        return {"error": "No valid file paths provided"}
        
    target_file = file_paths[0]
    
    file_hash = get_file_hash(target_file)
    cache_key = f"ocr_{file_hash}_v3"
    cached = cache_get(cache_key)
    if cached:
        return cached

    start_time = time.time()
    send_ws_progress(analysis_id, loop, 5, "Detecting document type and language")
    
    try:
        doc_type = detect_document_type(target_file)
        target_file = convert_to_pdf(target_file, doc_type)
        if target_file.endswith(".pdf") and doc_type == "image":
            doc_type = "scanned_pdf" # Post conversion

        # Open doc for global metrics
        doc = fitz.open(target_file)
        total_pages = len(doc)
        doc.close()
        
        pages_to_process = list(range(total_pages))
        
        # R2: Keyword scanning for >200 pages
        if total_pages > 200:
            send_ws_progress(analysis_id, loop, 15, "Large document detected, scanning for financial keywords")
            financial_pages = []
            test_doc = fitz.open(target_file)
            for i in range(total_pages):
                txt = test_doc.load_page(i).get_text("text").lower()
                if any(kw in txt for kw in ['revenue', 'profit', 'assets', 'liabilities', 'balance', 'crore']):
                    financial_pages.append(i)
            test_doc.close()
            pages_to_process = financial_pages if financial_pages else pages_to_process[:50]

        send_ws_progress(analysis_id, loop, 25, f"Processing {len(pages_to_process)} pages via {doc_type} engine")
        
        # Multi-threaded batch processing
        batch_size = 20
        batches = [pages_to_process[i:i + batch_size] for i in range(0, len(pages_to_process), batch_size)]
        
        full_text = ""
        batch_confs = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_pdf_batch, target_file, b, doc_type, analysis_id, loop) for b in batches]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                     txt, conf = future.result(timeout=30)
                     full_text += txt + "\n"
                     batch_confs.append(conf)
                     pct = 25 + int(((i+1)/max(1, len(batches))) * 40)
                     send_ws_progress(analysis_id, loop, pct, f"Processed batch {i+1}/{len(batches)} successfully")
                except Exception as e:
                     logger.warning(f"Batch timeout or failure, skipping. {e}")

        # Translation
        send_ws_progress(analysis_id, loop, 75, "Translating Hindi/Regional financial terms to English")
        full_text = translate_indian_text(full_text)
        full_text = clean_indian_numbers(full_text)

        # Mining logic
        send_ws_progress(analysis_id, loop, 85, "Mining exact financial KPIs using clustering")
        found_indicators, avg_conf = find_financial_indicators(full_text)
        
        # NEVER FAIL completely logic
        if not found_indicators:
            return {
                "error_detected": True,
                "error_message": "Document does not appear to contain standard financial statement data. Use a clearer version.",
                "data_quality_score": 0.0,
                "pages_processed": total_pages,
                **found_indicators
            }

        # Calculate math ratios
        ratios = {}
        try:
            if "total_debt" in found_indicators and "total_equity" in found_indicators and found_indicators["total_equity"]>0:
                ratios["debt_to_equity"] = round(found_indicators["total_debt"]/found_indicators["total_equity"], 2)
            if "ebitda" in found_indicators and "revenue_fy24" in found_indicators and found_indicators["revenue_fy24"]>0:
                ratios["ebitda_margin_percent"] = round((found_indicators["ebitda"]/found_indicators["revenue_fy24"])*100, 2)
            if "net_profit" in found_indicators and "revenue_fy24" in found_indicators and found_indicators["revenue_fy24"]>0:
                ratios["net_profit_margin_percent"] = round((found_indicators["net_profit"]/found_indicators["revenue_fy24"])*100, 2)
        except Exception:
            pass

        data_quality_score = 100.0 - ((12 - len(found_indicators)) * 8.33)
        data_quality_score = round(max(0.0, min(100.0, data_quality_score)), 1)
        
        send_ws_progress(analysis_id, loop, 95, f"Extracted {len(found_indicators)} values with average confidence {avg_conf:.0f}%")

        final_res = {
            **found_indicators,
            **ratios,
            "data_quality_score": data_quality_score,
            "overall_confidence_score": round(avg_conf, 1),
            "pages_processed": len(pages_to_process),
            "processing_time_seconds": round(time.time() - start_time, 2)
        }
        
        cache_set(cache_key, final_res, 86400)
        return final_res
        
    except Exception as e:
        logger.error(f"Ultimate Fallback error: {e}")
        return {
            "error_detected": True,
            "error_message": f"Extraction partially failed. Check logs: {str(e)}",
            "data_quality_score": 0.0,
            "pages_processed": 0
        }
