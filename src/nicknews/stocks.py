import requests
import yfinance as yf

KR_EXCHANGES = {"KSC", "KOE", "KSE", "KQ"}

YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0"}


def search_ticker(query):
    try:
        res = requests.get(
            YAHOO_SEARCH_URL,
            params={"q": query, "quotesCount": 5, "newsCount": 0, "lang": "ko", "region": "KR"},
            headers=YAHOO_HEADERS,
            timeout=10,
        )
        quotes = res.json().get("quotes", [])
        for q in quotes:
            if q.get("quoteType") == "EQUITY":
                ticker = q.get("symbol", "")
                name = q.get("shortname") or q.get("longname") or ticker
                return ticker, name
        return None, None
    except Exception:
        return None, None


def get_market(ticker):
    try:
        info = yf.Ticker(ticker).info
        exchange = info.get("exchange", "")
        return "kr" if exchange in KR_EXCHANGES else "us"
    except Exception:
        return "us"


def get_stock_line(name, ticker):
    try:
        info = yf.Ticker(ticker).fast_info
        price = info.last_price
        prev = info.previous_close
        change = price - prev
        pct = change / prev * 100
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} <b>{name}</b>  {price:,.0f}  ({pct:+.2f}%)"
    except Exception:
        return f"<b>{name}</b>  데이터 조회 실패"
