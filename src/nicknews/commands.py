import html
import os

from .sender import send_message
from .storage import load_user_stocks, save_user_stocks, add_allowed_id, remove_allowed_id
from .stocks import search_ticker, get_market, get_stock_detail
from .notify import send_daily_news, send_kr_stocks, send_us_stocks


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


def cmd_allow(parts, chat_id=None):
    if not _is_owner(chat_id):
        send_message("❌ 관리자 전용 명령어입니다.", chat_id)
        return
    if len(parts) < 2:
        send_message("사용법: /allow <chat_id>", chat_id)
        return
    target = parts[1]
    add_allowed_id(target)
    send_message(f"✅ 허용 추가: <code>{html.escape(target)}</code>", chat_id)


def cmd_disallow(parts, chat_id=None):
    if not _is_owner(chat_id):
        send_message("❌ 관리자 전용 명령어입니다.", chat_id)
        return
    if len(parts) < 2:
        send_message("사용법: /disallow <chat_id>", chat_id)
        return
    target = parts[1]
    if _is_owner(target):
        send_message("❌ 관리자 자신은 제거할 수 없습니다.", chat_id)
        return
    remove_allowed_id(target)
    send_message(f"✅ 허용 제거: <code>{html.escape(target)}</code>", chat_id)


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
    "/allow": cmd_allow,
    "/disallow": cmd_disallow,
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


def _is_owner(chat_id) -> bool:
    return str(chat_id) == str(os.getenv("TELEGRAM_CHAT_ID", ""))
