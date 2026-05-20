from unittest.mock import call, patch

from nicknews.notify import send_daily_news, send_kr_stocks, send_us_stocks


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
             patch("nicknews.notify.get_stock_line", return_value=""):
            send_kr_stocks(intraday=True)
        assert "장 중" in mock_send.call_args[0][0]

    def test_closing_header(self):
        stocks = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.notify.send_message", return_value={"ok": True}) as mock_send, \
             patch("nicknews.notify.all_user_ids", return_value={"111"}), \
             patch("nicknews.notify.load_user_stocks", return_value=stocks), \
             patch("nicknews.notify.get_stock_line", return_value=""):
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
             patch("nicknews.notify.get_stock_line", return_value=""):
            send_us_stocks(intraday=True)
        assert "장 중" in mock_send.call_args[0][0]
