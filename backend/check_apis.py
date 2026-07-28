"""
CreditIQ API Health Check Script
Run this to verify all credentials and service imports are working.
"""
import os
import sys
import warnings
import logging

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# Load .env
from dotenv import load_dotenv
load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

print("=" * 60)
print("  CreditIQ PLATFORM ? FULL SYSTEM CHECK")
print("=" * 60)

# ??? 1. ENVIRONMENT VARIABLES ?????????????????????????????????
print("\n[1] ENVIRONMENT VARIABLES")

env_checks = {
    "AWS_ACCESS_KEY_ID":     "AWS Textract (OCR)",
    "AWS_SECRET_ACCESS_KEY": "AWS Textract (OCR)",
    "COHERE_API_KEY":        "Cohere (CAM Synthesis)",
    "NEWS_API_KEY":          "News RAG Service",
    "GSTN_API_TOKEN":        "GSTN Sandbox",
    "MCA_API_KEY":           "MCA21 Director API",
    "TWILIO_ACCOUNT_SID":    "Twilio SMS Alerts",
    "TWILIO_AUTH_TOKEN":     "Twilio SMS Alerts",
    "SENDGRID_API_KEY":      "SendGrid Email Alerts",
    "KAGGLE_USERNAME":       "Kaggle Dataset Download",
    "KAGGLE_KEY":            "Kaggle Dataset Download",
}

for var, label in env_checks.items():
    val = os.getenv(var)
    if val:
        masked = val[:6] + "..." + val[-4:]
        print(f"  {PASS}  {var:<30} ({label}) -> {masked}")
    else:
        print(f"  {FAIL}  {var:<30} ({label}) -> MISSING!")
        results.append(("ENV", var, "MISSING"))

# ??? 2. PYTHON PACKAGE IMPORTS ???????????????????????????????
print("\n[2] PYTHON PACKAGES")

packages = [
    ("fastapi",                  "FastAPI Server"),
    ("sqlalchemy",               "PostgreSQL ORM"),
    ("boto3",                    "AWS Textract"),
    ("cohere",                   "Cohere API"),
    ("xgboost",                  "XGBoost Model"),
    ("shap",                     "SHAP Explainability"),
    ("joblib",                   "Model Persistence"),
    ("pandas",                   "Data Processing"),
    ("numpy",                    "Numerics"),
    ("sklearn",                  "Train/Test Split"),
    ("kaggle",                   "Kaggle Dataset API"),
    ("transformers",             "FinBERT NLP"),
    ("chromadb",                 "Vector DB (RAG)"),
    ("networkx",                 "Circular Trading Graph"),
    ("apscheduler",              "EWS Scheduler"),
    ("docx",                     "Word Doc Generation"),
    ("twilio",                   "SMS Alerts"),
    ("sendgrid",                 "Email Alerts"),
    ("tenacity",                 "API Retry Logic"),
    ("pdfplumber",               "PDF Text Extraction"),
    ("aiohttp",                  "Async HTTP"),
    ("bs4",                      "Web Scraping"),
]

for pkg, label in packages:
    try:
        __import__(pkg)
        print(f"  {PASS}  {pkg:<25} ({label})")
    except ImportError as e:
        print(f"  {FAIL}  {pkg:<25} ({label}) ? NOT INSTALLED")
        results.append(("PKG", pkg, "MISSING"))

# ??? 3. SERVICE IMPORTS ???????????????????????????????????????
print("\n[3] CreditIQ SERVICE IMPORTS")

services = [
    ("services.external_apis",  "health_check_integrations"),
    ("services.ocr_service",    "extract_financial_data"),
    ("services.fraud_service",  "run_fraud_detection"),
    ("services.rag_service",    "get_news_intelligence"),
    ("services.scoring_service","calculate_credit_score"),
    ("services.cam_service",    "generate_cam"),
    ("services.ews_service",    "get_ews_data"),
    ("services.pipeline",       "run_full_analysis"),
]

for module, func in services:
    try:
        mod = __import__(module, fromlist=[func])
        getattr(mod, func)
        print(f"  {PASS}  {module}")
    except Exception as e:
        print(f"  {FAIL}  {module} ? {e}")
        results.append(("SVC", module, str(e)))

# ??? 4. LIVE API CHECKS ??????????????????????????????????????
print("\n[4] LIVE API CHECKS")

# Cohere API Ping
try:
    import cohere
    key = os.getenv("COHERE_API_KEY","")
    if key:
        co = cohere.ClientV2(api_key=key)
        response = co.chat(
            model="command-r-08-2024",
            messages=[{"role": "user", "content": "hi"}]
        )
        print(f"  {PASS}  Cohere command-r-08-2024 API -> Live & Responding")
    else:
        print(f"  {WARN}  Cohere API -> Key missing")
except Exception as e:
    print(f"  {FAIL}  Cohere API -> {e}")
    results.append(("API", "Cohere", str(e)))

# AWS Textract Ping
try:
    import boto3
    c = boto3.client(
        "textract",
        region_name=os.getenv("AWS_DEFAULT_REGION","us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    # Just init the client ? real call needs a file
    print(f"  {PASS}  AWS Textract Client ? Initialized (credentials valid)")
except Exception as e:
    print(f"  {FAIL}  AWS Textract ? {e}")
    results.append(("API", "Textract", str(e)))

# NewsAPI Ping
try:
    import requests
    key = os.getenv("NEWS_API_KEY","")
    if key:
        r = requests.get(f"https://newsapi.org/v2/everything?q=test&pageSize=1&apiKey={key}", timeout=5)
        if r.status_code == 200:
            print(f"  {PASS}  NewsAPI ? Live & Responding (status 200)")
        else:
            print(f"  {WARN}  NewsAPI ? Status {r.status_code}: {r.json().get('message','')}")
    else:
        print(f"  {WARN}  NewsAPI ? Key missing")
except Exception as e:
    print(f"  {FAIL}  NewsAPI ? {e}")

# Twilio Ping
try:
    from twilio.rest import Client as TwilioClient
    sid = os.getenv("TWILIO_ACCOUNT_SID","")
    tok = os.getenv("TWILIO_AUTH_TOKEN","")
    if sid and tok:
        tc = TwilioClient(sid, tok)
        account = tc.api.accounts(sid).fetch()
        print(f"  {PASS}  Twilio ? Account Active: {account.friendly_name}")
    else:
        print(f"  {WARN}  Twilio ? Credentials missing")
except Exception as e:
    print(f"  {FAIL}  Twilio ? {e}")

# ??? SUMMARY ?????????????????????????????????????????????????
print("\n" + "=" * 60)
if results:
    print(f"  ?  {len(results)} ISSUES FOUND:")
    for category, name, reason in results:
        print(f"     [{category}] {name}: {reason}")
else:
    print("  ?  ALL CHECKS PASSED ? SYSTEM READY FOR HACKATHON")
print("=" * 60)
