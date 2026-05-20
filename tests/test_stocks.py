from unittest.mock import MagicMock, patch

from nicknews.stocks import get_market, get_stock_line, search_ticker


def _naver_response(items):
    m = MagicMock()
    m.json.return_value = {"query": "test", "items": items}
    return m


def _yahoo_response(quotes):
    m = MagicMock()
    m.json.return_value = {"quotes": quotes}
    return m


# --- search_ticker ---

class TestSearchTickerKorean:
    def test_korean_query_calls_naver_api(self):
        with patch("nicknews.stocks.requests.get", return_value=_naver_response([
            {"code": "005930", "name": "삼성전자"}
        ])) as mock_get:
            ticker, name = search_ticker("삼성전자")
            url = mock_get.call_args[0][0]
            assert "ac.stock.naver.com" in url

    def test_kospi_stock_gets_KS_suffix(self):
        with patch("nicknews.stocks.requests.get", return_value=_naver_response([
            {"code": "005930", "name": "삼성전자", "typeCode": "KOSPI"}
        ])):
            ticker, name = search_ticker("삼성전자")
            assert ticker == "005930.KS"
            assert name == "삼성전자"

    def test_kosdaq_stock_gets_KQ_suffix(self):
        with patch("nicknews.stocks.requests.get", return_value=_naver_response([
            {"code": "035420", "name": "NAVER", "typeCode": "KOSDAQ"}
        ])):
            ticker, _ = search_ticker("네이버")
            assert ticker == "035420.KQ"

    def test_korean_no_results_returns_none(self):
        with patch("nicknews.stocks.requests.get", return_value=_naver_response([])):
            ticker, name = search_ticker("존재하지않는종목")
            assert ticker is None
            assert name is None

    def test_korean_api_error_returns_none(self):
        with patch("nicknews.stocks.requests.get", side_effect=Exception("timeout")):
            ticker, name = search_ticker("삼성전자")
            assert ticker is None
            assert name is None

    def test_korean_api_error_no_yahoo_fallback(self):
        with patch("nicknews.stocks.requests.get", side_effect=Exception("timeout")) as mock_get:
            search_ticker("삼성전자")
        assert mock_get.call_count == 1


class TestSearchTickerEnglish:
    def test_english_query_calls_yahoo_api(self):
        with patch("nicknews.stocks.requests.get", return_value=_yahoo_response([
            {"symbol": "AAPL", "shortname": "Apple Inc.", "quoteType": "EQUITY"}
        ])) as mock_get:
            search_ticker("AAPL")
            url = mock_get.call_args[0][0]
            assert "finance.yahoo.com" in url

    def test_english_query_returns_ticker(self):
        with patch("nicknews.stocks.requests.get", return_value=_yahoo_response([
            {"symbol": "AAPL", "shortname": "Apple Inc.", "quoteType": "EQUITY"}
        ])):
            ticker, name = search_ticker("AAPL")
            assert ticker == "AAPL"
            assert name == "Apple Inc."

    def test_non_equity_quotes_are_skipped(self):
        with patch("nicknews.stocks.requests.get", return_value=_yahoo_response([
            {"symbol": "AAPL-USD", "shortname": "AAPL USD", "quoteType": "CURRENCY"},
            {"symbol": "AAPL", "shortname": "Apple Inc.", "quoteType": "EQUITY"},
        ])):
            ticker, name = search_ticker("AAPL")
            assert ticker == "AAPL"

    def test_english_no_results_returns_none(self):
        with patch("nicknews.stocks.requests.get", return_value=_yahoo_response([])):
            ticker, name = search_ticker("ZZZZZ")
            assert ticker is None
            assert name is None

    def test_falls_back_to_longname_when_shortname_missing(self):
        with patch("nicknews.stocks.requests.get", return_value=_yahoo_response([
            {"symbol": "NVDA", "shortname": None, "longname": "NVIDIA Corporation", "quoteType": "EQUITY"}
        ])):
            ticker, name = search_ticker("nvidia")
            assert name == "NVIDIA Corporation"


# --- get_market ---

class TestGetMarket:
    def test_kospi_exchange_returns_kr(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value.info = {"exchange": "KSC"}
            assert get_market("005930.KS") == "kr"

    def test_kosdaq_exchange_returns_kr(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value.info = {"exchange": "KOE"}
            assert get_market("035720.KS") == "kr"

    def test_nasdaq_exchange_returns_us(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value.info = {"exchange": "NMS"}
            assert get_market("AAPL") == "us"

    def test_error_returns_us(self):
        with patch("nicknews.stocks.yf.Ticker", side_effect=Exception("network error")):
            assert get_market("AAPL") == "us"


# --- get_stock_line ---

class TestGetStockLine:
    def _mock_fast_info(self, last_price, previous_close):
        fast_info = MagicMock()
        fast_info.last_price = last_price
        fast_info.previous_close = previous_close
        mock_ticker = MagicMock()
        mock_ticker.fast_info = fast_info
        return mock_ticker

    def test_price_up_shows_up_arrow(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_fast_info(70000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert line.startswith("▲")

    def test_price_down_shows_down_arrow(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_fast_info(66000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert line.startswith("▼")

    def test_output_contains_name_and_price(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_fast_info(70000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert "삼성전자" in line
            assert "70,000" in line

    def test_error_returns_failure_message(self):
        with patch("nicknews.stocks.yf.Ticker", side_effect=Exception("timeout")):
            line = get_stock_line("삼성전자", "005930.KS")
            assert "삼성전자" in line
            assert "데이터 조회 실패" in line
