from datetime import date
from unittest.mock import call, patch

from nicknews.notify import send_daily_news, send_flight_prices, send_kr_stocks, send_us_stocks


class TestSendDailyNews:
    def test_sends_to_given_chat_id(self):
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.load_user_stocks", return_value={"keywords": []}), \
             patch("nicknews.notify.fetch_rss", return_value=[]), \
             patch("nicknews.notify.format_section", return_value=""):
            send_daily_news(chat_id="111")
        mock_send.assert_called_once()
        assert mock_send.call_args[0][1] == "111"

    def test_sends_to_all_users_when_no_chat_id(self):
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111", "222"}), \
             patch("nicknews.notify.load_user_stocks", return_value={"keywords": []}), \
             patch("nicknews.notify.fetch_rss", return_value=[]), \
             patch("nicknews.notify.format_section", return_value=""):
            send_daily_news()
        assert mock_send.call_count == 2

    def test_includes_keyword_sections(self):
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.load_user_stocks", return_value={"keywords": ["AI", "반도체"]}), \
             patch("nicknews.notify.fetch_rss", return_value=[]), \
             patch("nicknews.notify.fetch_keyword_news", return_value=[]) as mock_kw, \
             patch("nicknews.notify.format_section", return_value=""):
            send_daily_news(chat_id="111")
        assert mock_kw.call_count == 2


class TestSendKrStocks:
    def test_skips_user_with_no_kr_stocks(self):
        with patch("nicknews.notify.send_message") as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value={"kr": [], "us": [], "keywords": []}):
            send_kr_stocks()
        mock_send.assert_not_called()

    def test_sends_for_user_with_kr_stocks(self):
        stocks = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value="▲ 삼성전자  70,000"):
            send_kr_stocks()
        mock_send.assert_called_once()
        assert "111" == mock_send.call_args[0][1]

    def test_intraday_header(self):
        stocks = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value=""), \
             patch("nicknews.notify.is_significant", return_value=True), \
             patch("nicknews.notify.is_kr_market_open", return_value=True):
            send_kr_stocks(intraday=True)
        assert "장 중" in mock_send.call_args[0][0]

    def test_closing_header(self):
        stocks = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value=""), \
             patch("nicknews.notify.is_kr_market_open", return_value=False):
            send_kr_stocks(intraday=False)
        assert "마감" in mock_send.call_args[0][0]


class TestSendUsStocks:
    def test_skips_user_with_no_us_stocks(self):
        with patch("nicknews.notify.send_message") as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value={"kr": [], "us": [], "keywords": []}):
            send_us_stocks()
        mock_send.assert_not_called()

    def test_sends_for_user_with_us_stocks(self):
        stocks = {"kr": [], "us": [{"name": "Apple Inc.", "ticker": "AAPL"}], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value="▲ Apple Inc.  200"):
            send_us_stocks()
        mock_send.assert_called_once()

    def test_intraday_header(self):
        stocks = {"kr": [], "us": [{"name": "Apple Inc.", "ticker": "AAPL"}], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value=""), \
             patch("nicknews.notify.is_significant", return_value=True), \
             patch("nicknews.notify.is_us_market_open", return_value=True):
            send_us_stocks(intraday=True)
        assert "장 중" in mock_send.call_args[0][0]


class TestIntradayFiltering:
    def test_kr_intraday_skips_insignificant_stocks(self):
        stocks = {"kr": [
            {"name": "삼성전자", "ticker": "005930.KS"},
            {"name": "SK하이닉스", "ticker": "000660.KS"},
        ], "us": [], "keywords": []}
        with patch("nicknews.notify.send_message") as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value=""), \
             patch("nicknews.notify.is_significant", return_value=False):
            send_kr_stocks(intraday=True)
        mock_send.assert_not_called()

    def test_kr_intraday_sends_only_significant_stocks(self):
        stocks = {"kr": [
            {"name": "삼성전자", "ticker": "005930.KS"},
            {"name": "SK하이닉스", "ticker": "000660.KS"},
        ], "us": [], "keywords": []}
        significant_tickers = []

        def _sig(ticker):
            return ticker == "005930.KS"

        def _line(name, ticker):
            significant_tickers.append(ticker)
            return f"line:{ticker}"

        with patch("nicknews.notify.send_message", return_value={"ok": True}), \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", side_effect=_line), \
             patch("nicknews.notify.is_significant", side_effect=_sig):
            send_kr_stocks(intraday=True)
        assert significant_tickers == ["005930.KS"]

    def test_us_intraday_skips_insignificant_stocks(self):
        stocks = {"kr": [], "us": [{"name": "Apple Inc.", "ticker": "AAPL"}], "keywords": []}
        with patch("nicknews.notify.send_message") as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.is_significant", return_value=False):
            send_us_stocks(intraday=True)
        mock_send.assert_not_called()

    def test_non_intraday_sends_all_stocks(self):
        stocks = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value="line"), \
             patch("nicknews.notify.is_significant", return_value=False) as mock_sig:
            send_kr_stocks(intraday=False)
        mock_send.assert_called_once()
        mock_sig.assert_not_called()


class TestSendFlightPrices:
    def _flight(self, history=None):
        return {
            "origin": "ICN", "origin_name": "인천", "destination": "NRT", "destination_name": "나리타",
            "depart": "260901", "return": "260908", "history": history or [],
        }

    def test_skips_user_with_no_flights(self):
        with patch("nicknews.notify.send_message") as mock_send, \
             patch("nicknews.notify.save_user_stocks") as mock_save, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value={"flights": []}):
            send_flight_prices()
        mock_send.assert_not_called()
        mock_save.assert_not_called()

    def test_sends_price_for_each_flight(self):
        data = {"flights": [self._flight()]}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.save_user_stocks"), \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=data), \
             patch("nicknews.notify.get_flight_price", return_value={"price": 380000, "offers": []}), \
             patch("nicknews.notify.format_flight_price_message", return_value="✈️ 인천 → 나리타"):
            send_flight_prices()
        mock_send.assert_called_once()
        assert mock_send.call_args[0][1] == "111"

    def test_appends_today_to_history_and_saves(self):
        data = {"flights": [self._flight()]}
        with patch("nicknews.notify.send_message", return_value={"ok": True}), \
             patch("nicknews.notify.save_user_stocks") as mock_save, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=data), \
             patch("nicknews.notify.get_flight_price", return_value={"price": 380000, "offers": []}), \
             patch("nicknews.flights.date") as mock_date:
            mock_date.today.return_value = date(2026, 8, 29)
            send_flight_prices()
        saved_flight = mock_save.call_args[0][1]["flights"][0]
        assert saved_flight["history"] == [{"date": "260829", "price": 380000}]

    def test_overwrites_existing_entry_for_today(self):
        data = {"flights": [self._flight(history=[{"date": "260829", "price": 400000}])]}
        with patch("nicknews.notify.send_message", return_value={"ok": True}), \
             patch("nicknews.notify.save_user_stocks") as mock_save, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=data), \
             patch("nicknews.notify.get_flight_price", return_value={"price": 380000, "offers": []}), \
             patch("nicknews.flights.date") as mock_date:
            mock_date.today.return_value = date(2026, 8, 29)
            send_flight_prices()
        history = mock_save.call_args[0][1]["flights"][0]["history"]
        assert history == [{"date": "260829", "price": 380000}]

    def test_price_lookup_failure_skips_send_and_save(self):
        data = {"flights": [self._flight()]}
        with patch("nicknews.notify.send_message") as mock_send, \
             patch("nicknews.notify.save_user_stocks") as mock_save, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=data), \
             patch("nicknews.notify.get_flight_price", return_value=None):
            send_flight_prices()
        mock_send.assert_not_called()
        mock_save.assert_not_called()

    def test_sends_to_given_chat_id_only(self):
        data = {"flights": [self._flight()]}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.save_user_stocks"), \
             patch("nicknews.notify.load_user_stocks", return_value=data), \
             patch("nicknews.notify.get_flight_price", return_value={"price": 380000, "offers": []}):
            send_flight_prices(chat_id="222")
        assert mock_send.call_args[0][1] == "222"
