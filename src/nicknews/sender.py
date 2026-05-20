import os

import requests


def send_message(text, chat_id=None):
    token = os.getenv("TELEGRAM_TOKEN")
    if chat_id is None:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    return res.json()
