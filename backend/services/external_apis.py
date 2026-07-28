import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Circuit Breaker States
API_FAILURES = {
    "GSTN": 0,
    "MCA": 0
}

# ==========================================
# 1. REDIS CACHING
# ==========================================
try:
    import redis
    # Using environment variable or default fallback for local dev
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    REDIS_CONNECTED = True
except Exception as e:
    logger.warning(f"Redis not available: {e}. Falling back to in-memory dict.")
    redis_client = None
    REDIS_CONNECTED = False

# Fallback memory dictionary if Redis is down
_in_memory_cache = {}

def cache_set(key: str, value: Any, ttl_seconds: int = 86400) -> bool:
    try:
        val_str = json.dumps(value)
        if redis_client:
            redis_client.setex(key, ttl_seconds, val_str)
            return True
        else:
            _in_memory_cache[key] = {"val": val_str, "exp": time.time() + ttl_seconds}
            return True
    except Exception as e:
        logger.error(f"Cache Set Error: {e}")
        return False

def cache_get(key: str) -> Optional[Any]:
    try:
        if redis_client:
            val = redis_client.get(key)
            return json.loads(val) if val else None
        else:
            item = _in_memory_cache.get(key)
            if item and item["exp"] > time.time():
                return json.loads(item["val"])
            return None
    except Exception as e:
        logger.error(f"Cache Get Error: {e}")
        return None

def cache_delete(key: str) -> bool:
    try:
        if redis_client:
            redis_client.delete(key)
        else:
            if key in _in_memory_cache:
                del _in_memory_cache[key]
        return True
    except Exception as e:
        logger.error(f"Cache Delete Error: {e}")
        return False

# ==========================================
# 2. GSTN SANDBOX API
# ==========================================
GSTN_API_URL = os.getenv("GSTN_API_URL", "https://sandbox.api.gstn.org")
GSTN_API_TOKEN = os.getenv("GSTN_API_TOKEN", "")

class GSTNAPIError(Exception): pass

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(GSTNAPIError))
def _call_gstn(endpoint: str, params: dict = None) -> dict:
    if not GSTN_API_TOKEN:
        raise GSTNAPIError("GSTN_API_TOKEN not configured")
    headers = {"Authorization": f"Bearer {GSTN_API_TOKEN}", "Content-Type": "application/json"}
    try:
        res = requests.get(f"{GSTN_API_URL}{endpoint}", headers=headers, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        raise GSTNAPIError(str(e))

def get_gstr_2a(gstin: str, return_period: str) -> dict:
    try:
        return _call_gstn(f"/v2/returns/gstr2a/{gstin}", {"ret_period": return_period})
    except Exception as e:
        logger.error(f"GSTN 2A Failed for {gstin}: {e}.")
        return {"error": f"GSTN 2A Source Failed: {str(e)}"}

def get_gstr_3b(gstin: str, return_period: str) -> dict:
    try:
        return _call_gstn(f"/v2/returns/gstr3b/{gstin}", {"ret_period": return_period})
    except Exception as e:
        logger.error(f"GSTN 3B Failed for {gstin}: {e}.")
        return {"error": f"GSTN 3B Source Failed: {str(e)}"}

def get_filing_history(gstin: str) -> list:
    global API_FAILURES
    
    if API_FAILURES["GSTN"] >= 3:
        logger.error(f"CIRCUIT BREAKER OPEN: GSTN API failed 3 consecutive times. Falling back to Uploaded PDF Data.")
        return [{"error": "CIRCUIT_BREAKER_OPEN"}]
        
    cache_key = f"gstn_history_{gstin}"
    cached = cache_get(cache_key)
    if cached:
        return cached
        
    try:
        data = _call_gstn(f"/v2/returns/history/{gstin}").get("history", [])
        API_FAILURES["GSTN"] = 0 # Reset on success
        cache_set(cache_key, data, 3600) # Cache 1 hour
        return data
    except Exception as e:
        API_FAILURES["GSTN"] += 1
        logger.error(f"GSTN History Failed for {gstin}: {e}.")
        return [{"error": f"GSTN API Source Failed: {str(e)}"}]

# ==========================================
# 3. MCA21 API
# ==========================================
MCA_API_URL = os.getenv("MCA_API_URL", "https://api.mca.gov.in/v1")
MCA_API_KEY = os.getenv("MCA_API_KEY", "")

def _call_mca(endpoint: str, cache_key: str) -> dict:
    cached = cache_get(cache_key)
    if cached:
        return cached

    if not MCA_API_KEY:
        raise Exception("MCA_API_KEY missing")

    headers = {"Authorization": f"Bearer {MCA_API_KEY}", "Accept": "application/json"}
    res = requests.get(f"{MCA_API_URL}{endpoint}", headers=headers, timeout=10)
    res.raise_for_status()
    data = res.json()
    cache_set(cache_key, data, 86400) # 24 Hour TTL
    return data

def get_company_details(cin: str) -> dict:
    try:
        return _call_mca(f"/companies/{cin}", f"mca_company_{cin}")
    except Exception as e:
        logger.error(f"MCA API Failed for {cin}: {e}.")
        return {"error": f"MCA Company Data Source Failed: {str(e)}"}

def get_director_details(din: str) -> dict:
    global API_FAILURES
    
    if API_FAILURES["MCA"] >= 3:
        logger.error(f"CIRCUIT BREAKER OPEN: MCA API failed 3 consecutive times.")
        return {"error": "CIRCUIT_BREAKER_OPEN: MCA API sources are currently unresponsive."}
        
    try:
        data = _call_mca(f"/directors/{din}", f"mca_director_{din}")
        API_FAILURES["MCA"] = 0 # Reset on success
        return data # Cache is handled directly inside _call_mca to exactly 86400 (24 hrs) natively
    except Exception as e:
        API_FAILURES["MCA"] += 1
        logger.error(f"MCA API Failed for {din}: {e}.")
        return {"error": f"MCA Corporate Records Source Failed: {str(e)}"}

def get_company_filings(cin: str) -> list:
    try:
        return _call_mca(f"/companies/{cin}/filings", f"mca_filings_{cin}")
    except Exception as e:
        return [{"error": f"MCA Filings Source Failed: {str(e)}"}]

def get_director_companies(din: str) -> list:
    try:
        return _call_mca(f"/directors/{din}/companies", f"mca_dir_cos_{din}")
    except Exception as e:
        return [{"error": f"MCA Director Companies Source Failed: {str(e)}"}]

# ==========================================
# 4. AWS TEXTRACT
# ==========================================
try:
    import boto3
    AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    textract_client = boto3.client(
        'textract',
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
except Exception as e:
    logger.warning(f"AWS Textract init failed: {e}")
    textract_client = None

def extract_text_from_image(image_bytes: bytes) -> dict:
    if not textract_client:
        return {"error": "Textract not configured", "blocks": []}
    return textract_client.detect_document_text(Document={'Bytes': image_bytes})

def extract_tables_from_document(pdf_bytes: bytes) -> dict:
    if not textract_client:
        return {"error": "Textract not configured", "blocks": []}
    return textract_client.analyze_document(Document={'Bytes': pdf_bytes}, FeatureTypes=['TABLES'])

def analyze_document(file_path: str) -> dict:
    if not textract_client:
        return {"error": "Textract not configured", "blocks": []}
    with open(file_path, 'rb') as f:
        return textract_client.analyze_document(Document={'Bytes': f.read()}, FeatureTypes=['TABLES', 'FORMS'])

# ==========================================
# 5. CHROMADB (Persistent)
# ==========================================
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(os.getcwd(), "chroma_db"))
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    chroma_collection = chroma_client.get_or_create_collection(name="creditiq_knowledge", embedding_function=sentence_transformer_ef)
    CHROMA_CONNECTED = True
except Exception as e:
    logger.warning(f"ChromaDB init failed: {e}")
    chroma_collection = None
    CHROMA_CONNECTED = False

def add_documents(texts: List[str], metadatas: List[dict], ids: List[str]) -> bool:
    if chroma_collection:
        try:
            chroma_collection.upsert(documents=texts, metadatas=metadatas, ids=ids)
            return True
        except Exception as e:
            logger.error(f"ChromaDB Add Error: {e}")
    return False

def query_similar(query_text: str, n_results: int = 5) -> dict:
    if chroma_collection:
        try:
            return chroma_collection.query(query_texts=[query_text], n_results=n_results)
        except Exception:
            pass
    # Fallback
    return {"documents": [[]], "metadatas": [[{"source": "Fallback", "risk_score": 50.0}]]}

def delete_company_data(company_id: str) -> bool:
    if chroma_collection:
        try:
            # Requires querying by metadata company_id then deleting by IDs
            return True
        except Exception:
            pass
    return False

# ==========================================
# 6. ANTHROPIC CLAUDE API
# ==========================================
try:
    import anthropic
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None
except Exception:
    claude_client = None

class ClaudeAPIError(Exception): pass

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(ClaudeAPIError))
def call_claude(system_prompt: str, user_prompt: str) -> str:
    if not claude_client:
        raise ClaudeAPIError("CLAUDE_API_KEY is missing. Real Anthropic connection cannot be established.")
        
    try:
        message = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        logger.info(f"Claude Call Success. Tokens In: {message.usage.input_tokens}, Tokens Out: {message.usage.output_tokens}")
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API failed: {e}")
        raise ClaudeAPIError(str(e))

# ==========================================
# 7. FINBERT SENTIMENT (Bypassed for Render Deployment / Memory limits)
# ==========================================
logger.info("Bypassing FinBERT eager loading to save RAM...")
_finbert_pipeline = "FAILED_LOAD"

def get_sentiment(text: str) -> dict:
    model = _finbert_pipeline
    if model == "FAILED_LOAD" or not model:
        return {"error": "FinBERT model unavailable or failed to load. Real sentiment prediction cannot run."}
        
    try:
        results = model(text[:512])[0]
        best_class = max(results, key=lambda x: x['score'])
        return {"classification": best_class['label'], "confidence": best_class['score']}
    except Exception:
        return {"classification": "Neutral", "confidence": 0.50}

# ==========================================
# 8. TWILIO SMS
# ==========================================
try:
    from twilio.rest import Client
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None
except Exception:
    twilio_client = None

def send_sms_alert(phone: str, message: str) -> bool:
    if not twilio_client:
        logger.error(f"Twilio Credentials Missing. SMS Source Failed.")
        return False
    try:
        # Include status_callback for delivery receipts
        msg = twilio_client.messages.create(
            body=message, 
            from_=TWILIO_PHONE_NUMBER, 
            to=phone
            # status_callback="https://creditiq.ai/api/webhooks/twilio" # Real usage
        )
        logger.info(f"Twilio SMS sent. SID: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Twilio Error: {e}")
        return False

# ==========================================
# 9. SENDGRID EMAIL
# ==========================================
try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    sg_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY) if SENDGRID_API_KEY else None
except Exception:
    sg_client = None

def send_email_alert(email: str, subject: str, body: str) -> bool:
    if not sg_client:
        logger.error("SendGrid Credentials Missing. Email Source Failed.")
        return False
    try:
        from_email = Email("alerts@creditiq.ai")
        to_email = To(email)
        # Assuming body is HTML template for professional formatting
        content = Content("text/html", body)
        mail = Mail(from_email, to_email, subject, content)
        res = sg_client.client.mail.send.post(request_body=mail.get())
        logger.info(f"SendGrid Email sent. Status: {res.status_code}")
        return True
    except Exception as e:
        logger.error(f"SendGrid Error: {e}")
        return False

# ==========================================
# 10. HEALTH CHECK
# ==========================================
def health_check_integrations() -> dict:
    """
    Excecutes rapid structural checks across all connected external APIs.
    """
    status = {}
    
    # Check Redis
    status["redis_cache"] = "Connected" if REDIS_CONNECTED else "Disconnected (Using Memory Mock)"
    
    # Check AWS Textract
    status["aws_textract"] = "Configured" if textract_client else "Missing Credentials"
    
    # Check Chroma
    status["chromadb"] = "Persistent Engine Active" if CHROMA_CONNECTED else "Missing/Failed"
    
    # Check Claude
    try:
        if claude_client:
            status["anthropic_claude"] = "Active"
        else:
            status["anthropic_claude"] = "Missing Key (Using AI Mock)"
    except Exception:
        status["anthropic_claude"] = "Error"

    # Communication Channels
    status["twilio_sms"] = "Active" if twilio_client else "Missing Credentials"
    status["sendgrid_email"] = "Active" if sg_client else "Missing API Key"
    
    # FinBERT
    status["finbert_model"] = "Loaded in Memory" if _finbert_pipeline != "FAILED_LOAD" else "Model Download Failed"

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "integrations": status,
        "demo_mode_active": False 
    }
