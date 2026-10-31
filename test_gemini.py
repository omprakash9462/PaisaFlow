import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-3.1-flash-lite"

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": API_KEY
}

data = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Say hello in five words."
                }
            ]
        }
    ],
    "generationConfig": {
        "maxOutputTokens": 20
    }
}

try:
    print(f"Testing {MODEL}...", flush=True)

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=(10, 60)
    )

    print("Status Code:", response.status_code)
    print("Response:", response.text[:2000])

except requests.exceptions.Timeout:
    print("Request timed out after 60 seconds.")

except requests.exceptions.RequestException as e:
    print("Connection error:", e)