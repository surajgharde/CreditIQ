import sys
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import os
import base64

env_file = 'd:/PROJECT/TGP/Vivriti/.env'

env_vars = {}
try:
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
except Exception as e:
    print(f"Error reading .env: {e}")
    sys.exit(1)

def test_api(url, headers={}, data=None, method='GET'):
    try:
        if data:
            data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, headers=headers, data=data, method=method)
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode('utf-8')
    except HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except URLError as e:
        return -1, str(e.reason)

results = {}

# 1. AWS Test
try:
    import boto3
    client = boto3.client('sts', 
        aws_access_key_id=env_vars.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=env_vars.get('AWS_SECRET_ACCESS_KEY'),
        region_name=env_vars.get('AWS_DEFAULT_REGION', 'us-east-1')
    )
    client.get_caller_identity()
    results['AWS'] = "✅ Valid"
except ImportError:
    results['AWS'] = "⚠️ Could not test (boto3 not installed)"
except Exception as e:
    results['AWS'] = f"❌ Invalid: {str(e)}"

# 2. Cohere API
cohere_key = env_vars.get('COHERE_API_KEY', '')
status, body = test_api("https://api.cohere.ai/v1/models", headers={"Authorization": f"Bearer {cohere_key}"})
if status == 200:
    results['Cohere'] = "✅ Valid"
else:
    results['Cohere'] = f"❌ Invalid: HTTP {status} - {body}"

# 3. News API
news_key = env_vars.get('NEWS_API_KEY', '')
status, body = test_api(f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_key}", headers={'User-Agent': 'Mozilla/5.0'})
if status == 200:
    results['News API'] = "✅ Valid"
else:
    results['News API'] = f"❌ Invalid: HTTP {status} - {body}"

# 4. Twilio
twilio_sid = env_vars.get('TWILIO_ACCOUNT_SID', '')
twilio_token = env_vars.get('TWILIO_AUTH_TOKEN', '')
auth_str = f"{twilio_sid}:{twilio_token}"
b64_auth_str = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
status, body = test_api(f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}.json", headers={"Authorization": f"Basic {b64_auth_str}"})
if status == 200:
    results['Twilio'] = "✅ Valid"
else:
    results['Twilio'] = f"❌ Invalid: HTTP {status} - {body}"

# 5. TheCompaniesAPI (MCA_API_KEY)
mca_key = env_vars.get('MCA_API_KEY', '')
status, body = test_api("https://api.thecompaniesapi.com/v1/locations/countries", headers={"Authorization": f"Bearer {mca_key}", "User-Agent": "Mozilla/5.0"})
if status == 401 or status == 403:
    status, body = test_api(f"https://api.thecompaniesapi.com/v1/locations/countries?key={mca_key}", headers={"User-Agent": "Mozilla/5.0"})
if str(status).startswith('2') or status == 429:
    results['MCA/TheCompanies API'] = "✅ Valid (or Rate Limited)"
else:
    results['MCA/TheCompanies API'] = f"❌ Invalid: HTTP {status} - {body}"

# 6. SendGrid
sendgrid_key = env_vars.get('SENDGRID_API_KEY', '')
status, body = test_api("https://api.sendgrid.com/v3/scopes", headers={"Authorization": f"Bearer {sendgrid_key}"})
if status == 200:
    results['SendGrid'] = "✅ Valid"
else:
    results['SendGrid'] = f"❌ Invalid: HTTP {status} - {body}"

# 7. Kaggle
kaggle_user = env_vars.get('KAGGLE_USERNAME', '')
kaggle_key = env_vars.get('KAGGLE_KEY', '')
auth_str_k = f"{kaggle_user}:{kaggle_key}"
b64_auth_str_k = base64.b64encode(auth_str_k.encode('ascii')).decode('ascii')
status, body = test_api("https://www.kaggle.com/api/v1/competitions/list", headers={"Authorization": f"Basic {b64_auth_str_k}"})
if status == 200:
    results['Kaggle'] = "✅ Valid"
else:
    results['Kaggle'] = f"❌ Invalid: HTTP {status} - {body}"

# Output results nicely
print(json.dumps(results, indent=2))
