import os
import json

STOCKS_FILE = os.getenv(
    "NICKNEWS_DATA_FILE",
    os.path.join(os.getcwd(), "stocks.json"),
)


def load_stocks():
    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if "keywords" not in data:
            data["keywords"] = []
        return data
    return {"kr": [], "us": [], "keywords": []}


def save_stocks(data):
    with open(STOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
