import os
import time

import requests

from .storage import load_allowed_ids
from .commands import handle_command


def _allowed_ids():
    owner = os.getenv("TELEGRAM_CHAT_ID", "")
    return {owner} | load_allowed_ids()


def poll_messages():
    token = os.getenv("TELEGRAM_TOKEN")
    offset = None
    while True:
        try:
            allowed = _allowed_ids()
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset
            res = requests.get(url, params=params, timeout=35)
            data = res.json()
            if data.get("ok"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    sender_id = str(msg.get("chat", {}).get("id", ""))
                    if sender_id not in allowed:
                        continue
                    text = msg.get("text", "")
                    if text.startswith("/"):
                        handle_command(text, sender_id)
        except Exception as e:
            print(f"폴링 오류: {e}")
            time.sleep(5)
