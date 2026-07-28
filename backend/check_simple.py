import os, sys
# Suppress all logging before imports
import logging
logging.disable(logging.CRITICAL)
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

issues = []
print("=== CreditIQ ENVIRONMENT CHECK ===\n")

# --- ENV VARS ---
print("--- ENV VARIABLES ---")
env_vars = [
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
    "CLAUDE_API_KEY", "NEWS_API_KEY",
    "GSTN_API_TOKEN", "MCA_API_KEY",
    "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
    "SENDGRID_API_KEY", "KAGGLE_USERNAME", "KAGGLE_KEY"
]
for v in env_vars:
    val = os.getenv(v, "")
    if val:
        print(f"  OK    {v}: {val[:8]}...")
    else:
        print(f"  MISS  {v}: NOT SET")
        issues.append(v)

# --- PACKAGES ---
print("\n--- PACKAGES ---")
pkgs = [
    "fastapi","sqlalchemy","boto3","anthropic","xgboost","shap",
    "joblib","pandas","numpy","sklearn","kaggle","networkx",
    "apscheduler","docx","twilio","sendgrid","tenacity",
    "pdfplumber","aiohttp","bs4","chromadb","transformers"
]
for p in pkgs:
    try:
        __import__(p)
        print(f"  OK    {p}")
    except ImportError:
        print(f"  MISS  {p}: NOT INSTALLED")
        issues.append(f"pkg:{p}")

# --- SERVICE IMPORTS ---
print("\n--- CreditIQ SERVICES ---")
svcs = [
    ("services.external_apis", "health_check_integrations"),
    ("services.ocr_service",   "extract_financial_data"),
    ("services.fraud_service", "run_fraud_detection"),
    ("services.rag_service",   "get_news_intelligence"),
    ("services.scoring_service","calculate_credit_score"),
    ("services.cam_service",   "generate_cam"),
    ("services.ews_service",   "get_ews_data"),
    ("services.pipeline",      "run_full_analysis"),
]
for mod, fn in svcs:
    try:
        m = __import__(mod, fromlist=[fn])
        getattr(m, fn)
        print(f"  OK    {mod}")
    except Exception as e:
        print(f"  FAIL  {mod}: {e}")
        issues.append(f"svc:{mod}")

# --- LIVE API TESTS ---
print("\n--- LIVE API TESTS ---")

# Claude
try:
    import anthropic
    key = os.getenv("CLAUDE_API_KEY","")
    if key:
        c = anthropic.Anthropic(api_key=key)
        msg = c.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=5,
            messages=[{"role":"user","content":"ping"}]
        )
        print(f"  OK    Claude 3.5 Sonnet: LIVE (stop_reason={msg.stop_reason})")
    else:
        print("  SKIP  Claude: no key")
except Exception as e:
    print(f"  FAIL  Claude: {e}")
    issues.append("api:claude")

# NewsAPI
try:
    import requests
    key = os.getenv("NEWS_API_KEY","")
    if key:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q":"economy","pageSize":1,"apiKey":key},
            timeout=5
        )
        d = r.json()
        if d.get("status")=="ok":
            print(f"  OK    NewsAPI: LIVE (totalResults={d.get('totalResults',0)})")
        else:
            print(f"  WARN  NewsAPI: {d.get('message','unknown error')}")
    else:
        print("  SKIP  NewsAPI: no key")
except Exception as e:
    print(f"  FAIL  NewsAPI: {e}")

# AWS
try:
    import boto3
    client = boto3.client(
        "sts",
        region_name=os.getenv("AWS_DEFAULT_REGION","us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    identity = client.get_caller_identity()
    print(f"  OK    AWS Credentials: VALID (account={identity.get('Account')})")
except Exception as e:
    print(f"  FAIL  AWS: {e}")
    issues.append("api:aws")

# Twilio
try:
    from twilio.rest import Client as TC
    sid = os.getenv("TWILIO_ACCOUNT_SID","")
    tok = os.getenv("TWILIO_AUTH_TOKEN","")
    if sid and tok:
        tc = TC(sid,tok)
        acc = tc.api.accounts(sid).fetch()
        print(f"  OK    Twilio: LIVE (account={acc.friendly_name})")
    else:
        print("  SKIP  Twilio: no credentials")
except Exception as e:
    print(f"  FAIL  Twilio: {e}")
    issues.append("api:twilio")

print("\n=== SUMMARY ===")
if issues:
    print(f"ISSUES ({len(issues)}):")
    for i in issues:
        print(f"  - {i}")
else:
    print("ALL CHECKS PASSED - READY FOR HACKATHON")
