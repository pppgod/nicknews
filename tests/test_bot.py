from datetime import datetime
from zoneinfo import ZoneInfo

from nicknews.bot import is_kr_market_open, is_us_market_open

KST = ZoneInfo("Asia/Seoul")
EST = ZoneInfo("America/New_York")


class TestIsKrMarketOpen:
    def test_weekday_during_hours_is_open(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 10, 0, tzinfo=KST)) is True

    def test_at_open_is_open(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 9, 0, tzinfo=KST)) is True

    def test_before_open_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 8, 59, tzinfo=KST)) is False

    def test_after_close_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 15, 31, tzinfo=KST)) is False

    def test_saturday_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 13, 10, 0, tzinfo=KST)) is False

    def test_sunday_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 14, 10, 0, tzinfo=KST)) is False

    def test_new_years_day_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 1, 10, 0, tzinfo=KST)) is False

    def test_liberation_day_is_closed(self):
        # 2024-08-15 목요일 — 광복절
        assert is_kr_market_open(datetime(2024, 8, 15, 10, 0, tzinfo=KST)) is False

    def test_substitute_holiday_is_closed(self):
        # 어린이날(5/5 일요일) → 대체공휴일 5/6(월)
        assert is_kr_market_open(datetime(2024, 5, 6, 10, 0, tzinfo=KST)) is False

    def test_normal_weekday_not_holiday_is_open(self):
        assert is_kr_market_open(datetime(2024, 1, 2, 10, 0, tzinfo=KST)) is True


class TestIsUsMarketOpen:
    def test_weekday_during_hours_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 16, 12, 0, tzinfo=EST)) is True

    def test_at_open_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 16, 9, 30, tzinfo=EST)) is True

    def test_before_open_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 16, 9, 29, tzinfo=EST)) is False

    def test_after_close_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 16, 16, 1, tzinfo=EST)) is False

    def test_saturday_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 13, 12, 0, tzinfo=EST)) is False

    def test_sunday_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 14, 12, 0, tzinfo=EST)) is False

    def test_mlk_day_is_closed(self):
        # 2024-01-15 월요일 — Martin Luther King Jr. Day
        assert is_us_market_open(datetime(2024, 1, 15, 12, 0, tzinfo=EST)) is False

    def test_good_friday_is_closed(self):
        # 2024-03-29 금요일 — Good Friday (연방 공휴일 아님, NYSE만 휴장)
        assert is_us_market_open(datetime(2024, 3, 29, 12, 0, tzinfo=EST)) is False

    def test_black_friday_before_early_close_is_open(self):
        # 2024-11-29 — Black Friday, 13:00 ET 조기폐장
        assert is_us_market_open(datetime(2024, 11, 29, 10, 0, tzinfo=EST)) is True

    def test_black_friday_after_early_close_is_closed(self):
        assert is_us_market_open(datetime(2024, 11, 29, 14, 0, tzinfo=EST)) is False

    def test_july3_before_early_close_is_open(self):
        # 2024-07-03 — 독립기념일 전날 조기폐장 (13:00 ET)
        assert is_us_market_open(datetime(2024, 7, 3, 10, 0, tzinfo=EST)) is True

    def test_july3_after_early_close_is_closed(self):
        assert is_us_market_open(datetime(2024, 7, 3, 14, 0, tzinfo=EST)) is False

    def test_dst_summer_open(self):
        # 2024-07-15 (EDT 기간) — DST 자동 처리 확인
        assert is_us_market_open(datetime(2024, 7, 15, 12, 0, tzinfo=EST)) is True

    def test_dst_winter_open(self):
        # 2024-01-16 (EST 기간)
        assert is_us_market_open(datetime(2024, 1, 16, 12, 0, tzinfo=EST)) is True
