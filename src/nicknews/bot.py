from apscheduler.schedulers.background import BackgroundScheduler

from .telegram import send_daily_news, send_kr_stocks, send_us_stocks, poll_messages


def main():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_daily_news, "cron", hour=9, minute=0)
    scheduler.add_job(send_kr_stocks, "cron", hour=15, minute=35)
    scheduler.add_job(send_us_stocks, "cron", hour=5, minute=5)
    scheduler.start()

    print("봇 실행 중 — 종료: Ctrl+C")
    print("  뉴스: 매일 09:00")
    print("  코스피 마감: 매일 15:35")
    print("  나스닥 마감: 매일 05:05")
    print("  명령어: /add /remove /watch /unwatch /list /help")

    poll_messages()


if __name__ == "__main__":
    main()
