import html
import os
from datetime import date

from .sender import send_message
from .storage import load_user_stocks, save_user_stocks, add_allowed_id, remove_allowed_id
from .stocks import search_ticker, get_market, get_stock_detail
from .notify import send_daily_news, send_kr_stocks, send_us_stocks
from .flights import (
    parse_yymmdd, resolve_route, get_flight_price, record_price,
    format_flight_price_message, route_label, date_label,
)


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
    send_kr_stocks(intraday=False, chat_id=chat_id)


def cmd_us(_, chat_id=None):
    send_us_stocks(intraday=False, chat_id=chat_id)


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


def cmd_addflight(parts, chat_id=None):
    if len(parts) < 4:
        send_message(
            "사용법: /addflight <출발지> <목적지> <가는날짜:yymmdd> [오는날짜:yymmdd]\n"
            "예) /addflight 인천 도쿄 260901 260908\n"
            "예) /addflight ICN NRT 260901  (편도)",
            chat_id,
        )
        return
    origin_query, dest_query, depart_raw = parts[1], parts[2], parts[3]
    return_raw = parts[4] if len(parts) > 4 else None

    try:
        depart_date = parse_yymmdd(depart_raw)
    except ValueError:
        send_message(f"❌ 가는 날짜 형식이 올바르지 않습니다 (yymmdd): {html.escape(depart_raw)}", chat_id)
        return
    if depart_date < date.today():
        send_message("❌ 가는 날짜가 이미 지났습니다.", chat_id)
        return

    return_date = None
    if return_raw:
        try:
            return_date = parse_yymmdd(return_raw)
        except ValueError:
            send_message(f"❌ 오는 날짜 형식이 올바르지 않습니다 (yymmdd): {html.escape(return_raw)}", chat_id)
            return
        if return_date < depart_date:
            send_message("❌ 오는 날짜가 가는 날짜보다 빠릅니다.", chat_id)
            return

    send_message(f"🔍 {html.escape(origin_query)} → {html.escape(dest_query)} 조회 중...", chat_id)
    resolved = resolve_route(origin_query, dest_query)
    if resolved is None:
        send_message(f"❌ 공항을 찾을 수 없습니다: {html.escape(origin_query)} / {html.escape(dest_query)}", chat_id)
        return
    o_code, o_name, d_code, d_name = resolved

    flight = {
        "origin": o_code,
        "origin_name": o_name,
        "destination": d_code,
        "destination_name": d_name,
        "depart": depart_raw,
        "return": return_raw,
        "history": [],
    }

    fare = get_flight_price(flight)
    if fare is not None:
        record_price(flight, fare["price"])

    data = load_user_stocks(chat_id)
    data.setdefault("flights", []).append(flight)
    save_user_stocks(chat_id, data)

    if fare is not None:
        message = format_flight_price_message(flight, fare)
        send_message(f"✅ 항공권 추적 등록\n\n{message}", chat_id)
    else:
        send_message(
            f"✅ 항공권 추적 등록: <b>{route_label(flight)}</b>  {date_label(flight)}\n"
            "(현재가 조회 실패, 다음 예약 전송 때 다시 시도합니다)",
            chat_id,
        )


def cmd_removeflight(parts, chat_id=None):
    if len(parts) < 2 or not parts[1].isdigit():
        send_message("사용법: /removeflight <번호>\n/flights 로 번호를 먼저 확인하세요.", chat_id)
        return
    idx = int(parts[1]) - 1
    data = load_user_stocks(chat_id)
    flights = data.get("flights", [])
    if idx < 0 or idx >= len(flights):
        send_message(f"❌ 등록되지 않은 번호: {html.escape(parts[1])}", chat_id)
        return
    removed = flights.pop(idx)
    save_user_stocks(chat_id, data)
    send_message(f"✅ 항공권 추적 삭제: <b>{route_label(removed)}</b>", chat_id)


def cmd_flights(_, chat_id=None):
    data = load_user_stocks(chat_id)
    flights = data.get("flights", [])
    if not flights:
        send_message("✈️ 추적 중인 항공권이 없습니다.\n/addflight 로 등록하세요.", chat_id)
        return
    lines = ["✈️ <b>추적 중인 항공권</b>\n"]
    for i, f in enumerate(flights, 1):
        history = f.get("history", [])
        last_price = f"{history[-1]['price']:,}원" if history else "미확인"
        lines.append(f"{i}. {route_label(f)}  {date_label(f)}\n   최근 조회가 {last_price}")
    send_message("\n".join(lines), chat_id)


def cmd_flight(parts, chat_id=None):
    if len(parts) < 2 or not parts[1].isdigit():
        send_message("사용법: /flight <번호>\n/flights 로 번호를 먼저 확인하세요.", chat_id)
        return
    idx = int(parts[1]) - 1
    data = load_user_stocks(chat_id)
    flights = data.get("flights", [])
    if idx < 0 or idx >= len(flights):
        send_message(f"❌ 등록되지 않은 번호: {html.escape(parts[1])}", chat_id)
        return

    flight = flights[idx]
    send_message(f"🔍 {route_label(flight)} 조회 중...", chat_id)
    fare = get_flight_price(flight)
    if fare is None:
        send_message(f"❌ {route_label(flight)} 현재가 조회 실패", chat_id)
        return

    record_price(flight, fare["price"])
    save_user_stocks(chat_id, data)
    send_message(format_flight_price_message(flight, fare), chat_id)


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
        "<b>항공권 가격 추적</b>\n"
        "/addflight &lt;출발지&gt; &lt;목적지&gt; &lt;가는날짜:yymmdd&gt; [오는날짜:yymmdd] — 항공권 추적 등록\n"
        "/removeflight &lt;번호&gt; — 항공권 추적 삭제\n"
        "/flights — 추적 중인 항공권 목록 확인 (매일 14:00 자동 전송)\n"
        "/flight &lt;번호&gt; — 해당 항공권 지금 바로 가격 조회\n\n"
        "예시:\n"
        "/stock 삼성전자\n"
        "/stock AAPL\n"
        "/add 삼성전자\n"
        "/watch 엔비디아\n"
        "/addflight 인천 도쿄 260901 260908",
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
    "/addflight": cmd_addflight,
    "/removeflight": cmd_removeflight,
    "/flights": cmd_flights,
    "/flight": cmd_flight,
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
