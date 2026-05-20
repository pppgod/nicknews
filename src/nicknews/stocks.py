import requests
import yfinance as yf

KR_EXCHANGES = {"KSC", "KOE", "KSE", "KQ"}

YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
NAVER_SEARCH_URL = "https://ac.stock.naver.com/ac"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _search_naver(query):
    """Korean stock name -> (ticker, name) via Naver Finance autocomplete."""
    res = requests.get(
        NAVER_SEARCH_URL,
        params={"q": query, "q_enc": "UTF-8", "target": "stock"},
        headers=HEADERS,
        timeout=10,
    )
    items = res.json().get("items", [])
    if not items:
        return None, None
    item = items[0]
    suffix = ".KS" if item.get("typeCode") == "KOSPI" else ".KQ"
    return f"{item['code']}{suffix}", item["name"]


def _search_yahoo(query):
    """English name/ticker -> (ticker, name) via Yahoo Finance."""
    res = requests.get(
        YAHOO_SEARCH_URL,
        params={"q": query, "quotesCount": 5, "newsCount": 0},
        headers=HEADERS,
        timeout=10,
    )
    for q in res.json().get("quotes", []):
        if q.get("quoteType") == "EQUITY":
            ticker = q.get("symbol", "")
            name = q.get("shortname") or q.get("longname") or ticker
            return ticker, name
    return None, None


def search_ticker(query):
    try:
        if any("가" <= c <= "힣" for c in query):
            return _search_naver(query)
        return _search_yahoo(query)
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
