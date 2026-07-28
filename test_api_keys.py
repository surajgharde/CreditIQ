import os
import requests
from dotenv import load_dotenv

load_dotenv('d:/PROJECT/TGP/Vivriti/.env')

results = {}

# 1. AWS (Boto3)
try:
    import boto3
    client = boto3.client(
        'sts',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )
    client.get_caller_identity()
    results['AWS'] = 'Working'
except Exception as e:
    results['AWS'] = f'Failed: {str(e)}'

# 2. Cohere
try:
    response = requests.post(
        'https://api.cohere.ai/v1/generate',
        headers={'Authorization': f"Bearer {os.getenv('COHERE_API_KEY')}"},
        json={'prompt': 'test', 'max_tokens': 1}
    )
    if response.status_code == 200:
        results['Cohere'] = 'Working'
    else:
        results['Cohere'] = f'Failed: {response.status_code} {response.text}'
except Exception as e:
    results['Cohere'] = f'Failed: {str(e)}'

# 3. News API
try:
    response = requests.get(f"https://newsapi.org/v2/top-headlines?country=us&apiKey={os.getenv('NEWS_API_KEY')}")
    if response.status_code == 200:
        results['News API'] = 'Working'
    else:
        results['News API'] = f'Failed: {response.status_code} {response.text}'
except Exception as e:
    results['News API'] = f'Failed: {str(e)}'

# 4. Companies API (MCA)
try:
    response = requests.get(
        "https://api.thecompaniesapi.com/v1/companies/tata",
        headers={'Authorization': f"Basic {os.getenv('MCA_API_KEY')}"}
    )
    if response.status_code in [200, 404]: # 404 means company not found, but API key is valid
        results['Companies API (MCA)'] = 'Working'
    elif response.status_code == 401:
        results['Companies API (MCA)'] = 'Failed: Unauthorized (401)'
    else:
        results['Companies API (MCA)'] = f'Failed: {response.status_code} {response.text}'
except Exception as e:
    results['Companies API (MCA)'] = f'Failed: {str(e)}'

# 5. Twilio
try:
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    response = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json", auth=(sid, token))
    if response.status_code == 200:
        results['Twilio'] = 'Working'
    else:
        results['Twilio'] = f'Failed: {response.status_code} {response.text}'
except Exception as e:
    results['Twilio'] = f'Failed: {str(e)}'

# 6. SendGrid
try:
    response = requests.get(
        "https://api.sendgrid.com/v3/user/profile",
        headers={"Authorization": f"Bearer {os.getenv('SENDGRID_API_KEY')}"}
    )
    if response.status_code == 200:
        results['SendGrid'] = 'Working'
    else:
        results['SendGrid'] = f'Failed: {response.status_code} {response.text}'
except Exception as e:
    results['SendGrid'] = f'Failed: {str(e)}'

for k, v in results.items():
    print(f"{k}: {v}")
