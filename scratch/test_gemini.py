import requests
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
model = "gemma-3-27b-it"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

payload = {
    "contents": [{"parts": [{"text": "Hello, are you Gemma 3?"}]}]
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
