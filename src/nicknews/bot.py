import os
from datetime import datetime
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from .notify import send_daily_news, send_kr_stocks, send_us_stocks
from .telegram import poll_messages

KST = ZoneInfo("Asia/Seoul")
# ZoneInfo("America/New_York") switches between EST(UTC-5) and EDT(UTC-4) automatically
EST = ZoneInfo("America/New_York")

_KR_CAL = xcals.get_calendar("XKRX")
_US_CAL = xcals.get_calendar("XNYS")


def is_kr_market_open(now=None):
    if now is None:
        now = datetime.now(KST)
    return bool(_KR_CAL.is_open_at_time(pd.Timestamp(now)))


def is_us_market_open(now=None):
    if now is None:
        now = datetime.now(EST)
    return bool(_US_CAL.is_open_at_time(pd.Timestamp(now)))


def _send_kr_if_open():
    if is_kr_market_open():
        send_kr_stocks(intraday=True)


def _send_us_if_open():
    if is_us_market_open():
        send_us_stocks(intraday=True)


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
    print("  코스피 마감: 매일 15:35 / 장 중 30분마다 (공휴일·대체공휴일 제외)")
    print("  나스닥 마감: 매일 05:05 / 장 중 30분마다 (NYSE 휴장일·조기폐장 반영)")
    print("  명령어: /add /remove /watch /unwatch /list /help /news /kr /us /stock")

    poll_messages()


if __name__ == "__main__":
    main()
