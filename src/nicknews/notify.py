import html
from datetime import datetime

from .sender import send_message
from .storage import load_user_stocks, all_user_ids
from .news import fetch_rss, fetch_keyword_news, format_section, TECH_FEEDS, ECONOMY_FEEDS
from .stocks import get_stock_line, is_significant


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
        if intraday:
            stocks = [s for s in stocks if is_significant(s["ticker"])]
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
        if intraday:
            stocks = [s for s in stocks if is_significant(s["ticker"])]
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
