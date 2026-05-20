import os
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import holidays
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from .telegram import send_daily_news, send_kr_stocks, send_us_stocks, poll_messages

KST = ZoneInfo("Asia/Seoul")
# ZoneInfo("America/New_York") automatically switches between EST(UTC-5) and EDT(UTC-4)
EST = ZoneInfo("America/New_York")


def is_kr_market_open(now=None):
    if now is None:
        now = datetime.now(KST)
    if now.weekday() >= 5:
        return False
    if now.date() in holidays.KR(years=now.year):
        return False
    t = now.time()
    return dtime(9, 0) <= t <= dtime(15, 30)


def is_us_market_open(now=None):
    if now is None:
        now = datetime.now(EST)
    if now.weekday() >= 5:
        return False
    if now.date() in holidays.NYSE(years=now.year):
        return False
    t = now.time()
    return dtime(9, 30) <= t <= dtime(16, 0)


def _send_kr_if_open():
    if is_kr_market_open():
        send_kr_stocks()


def _send_us_if_open():
    if is_us_market_open():
        send_us_stocks()


def main():
    load_dotenv()
    missing = [k for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID") if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"필수 환경변수 미설정: {', '.join(missing)}")

    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_daily_news, "cron", hour=9, minute=0)
    scheduler.add_job(send_kr_stocks, "cron", hour=15, minute=35)
    scheduler.add_job(send_us_stocks, "cron", hour=5, minute=5)
    scheduler.add_job(_send_kr_if_open, "cron", minute="0,30", timezone="Asia/Seoul")
    scheduler.add_job(_send_us_if_open, "cron", minute="0,30", timezone="Asia/Seoul")
    scheduler.start()

    print("봇 실행 중 — 종료: Ctrl+C")
    print("  뉴스: 매일 09:00")
    print("  코스피 마감: 매일 15:35 / 장 중 30분마다 (09:00-15:30 KST)")
    print("  나스닥 마감: 매일 05:05 / 장 중 30분마다 (09:30-16:00 ET)")
    print("  명령어: /add /remove /watch /unwatch /list /help /news /kr /us /stock")

    poll_messages()


if __name__ == "__main__":
    main()
