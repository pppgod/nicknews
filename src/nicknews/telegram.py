import html
import os
import time
import requests
from datetime import datetime

from .storage import load_user_stocks, save_user_stocks, all_user_ids
from .news import fetch_rss, fetch_keyword_news, format_section, TECH_FEEDS, ECONOMY_FEEDS
from .stocks import search_ticker, get_market, get_stock_line, get_stock_detail


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


def _news_message(chat_id):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    tech = fetch_rss(TECH_FEEDS, 5)
    economy = fetch_rss(ECONOMY_FEEDS, 5)

    interest_sections = []
    for keyword in load_user_stocks(chat_id)["keywords"]:
        articles = fetch_keyword_news(keyword, 3)
        interest_sections.append(format_section(articles, f"🔍 <b>{html.escape(keyword)}</b>"))

    parts = [
        f"📰 <b>{today} 데일리 뉴스</b>",
        format_section(tech, "💻 <b>기술</b>"),
        format_section(economy, "💰 <b>경제</b>"),
        *interest_sections,
    ]
    return "\n\n".join(parts)


def send_daily_news(chat_id=None):
    targets = [chat_id] if chat_id else list(all_user_ids())
    for uid in targets:
        result = send_message(_news_message(uid), uid)
        if result.get("ok"):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 뉴스 전송 완료 → {uid}")
        else:
            print(f"뉴스 전송 실패 → {uid}: {result}")


def send_kr_stocks(intraday=False, chat_id=None):
    targets = [chat_id] if chat_id else list(all_user_ids())
    today = datetime.now().strftime("%Y년 %m월 %d일")
    header = "코스피 장 중" if intraday else "코스피 마감"
    for uid in targets:
        stocks = load_user_stocks(uid)["kr"]
        if not stocks:
            continue
        lines = [f"📈 <b>{today} {header}</b>\n"]
        for s in stocks:
            lines.append(get_stock_line(s["name"], s["ticker"]))
        result = send_message("\n".join(lines), uid)
        if result.get("ok"):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 코스피 전송 완료 → {uid}")
        else:
            print(f"코스피 전송 실패 → {uid}: {result}")


def send_us_stocks(intraday=False, chat_id=None):
    targets = [chat_id] if chat_id else list(all_user_ids())
    today = datetime.now().strftime("%Y년 %m월 %d일")
    header = "나스닥 장 중" if intraday else "나스닥 마감"
    for uid in targets:
        stocks = load_user_stocks(uid)["us"]
        if not stocks:
            continue
        lines = [f"📈 <b>{today} {header}</b>\n"]
        for s in stocks:
            lines.append(get_stock_line(s["name"], s["ticker"]))
        result = send_message("\n".join(lines), uid)
        if result.get("ok"):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 나스닥 전송 완료 → {uid}")
        else:
            print(f"나스닥 전송 실패 → {uid}: {result}")


# --- 명령어 핸들러 ---

def cmd_add(parts, chat_id=None):
    if len(parts) < 2:
        send_message("사용법: /add <티커 또는 회사명>\n예) /add 삼성전자\n예) /add AAPL", chat_id)
        return
    query = " ".join(parts[1:])
    send_message(f"🔍 {html.escape(query)} 조회 중...", chat_id)
    ticker, name = search_ticker(query)
    if ticker is None:
        send_message(f"❌ 종목을 찾을 수 없습니다: {html.escape(query)}", chat_id)
        return
    market = get_market(ticker)
    data = load_user_stocks(chat_id)
    if any(s["ticker"] == ticker for s in data[market]):
        send_message(f"이미 등록된 종목: {html.escape(name)} ({html.escape(ticker)})", chat_id)
        return
    market_label = "🇰🇷 한국" if market == "kr" else "🇺🇸 미국"
    data[market].append({"name": name, "ticker": ticker})
    save_user_stocks(chat_id, data)
    send_message(f"✅ {market_label} 주식 추가: <b>{html.escape(name)}</b> ({html.escape(ticker)})", chat_id)


def cmd_remove(parts, chat_id=None):
    if len(parts) < 2:
        send_message("사용법: /remove <티커>\n예) /remove AAPL", chat_id)
        return
    ticker = parts[1].upper()
    data = load_user_stocks(chat_id)
    before = len(data["kr"]) + len(data["us"])
    data["kr"] = [s for s in data["kr"] if s["ticker"] != ticker]
    data["us"] = [s for s in data["us"] if s["ticker"] != ticker]
    if len(data["kr"]) + len(data["us"]) == before:
        send_message(f"등록되지 않은 종목: {html.escape(ticker)}", chat_id)
    else:
        save_user_stocks(chat_id, data)
        send_message(f"✅ 종목 제거: <b>{html.escape(ticker)}</b>", chat_id)


def cmd_watch(parts, chat_id=None):
    if len(parts) < 2:
        send_message("사용법: /watch <키워드>\n예) /watch 엔비디아", chat_id)
        return
    keyword = " ".join(parts[1:])
    data = load_user_stocks(chat_id)
    if keyword in data["keywords"]:
        send_message(f"이미 등록된 키워드: {html.escape(keyword)}", chat_id)
        return
    data["keywords"].append(keyword)
    save_user_stocks(chat_id, data)
    send_message(f"✅ 관심 키워드 추가: <b>{html.escape(keyword)}</b>", chat_id)


def cmd_unwatch(parts, chat_id=None):
    if len(parts) < 2:
        send_message("사용법: /unwatch <키워드>\n예) /unwatch 엔비디아", chat_id)
        return
    keyword = " ".join(parts[1:])
    data = load_user_stocks(chat_id)
    if keyword not in data["keywords"]:
        send_message(f"등록되지 않은 키워드: {html.escape(keyword)}", chat_id)
        return
    data["keywords"].remove(keyword)
    save_user_stocks(chat_id, data)
    send_message(f"✅ 관심 키워드 제거: <b>{html.escape(keyword)}</b>", chat_id)


def cmd_list(_, chat_id=None):
    data = load_user_stocks(chat_id)
    kr_list = "\n".join(f"  • {html.escape(s['name'])} ({html.escape(s['ticker'])})" for s in data["kr"]) or "  없음"
    us_list = "\n".join(f"  • {html.escape(s['name'])} ({html.escape(s['ticker'])})" for s in data["us"]) or "  없음"
    kw_list = "\n".join(f"  • {html.escape(k)}" for k in data["keywords"]) or "  없음"
    send_message(f"📋 <b>구독 목록</b>\n\n🇰🇷 한국 주식\n{kr_list}\n\n🇺🇸 미국 주식\n{us_list}\n\n🔍 관심 키워드\n{kw_list}", chat_id)


def cmd_news(_, chat_id=None):
    send_daily_news(chat_id=chat_id)


def cmd_kr(_, chat_id=None):
    from .bot import is_kr_market_open
    send_kr_stocks(intraday=is_kr_market_open(), chat_id=chat_id)


def cmd_us(_, chat_id=None):
    from .bot import is_us_market_open
    send_us_stocks(intraday=is_us_market_open(), chat_id=chat_id)


def cmd_stock(parts, chat_id=None):
    if len(parts) < 2:
        send_message("사용법: /stock <티커 또는 종목명>\n예) /stock AAPL\n예) /stock 삼성전자", chat_id)
        return
    query = " ".join(parts[1:])
    send_message(f"🔍 {html.escape(query)} 조회 중...", chat_id)
    ticker, name = search_ticker(query)
    if ticker is None:
        send_message(f"❌ 종목을 찾을 수 없습니다: {html.escape(query)}", chat_id)
        return
    send_message(get_stock_detail(name, ticker), chat_id)


def cmd_help(_, chat_id=None):
    send_message(
        "📖 <b>명령어 안내</b>\n\n"
        "<b>즉시 조회</b>\n"
        "/news — 오늘 뉴스 지금 받기\n"
        "/kr — 한국 주식 현재가 조회\n"
        "/us — 미국 주식 현재가 조회\n"
        "/stock &lt;티커 또는 종목명&gt; — 단일 종목 현재가 조회\n\n"
        "<b>구독 관리</b>\n"
        "/add &lt;종목명 또는 티커&gt; — 주식 추가 (한국/미국 자동 구분)\n"
        "/remove &lt;티커&gt; — 주식 제거\n"
        "/watch &lt;키워드&gt; — 관심 키워드 추가\n"
        "/unwatch &lt;키워드&gt; — 관심 키워드 제거\n"
        "/list — 전체 구독 목록 확인\n\n"
        "예시:\n"
        "/stock 삼성전자\n"
        "/stock AAPL\n"
        "/add 삼성전자\n"
        "/watch 엔비디아",
        chat_id,
    )


COMMANDS = {
    "/add": cmd_add,
    "/remove": cmd_remove,
    "/watch": cmd_watch,
    "/unwatch": cmd_unwatch,
    "/list": cmd_list,
    "/news": cmd_news,
    "/kr": cmd_kr,
    "/us": cmd_us,
    "/stock": cmd_stock,
    "/help": cmd_help,
}


def handle_command(text, chat_id=None):
    parts = text.strip().split()
    if not parts:
        return
    cmd = parts[0].lower().split("@")[0]
    handler = COMMANDS.get(cmd)
    if handler:
        handler(parts, chat_id)


def _allowed_ids():
    owner = os.getenv("TELEGRAM_CHAT_ID", "")
    extra = os.getenv("ALLOWED_CHAT_IDS", "")
    return {owner} | {c.strip() for c in extra.split(",") if c.strip()}


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
