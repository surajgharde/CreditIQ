import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv('d:/PROJECT/TGP/Vivriti/.env')

response = requests.get('https://www.kaggle.com/api/v1/competitions', auth=HTTPBasicAuth(os.getenv('KAGGLE_USERNAME'), os.getenv('KAGGLE_KEY')))
print(f"Kaggle: {response.status_code} {response.text[:100]}")
