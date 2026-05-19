import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

from storage import load_stocks, save_stocks
from news import fetch_rss, fetch_keyword_news, format_section, TECH_FEEDS, ECONOMY_FEEDS
from stocks import search_ticker, get_market, get_stock_line

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    return res.json()


def send_daily_news():
    today = datetime.now().strftime("%Y년 %m월 %d일")
    tech = fetch_rss(TECH_FEEDS, 5)
    economy = fetch_rss(ECONOMY_FEEDS, 5)

    interest_sections = []
    for keyword in load_stocks()["keywords"]:
        articles = fetch_keyword_news(keyword, 3)
        interest_sections.append(format_section(articles, f"🔍 <b>{keyword}</b>"))

    parts = [
        f"📰 <b>{today} 데일리 뉴스</b>",
        format_section(tech, "💻 <b>기술</b>"),
        format_section(economy, "💰 <b>경제</b>"),
        *interest_sections,
    ]
    result = send_message("\n\n".join(parts))
    if result.get("ok"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 뉴스 전송 완료")
    else:
        print(f"뉴스 전송 실패: {result}")


def send_kr_stocks():
    today = datetime.now().strftime("%Y년 %m월 %d일")
    lines = [f"📈 <b>{today} 코스피 마감</b>\n"]
    for s in load_stocks()["kr"]:
        lines.append(get_stock_line(s["name"], s["ticker"]))
    result = send_message("\n".join(lines))
    if result.get("ok"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 코스피 주가 전송 완료")
    else:
        print(f"코스피 전송 실패: {result}")


def send_us_stocks():
    today = datetime.now().strftime("%Y년 %m월 %d일")
    lines = [f"📈 <b>{today} 나스닥 마감</b>\n"]
    for s in load_stocks()["us"]:
        lines.append(get_stock_line(s["name"], s["ticker"]))
    result = send_message("\n".join(lines))
    if result.get("ok"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 나스닥 주가 전송 완료")
    else:
        print(f"나스닥 전송 실패: {result}")


# --- 명령어 핸들러 ---

def cmd_add(parts):
    if len(parts) < 2:
        send_message("사용법: /add <티커 또는 회사명>\n예) /add 삼성전자\n예) /add AAPL")
        return
    query = " ".join(parts[1:])
    send_message(f"🔍 {query} 조회 중...")
    ticker, name = search_ticker(query)
    if ticker is None:
        send_message(f"❌ 종목을 찾을 수 없습니다: {query}")
        return
    market = get_market(ticker)
    data = load_stocks()
    if any(s["ticker"] == ticker for s in data[market]):
        send_message(f"이미 등록된 종목: {name} ({ticker})")
        return
    market_label = "🇰🇷 한국" if market == "kr" else "🇺🇸 미국"
    data[market].append({"name": name, "ticker": ticker})
    save_stocks(data)
    send_message(f"✅ {market_label} 주식 추가: <b>{name}</b> ({ticker})")


def cmd_remove(parts):
    if len(parts) < 2:
        send_message("사용법: /remove <티커>\n예) /remove AAPL")
        return
    ticker = parts[1].upper()
    data = load_stocks()
    before = len(data["kr"]) + len(data["us"])
    data["kr"] = [s for s in data["kr"] if s["ticker"] != ticker]
    data["us"] = [s for s in data["us"] if s["ticker"] != ticker]
    if len(data["kr"]) + len(data["us"]) == before:
        send_message(f"등록되지 않은 종목: {ticker}")
    else:
        save_stocks(data)
        send_message(f"✅ 종목 제거: <b>{ticker}</b>")


def cmd_watch(parts):
    if len(parts) < 2:
        send_message("사용법: /watch <키워드>\n예) /watch 엔비디아")
        return
    keyword = " ".join(parts[1:])
    data = load_stocks()
    if keyword in data["keywords"]:
        send_message(f"이미 등록된 키워드: {keyword}")
        return
    data["keywords"].append(keyword)
    save_stocks(data)
    send_message(f"✅ 관심 키워드 추가: <b>{keyword}</b>")


def cmd_unwatch(parts):
    if len(parts) < 2:
        send_message("사용법: /unwatch <키워드>\n예) /unwatch 엔비디아")
        return
    keyword = " ".join(parts[1:])
    data = load_stocks()
    if keyword not in data["keywords"]:
        send_message(f"등록되지 않은 키워드: {keyword}")
        return
    data["keywords"].remove(keyword)
    save_stocks(data)
    send_message(f"✅ 관심 키워드 제거: <b>{keyword}</b>")


def cmd_list(_):
    data = load_stocks()
    kr_list = "\n".join(f"  • {s['name']} ({s['ticker']})" for s in data["kr"]) or "  없음"
    us_list = "\n".join(f"  • {s['name']} ({s['ticker']})" for s in data["us"]) or "  없음"
    kw_list = "\n".join(f"  • {k}" for k in data["keywords"]) or "  없음"
    send_message(f"📋 <b>구독 목록</b>\n\n🇰🇷 한국 주식\n{kr_list}\n\n🇺🇸 미국 주식\n{us_list}\n\n🔍 관심 키워드\n{kw_list}")


def cmd_help(_):
    send_message(
        "📖 <b>명령어 안내</b>\n\n"
        "/add &lt;종목명 또는 티커&gt; — 주식 추가 (한국/미국 자동 구분)\n"
        "/remove &lt;티커&gt; — 주식 제거\n"
        "/watch &lt;키워드&gt; — 관심 키워드 추가\n"
        "/unwatch &lt;키워드&gt; — 관심 키워드 제거\n"
        "/list — 전체 구독 목록 확인\n\n"
        "예시:\n"
        "/add 삼성전자\n"
        "/add AAPL\n"
        "/watch 엔비디아\n"
        "/unwatch 인공지능"
    )


COMMANDS = {
    "/add": cmd_add,
    "/remove": cmd_remove,
    "/watch": cmd_watch,
    "/unwatch": cmd_unwatch,
    "/list": cmd_list,
    "/help": cmd_help,
}


def handle_command(text):
    parts = text.strip().split()
    if not parts:
        return
    cmd = parts[0].lower().split("@")[0]
    handler = COMMANDS.get(cmd)
    if handler:
        handler(parts)


def poll_messages():
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset
            res = requests.get(url, params=params, timeout=35)
            data = res.json()
            if data.get("ok"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if str(msg.get("chat", {}).get("id", "")) != str(TELEGRAM_CHAT_ID):
                        continue
                    text = msg.get("text", "")
                    if text.startswith("/"):
                        handle_command(text)
        except Exception as e:
            print(f"폴링 오류: {e}")
            time.sleep(5)
