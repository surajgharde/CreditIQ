import os
import requests
from dotenv import load_dotenv

# Force reload by not using cache
load_dotenv('d:/PROJECT/TGP/Vivriti/.env', override=True)

try:
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    print(f"Testing with SID: {sid[:5]}... Token: {token[:5]}...")
    response = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json", auth=(sid, token))
    if response.status_code == 200:
        print("Twilio: Working")
    else:
        print(f"Twilio: Failed: {response.status_code} {response.text}")
except Exception as e:
    print(f"Twilio: Failed: {str(e)}")
