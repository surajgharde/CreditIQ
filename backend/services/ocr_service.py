import re
import os
import shutil
import time
import logging
import concurrent.futures
import hashlib
from typing import Dict, Any, List, Optional
import io
import datetime
import asyncio

# Document Processing Imports
import boto3
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import cv2
import numpy as np
import pytesseract
from langdetect import detect
from deep_translator import GoogleTranslator
from word2number import w2n

from services.external_apis import cache_get, cache_set

logger = logging.getLogger(__name__)

def _locate_tesseract() -> str | None:
    """
    Finds the Tesseract binary and points pytesseract at it.

    The Windows installer does not add itself to PATH, so relying on PATH alone
    leaves scanned-PDF OCR silently dead. Order: TESSERACT_CMD, then PATH, then
    the usual install locations.
    """
    explicit = (os.getenv("TESSERACT_CMD") or "").strip()
    if explicit and os.path.isfile(explicit):
        pytesseract.pytesseract.tesseract_cmd = explicit
        return explicit

    on_path = shutil.which("tesseract")
    if on_path:
        pytesseract.pytesseract.tesseract_cmd = on_path
        return on_path

    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ):
        if candidate and os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate
    return None


TESSERACT_CMD = _locate_tesseract()
if TESSERACT_CMD:
    logger.info("Tesseract OCR binary: %s", TESSERACT_CMD)
else:
    logger.warning(
        "Tesseract binary not found. Scanned PDFs will fall back to AWS Textract, "
        "and fail entirely if AWS credentials are absent. Install Tesseract or set "
        "TESSERACT_CMD to its full path."
    )


def tesseract_languages() -> set:
    """Language packs installed alongside the binary."""
    if not TESSERACT_CMD:
        return set()
    try:
        return {str(lang) for lang in pytesseract.get_languages(config="")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not list Tesseract languages: %s", exc)
        return set()

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
    """
    Binarises a degraded scan. Only worth applying to genuinely poor input —
    see ocr_page_tesseract, which treats this as a fallback.
    """
    try:
        # Convert PIL to CV2
        open_cv_image = np.array(img)

        if len(open_cv_image.shape) == 3:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)

        # Denoise
        blur = cv2.GaussianBlur(open_cv_image, (3, 3), 0)

        # Adaptive threshold. The window must be wider than a glyph stroke: a
        # fixed 11px window on a 300dpi render cuts through the middle of the
        # strokes and shreds them, so scale it with the page and keep it odd.
        block = max(11, (min(open_cv_image.shape[:2]) // 40) | 1)
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 10
        )

        # Convert back
        return Image.fromarray(thresh)
    except Exception:
        return img


def _tesseract_pass(img: Image.Image, lang: str, psm: str = "--psm 6") -> tuple[str, float]:
    """
    One Tesseract run. Returns (text, mean word confidence).

    Line structure is rebuilt from Tesseract's block/paragraph/line indices.
    Joining every word with spaces collapses the page into a single line, and
    the downstream matcher works line by line — so each statement label matched
    the same whole-page "line" and every field came back with the same number.
    """
    data = pytesseract.image_to_data(
        img, lang=lang, output_type=pytesseract.Output.DICT, config=psm
    )

    word_scores = []
    lines: Dict[tuple, List[str]] = {}
    order: List[tuple] = []

    for i, raw_conf in enumerate(data["conf"]):
        conf = int(raw_conf)
        if conf <= 0:
            continue
        word = data["text"][i]
        if not word.strip():
            continue
        word_scores.append(conf)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if key not in lines:
            lines[key] = []
            order.append(key)
        lines[key].append(word)

    text = "\n".join(" ".join(lines[key]) for key in order)
    return text, (float(np.mean(word_scores)) if word_scores else 0.0)


# Above this, the first pass is good enough that a second one is wasted work.
GOOD_ENOUGH_CONFIDENCE = 75.0


def ocr_page_tesseract(page_img: Image.Image, lang: str = "eng") -> tuple[str, float]:
    """
    Runs Tesseract, returning the best (text, confidence) available.

    The page is read as-is first. Binarisation is tuned for degraded scans and
    actively harms clean ones — on a crisp balance sheet it took confidence from
    92% to 23% and produced gibberish — so it is attempted only when the direct
    read comes back poor.
    """
    best_text, best_conf = "", 0.0
    attempts = (("direct", lambda: page_img), ("binarised", lambda: preprocess_image_for_ocr(page_img)))

    for label, build in attempts:
        try:
            text, conf = _tesseract_pass(build(), lang)
            if conf > best_conf:
                best_text, best_conf = text, conf
            if best_conf >= GOOD_ENOUGH_CONFIDENCE:
                return best_text, best_conf
            logger.debug("Tesseract %s pass: confidence %.1f", label, conf)
        except Exception as e:
            # Swallowing this silently made a missing Tesseract binary look like
            # a clean run that simply found no data. Log it so the cause shows.
            logger.warning("Tesseract OCR (%s pass) failed: %s: %s", label, type(e).__name__, e)

    return best_text, best_conf

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
    except Exception as e:
        logger.warning("AWS Textract fallback failed: %s: %s", type(e).__name__, e)
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
                if conf < 60.0:  # Bad quality — try the stronger engine
                    alt_txt, alt_conf = ocr_page_textract(img)
                    # Only take the fallback when it actually returned something.
                    # Assigning unconditionally discarded usable Tesseract text
                    # whenever Textract was unreachable or unauthorised.
                    if alt_txt.strip() and alt_conf >= conf:
                        txt, conf = alt_txt, alt_conf
                
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

    # Rs, INR, ru symbols to standard. The leading  matters: without it the
    # "rs" inside ordinary words is treated as a currency token, so
    # "Shareholders Funds" became "Shareholde₹ Funds" and the label stopped
    # matching. The same applied to creditors, debtors, directors, borrowers.
    text = re.sub(r'(Rs\.?|INR|रु)\s*', '₹', text, flags=re.IGNORECASE)
    
    # 1,00,00,000 -> 10000000
    cleaned = re.sub(r'(?<=\d),(?=\d)', '', text)
    return cleaned

# Indian statements lay rows out as: Particulars | Note | Current year | Prior year.
# Taking the first number on the row therefore picks up the note reference, not
# the amount — "Revenue from operations 2 500000000" would read as 2. Candidates
# that look like note references or financial years are dropped before choosing.
NOTE_REF_CEILING = 100.0


def _numeric_candidates(text: str) -> list:
    """Numbers in the block, in reading order, as (value, had_decimal)."""
    out = []
    for raw in re.findall(r'\d[\d,]*\.?\d*', text):
        token = raw.replace(',', '').rstrip('.')
        if not token:
            continue
        try:
            out.append((float(token), '.' in raw))
        except ValueError:
            continue
    return out


def parse_financial_value(text: str, current_year: bool = True) -> tuple[Optional[float], float]:
    """
    Extracts the amount for a statement row. Returns (value, confidence_field).

    Picks the first candidate that is not a note reference or a financial year,
    which maps to the current-year column in a standard Indian layout.
    """
    base_conf = 85.0
    candidates = _numeric_candidates(text)
    if not candidates:
        return None, 30.0

    def is_note_ref(value, had_decimal):
        # Bare small integers in a statement row are note/serial references.
        return not had_decimal and value < NOTE_REF_CEILING and value == int(value)

    def is_year(value, had_decimal):
        return not had_decimal and 1900 <= value <= 2100 and value == int(value)

    amounts = [
        (v, d) for v, d in candidates
        if not is_note_ref(v, d) and not is_year(v, d)
    ]

    if not amounts:
        # Every candidate was a note reference, section number or year. Reporting
        # the largest of those as an amount is how "revenue of 2" happens, so the
        # field is left unextracted and reads downstream as "Not extracted".
        return None, 30.0

    value, _ = amounts[0]

    # R6: Deduct confidence if OCR was messy around numbers
    if "!" in text or "?" in text:
        base_conf -= 15.0
    return value, max(0.0, base_conf)

def find_financial_indicators(text: str) -> Dict[str, Any]:
    """Runs keyword clustering regex against the raw document text."""
    indicators = {}
    # Statements spell the same label several ways: "Cash & Cash Equivalents" or
    # "Cash and Cash Equivalents", "Shareholders' Funds" or "Shareholders Funds"
    # (and OCR may emit a curly apostrophe). Normalising the ampersand and
    # dropping apostrophes lets one pattern match every spelling.
    normalised = re.sub(r'\s*&\s*', ' and ', text.lower())
    normalised = re.sub(r"[‘’'`]", '', normalised)
    lines = normalised.split('\n')

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
        "cash_equivalents": ["cash and cash equivalents", "cash and bank balances"],
        "interest_expense": ["finance costs", "interest expense", "interest paid"]
    }

    field_confidences = []

    # (pattern, phrases that must NOT appear on the same line)
    EXCLUSIONS = [
        ("total equity", ("total equity and liabilities", "equity and liabilities")),
        ("total liabilities", ("total equity and liabilities",)),
    ]

    # Short acronyms must match as whole words: a plain substring test makes
    # "ebit" match inside "ebitda", so EBIT silently takes EBITDA's amount.
    # Longer multi-word phrases are matched as substrings, which is safe.
    def matches(line: str, pattern: str) -> bool:
        if len(pattern) <= 5 and " " not in pattern:
            return re.search(r'' + re.escape(pattern) + r'', line) is not None
        # "current assets" and "current liabilities" are substrings of their own
        # "non-current" counterparts, so a plain test matches the wrong section
        # header and reads its section number as the amount.
        if pattern.startswith("current "):
            return re.search(r'(?<!non-)(?<!non )' + re.escape(pattern), line) is not None
        # Likewise "total equity" appears inside the balancing total "TOTAL
        # EQUITY AND LIABILITIES", which is the whole balance sheet rather than
        # shareholders' funds — matching it overstates net worth badly.
        for phrase, forbidden in EXCLUSIONS:
            if pattern == phrase and any(bad in line for bad in forbidden):
                return False
        return pattern in line

    # Keys that name a total rather than a component. A statement writes the
    # section header ("Shareholders' Funds") above the figure and the total
    # ("Total Shareholders' Funds 797.47") below it, so taking the first match
    # reads the header and then picks up the first component beneath it — 485.00
    # share capital instead of 797.47 net worth. Lines labelled "total" win.
    # Revenue is deliberately absent: "Revenue from Operations" is the wanted
    # line and "Total Income" is a different figure (it adds other income), so
    # preferring the "total" line there would read the wrong number.
    TOTAL_KEYS = {
        "total_assets", "total_liabilities", "total_equity", "total_debt",
        "current_assets", "current_liabilities",
    }

    for key, patterns in keywords.items():
        candidates = [
            i for i, line in enumerate(lines)
            if any(matches(line, pattern) for pattern in patterns)
        ]
        if key in TOTAL_KEYS:
            # Stable sort: "total" lines first, original order preserved within
            # each group.
            candidates.sort(key=lambda i: 0 if "total" in lines[i] else 1)

        for i in candidates:
            line = lines[i]
            # Search the label's own line first; only spill into following
            # lines when the amount is not on it (wrapped table rows).
            val, conf = parse_financial_value(line)
            if val is None:
                search_block = " ".join(lines[i:min(i + 3, len(lines))])
                val, conf = parse_financial_value(search_block)
            if val is not None:
                if conf < 30.0:
                    break  # Too doubtful to record
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
                "error_message": (
                    "No financial statement lines were recognised in the document. "
                    "If it is a scan, check the OCR engines: Tesseract must be installed "
                    "and on PATH, or AWS credentials must be valid for the Textract "
                    "fallback. Otherwise supply a clearer copy."
                ),
                "data_quality_score": 0.0,
                "pages_processed": total_pages,
                **found_indicators
            }

        # Calculate math ratios.
        # Only ratios whose inputs were actually extracted are emitted — a missing
        # key here is read downstream as "not supplied" rather than defaulted, so
        # never insert a placeholder value.
        ratios = {}
        try:
            fi = found_indicators
            if fi.get("total_equity", 0) > 0 and "total_debt" in fi:
                ratios["debt_to_equity"] = round(fi["total_debt"] / fi["total_equity"], 2)
            if fi.get("revenue_fy24", 0) > 0 and "ebitda" in fi:
                ratios["ebitda_margin_percent"] = round((fi["ebitda"] / fi["revenue_fy24"]) * 100, 2)
            if fi.get("revenue_fy24", 0) > 0 and "net_profit" in fi:
                ratios["net_profit_margin_percent"] = round((fi["net_profit"] / fi["revenue_fy24"]) * 100, 2)
            # Liquidity: consumed by the XGBoost feature vector and the CAM ratio table.
            if fi.get("current_liabilities", 0) > 0 and "current_assets" in fi:
                ratios["current_ratio"] = round(fi["current_assets"] / fi["current_liabilities"], 2)
            # Interest cover: prefer EBIT, fall back to EBITDA when EBIT was not found.
            if fi.get("interest_expense", 0) > 0:
                earnings = fi.get("ebit", fi.get("ebitda"))
                if earnings is not None:
                    ratios["interest_coverage"] = round(earnings / fi["interest_expense"], 2)
            if fi.get("revenue_fy24", 0) > 0 and "gross_profit" in fi:
                ratios["gross_profit_margin_percent"] = round((fi["gross_profit"] / fi["revenue_fy24"]) * 100, 2)
            # Leverage: total outside liabilities to tangible net worth.
            if fi.get("total_equity", 0) > 0 and "total_liabilities" in fi:
                ratios["tol_tnw"] = round(fi["total_liabilities"] / fi["total_equity"], 2)
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
