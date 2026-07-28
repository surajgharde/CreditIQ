import os
import requests
from dotenv import load_dotenv

load_dotenv('d:/PROJECT/TGP/Vivriti/.env')

response = requests.post(
    'https://api.cohere.ai/v1/chat',
    headers={'Authorization': f"Bearer {os.getenv('COHERE_API_KEY')}"},
    json={'message': 'test'}
)
print(f"Cohere Chat API: {response.status_code} {response.text}")
