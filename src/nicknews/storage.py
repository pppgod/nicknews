import os
import json

STOCKS_FILE = os.getenv(
    "NICKNEWS_DATA_FILE",
    os.path.join(os.getcwd(), "stocks.json"),
)

_EMPTY = {"kr": [], "us": [], "keywords": []}


def _load_all() -> dict:
    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_all(data: dict):
    with open(STOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _migrate_if_needed(data: dict) -> dict:
    # old flat format: {"kr": [...], "us": [...], "keywords": [...]}
    if "kr" in data:
        owner = os.getenv("TELEGRAM_CHAT_ID", "unknown")
        migrated = {owner: data}
        _save_all(migrated)
        return migrated
    return data


def load_user_stocks(chat_id: str) -> dict:
    data = _migrate_if_needed(_load_all())
    user = dict(data.get(str(chat_id), _EMPTY))
    if "keywords" not in user:
        user["keywords"] = []
    return user


def save_user_stocks(chat_id: str, user_data: dict):
    data = _migrate_if_needed(_load_all())
    data[str(chat_id)] = user_data
    _save_all(data)


def all_user_ids() -> set:
    data = _migrate_if_needed(_load_all())
    ids = set(data.keys())
    owner = os.getenv("TELEGRAM_CHAT_ID", "")
    if owner:
        ids.add(owner)
    return ids
