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


class TestIsUsMarketOpen:
    def test_weekday_during_hours_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 15, 12, 0, tzinfo=EST)) is True

    def test_at_open_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 15, 9, 30, tzinfo=EST)) is True

    def test_at_close_is_open(self):
        assert is_us_market_open(datetime(2024, 1, 15, 16, 0, tzinfo=EST)) is True

    def test_before_open_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 15, 9, 29, tzinfo=EST)) is False

    def test_after_close_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 15, 16, 1, tzinfo=EST)) is False

    def test_saturday_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 13, 12, 0, tzinfo=EST)) is False

    def test_sunday_is_closed(self):
        assert is_us_market_open(datetime(2024, 1, 14, 12, 0, tzinfo=EST)) is False
