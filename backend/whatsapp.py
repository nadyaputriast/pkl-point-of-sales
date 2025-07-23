import requests
import os

FONNTE_API_URL = "https://api.fonnte.com/send"
FONNTE_API_KEY = os.getenv("FONNTE_API_KEY")  # simpan di .env

def send_whatsapp(phone, message):
    payload = {
        "target": phone,
        "message": message,
        "token": FONNTE_API_KEY
    }
    response = requests.post(FONNTE_API_URL, data=payload)
    return response.json()
