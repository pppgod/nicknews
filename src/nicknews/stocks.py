import html
import pandas as pd
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


def _format_volume(vol):
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"{vol / 1_000:.1f}K"
    return f"{int(vol):,}"


def get_stock_line(name, ticker):
    ename = html.escape(name)
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price
        prev = info.previous_close
        volume = info.last_volume
        change = price - prev
        pct = change / prev * 100
        arrow = "▲" if change >= 0 else "▼"

        hist = stock.history(period="5d")
        closes = hist.get("Close", pd.Series(dtype=float))
        vols = hist.get("Volume", pd.Series(dtype=float))

        def _change_str(current, past):
            if past > 0:
                p = (current - past) / past * 100
                a = "▲" if p >= 0 else "▼"
                return f"{a}{p:+.2f}%"
            return None

        price_parts = [f"전일 {pct:+.2f}%"]
        if len(closes) >= 5 and (s := _change_str(price, closes.iloc[0])):
            price_parts.append(f"1주전 {s}")
        price_str = "  ".join(price_parts)

        vol_changes = []
        if len(vols) >= 2 and (s := _change_str(volume, vols.iloc[-2])):
            vol_changes.append(f"전일 {s}")
        if len(vols) >= 5 and (s := _change_str(volume, vols.iloc[0])):
            vol_changes.append(f"1주전 {s}")
        vol_str = _format_volume(volume)
        if vol_changes:
            vol_str += f"  ({'  '.join(vol_changes)})"

        return f"{arrow} <b>{ename}</b>  {price:,.0f}  ({price_str})\n   거래량 {vol_str}"
    except Exception:
        return f"<b>{ename}</b>  데이터 조회 실패"


def get_stock_detail(name, ticker):
    ename = html.escape(name)
    eticker = html.escape(ticker)
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        current = info.last_price
        volume = info.last_volume

        hist = stock.history(period="3mo")
        closes = hist["Close"]

        prev_close = closes.iloc[-1]
        today_pct = (current - prev_close) / prev_close * 100
        today_arrow = "▲" if today_pct >= 0 else "▼"

        lines = [
            f"📊 <b>{ename}</b> ({eticker})\n",
            f"현재가  {today_arrow} {current:,.0f}  ({today_pct:+.2f}%)",
            f"거래량  {_format_volume(volume)}\n",
            "📅 기간별 등락",
        ]

        volumes = hist["Volume"]

        def _period_line(label, past_price, past_vol):
            price_pct = (current - past_price) / past_price * 100
            pa = "▲" if price_pct >= 0 else "▼"
            base = f"  {label}  {past_price:,.0f}  {pa} {price_pct:+.2f}%"
            if past_vol > 0:
                vol_pct = (volume - past_vol) / past_vol * 100
                va = "▲" if vol_pct >= 0 else "▼"
                return f"{base}   거래량 {_format_volume(past_vol)}  {va} {vol_pct:+.2f}%"
            return f"{base}   거래량 {_format_volume(past_vol)}"

        for label, n in [("1주 전  ", 5), ("1개월 전", 21)]:
            if n <= len(closes):
                lines.append(_period_line(label, closes.iloc[-n], volumes.iloc[-n]))

        if len(closes) > 1:
            lines.append(_period_line("3개월 전", closes.iloc[0], volumes.iloc[0]))

        return "\n".join(lines)
    except Exception:
        return f"<b>{ename}</b>  데이터 조회 실패"
