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

    def test_at_close_is_open(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 15, 30, tzinfo=KST)) is True

    def test_before_open_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 8, 59, tzinfo=KST)) is False

    def test_after_close_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 15, 15, 31, tzinfo=KST)) is False

    def test_saturday_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 13, 10, 0, tzinfo=KST)) is False

    def test_sunday_is_closed(self):
        assert is_kr_market_open(datetime(2024, 1, 14, 10, 0, tzinfo=KST)) is False

    def test_new_years_day_is_closed(self):
        # 2024-01-01 월요일 — 공휴일
        assert is_kr_market_open(datetime(2024, 1, 1, 10, 0, tzinfo=KST)) is False

    def test_liberation_day_is_closed(self):
        # 2024-08-15 목요일 — 광복절
        assert is_kr_market_open(datetime(2024, 8, 15, 10, 0, tzinfo=KST)) is False

    def test_normal_weekday_not_holiday_is_open(self):
        # 2024-01-02 화요일 — 평일
        assert is_kr_market_open(datetime(2024, 1, 2, 10, 0, tzinfo=KST)) is True


class TestIsUsMarketOpen:
    def test_weekday_during_hours_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 16, 12, 0, tzinfo=EST)) is True

    def test_at_open_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 16, 9, 30, tzinfo=EST)) is True

    def test_at_close_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 16, 16, 0, tzinfo=EST)) is True

    def test_before_open_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 16, 9, 29, tzinfo=EST)) is False

    def test_after_close_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 16, 16, 1, tzinfo=EST)) is False

    def test_saturday_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 13, 12, 0, tzinfo=EST)) is False

    def test_sunday_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 14, 12, 0, tzinfo=EST)) is False

    def test_nyse_holiday_is_closed(self):
        # 2024-01-15 월요일 — Martin Luther King Jr. Day
        assert is_us_market_open(datetime(2024, 1, 15, 12, 0, tzinfo=EST)) is False

    def test_good_friday_is_closed(self):
        # 2024-03-29 금요일 — Good Friday (NYSE 휴장, 연방 공휴일 아님)
        assert is_us_market_open(datetime(2024, 3, 29, 12, 0, tzinfo=EST)) is False

    def test_dst_summer_open(self):
        # 2024-07-15 월요일 10:00 EDT — 서머타임 기간, 장 중
        assert is_us_market_open(datetime(2024, 7, 15, 10, 0, tzinfo=EST)) is True

    def test_dst_winter_open(self):
        # 2024-01-16 화요일 10:00 EST — 표준시 기간, 장 중
        assert is_us_market_open(datetime(2024, 1, 16, 10, 0, tzinfo=EST)) is True

    def test_dst_transition_day(self):
        # 2024-03-10 일요일 — DST 시작일, 주말이므로 휴장
        assert is_us_market_open(datetime(2024, 3, 10, 10, 0, tzinfo=EST)) is False
