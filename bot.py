import os
import requests
import feedparser
import yfinance as yf
from urllib.parse import quote
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TECH_FEEDS = [
    "https://it.chosun.com/rss/allArticle.xml",
    "https://feeds.feedburner.com/zdkorea",
]

ECONOMY_FEEDS = [
    "https://www.yna.co.kr/rss/economy.xml",
    "https://www.mk.co.kr/rss/30000001/",
]

INTEREST_KEYWORDS = ["삼성전자", "SK하이닉스", "인공지능"]

KR_STOCKS = [
    {"name": "삼성전자", "ticker": "005930.KS"},
]

US_STOCKS = [
    {"name": "구글", "ticker": "GOOGL"},
]


def google_news_url(keyword):
    return f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"


def fetch_rss(feed_urls, count=5):
    articles = []
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
            })
        if len(articles) >= count:
            break
    return articles[:count]


def fetch_keyword_news(keyword, count=3):
    feed = feedparser.parse(google_news_url(keyword))
    return [
        {"title": e.get("title", "").split(" - ")[0].strip(), "url": e.get("link", "")}
        for e in feed.entries[:count]
    ]


def format_section(articles, header):
    lines = [header]
    for i, article in enumerate(articles, 1):
        title = article["title"].strip()
        url = article["url"]
        lines.append(f'{i}. <a href="{url}">{title}</a>')
    return "\n".join(lines)


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
    for keyword in INTEREST_KEYWORDS:
        articles = fetch_keyword_news(keyword, 3)
        interest_sections.append(format_section(articles, f"🔍 <b>{keyword}</b>"))

    message = (
        f"📰 <b>{today} 데일리 뉴스</b>\n\n"
        + format_section(tech, "💻 <b>기술</b>")
        + "\n\n"
        + format_section(economy, "💰 <b>경제</b>")
        + "\n\n"
        + "\n\n".join(interest_sections)
    )

    result = send_message(message)
    if result.get("ok"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 뉴스 전송 완료")
    else:
        print(f"뉴스 전송 실패: {result}")


def send_kr_stocks():
    today = datetime.now().strftime("%Y년 %m월 %d일")
    lines = [f"📈 <b>{today} 코스피 마감</b>\n"]
    for s in KR_STOCKS:
        lines.append(get_stock_line(s["name"], s["ticker"]))
    result = send_message("\n".join(lines))
    if result.get("ok"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 코스피 주가 전송 완료")
    else:
        print(f"코스피 전송 실패: {result}")


def send_us_stocks():
    today = datetime.now().strftime("%Y년 %m월 %d일")
    lines = [f"📈 <b>{today} 나스닥 마감</b>\n"]
    for s in US_STOCKS:
        lines.append(get_stock_line(s["name"], s["ticker"]))
    result = send_message("\n".join(lines))
    if result.get("ok"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 나스닥 주가 전송 완료")
    else:
        print(f"나스닥 전송 실패: {result}")


if __name__ == "__main__":
    print("테스트 전송 중...")
    send_kr_stocks()
    send_us_stocks()

    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_daily_news, "cron", hour=9, minute=0)
    scheduler.add_job(send_kr_stocks, "cron", hour=15, minute=35)
    scheduler.add_job(send_us_stocks, "cron", hour=5, minute=5)
    print("봇 실행 중 — 종료: Ctrl+C")
    print("  뉴스: 매일 09:00")
    print("  코스피 마감: 매일 15:35")
    print("  나스닥 마감: 매일 05:05")
    scheduler.start()
