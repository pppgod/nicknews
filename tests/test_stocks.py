from unittest.mock import MagicMock, patch

import pandas as pd

from nicknews.stocks import get_market, get_stock_detail, get_stock_line, is_significant, search_ticker


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
    def _mock_ticker(self, last_price, previous_close, last_volume=1_000_000,
                     volumes=None, closes=None):
        fast_info = MagicMock()
        fast_info.last_price = last_price
        fast_info.previous_close = previous_close
        fast_info.last_volume = last_volume
        mock_ticker = MagicMock()
        mock_ticker.fast_info = fast_info
        n = max(len(volumes or []), len(closes or []))
        mock_ticker.history.return_value = pd.DataFrame({
            "Volume": volumes if volumes is not None else [0] * n,
            "Close": closes if closes is not None else [0.0] * n,
        })
        return mock_ticker

    def test_price_up_shows_up_arrow(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert line.startswith("🔺")

    def test_price_down_shows_down_arrow(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(66000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert line.startswith("▼")

    def test_output_contains_name_and_price(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert "삼성전자" in line
            assert "70,000" in line

    def test_output_contains_volume(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, 5_500_000)):
            line = get_stock_line("삼성전자", "005930.KS")
            assert "5.5M" in line

    def test_price_yesterday_change_shown(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert "전일 🔺+2.94%" in line

    def test_price_weekly_change_shown(self):
        closes = [60000.0] * 5
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, closes=closes)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert "1주전" in line
        assert "+16.67%" in line

    def test_price_weekly_not_shown_with_fewer_than_5_days(self):
        closes = [68000.0, 68000.0]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, closes=closes)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert line.count("1주전") == 0

    def test_volume_yesterday_change(self):
        vols = [4_000_000, 5_000_000]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, 5_000_000, volumes=vols)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert "전일" in line
        assert "+25.00%" in line

    def test_volume_weekly_change(self):
        vols = [2_000_000, 3_000_000, 4_000_000, 4_500_000, 5_000_000]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, 5_000_000, volumes=vols)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert line.count("1주전") >= 1
        assert "+150.00%" in line

    def test_volume_weekly_not_shown_with_fewer_than_5_days(self):
        vols = [4_000_000, 5_000_000]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, 5_000_000, volumes=vols)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert line.count("1주전") == 0

    def test_volume_down_shows_down_arrow(self):
        vols = [4_000_000, 3_000_000]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(70000, 68000, 3_000_000, volumes=vols)):
            line = get_stock_line("삼성전자", "005930.KS")
        assert "전일 ▼-25.00%" in line

    def test_error_returns_failure_message(self):
        with patch("nicknews.stocks.yf.Ticker", side_effect=Exception("timeout")):
            line = get_stock_line("삼성전자", "005930.KS")
            assert "삼성전자" in line
            assert "데이터 조회 실패" in line


# --- get_stock_detail ---

class TestGetStockDetail:
    def _mock_ticker(self, current_price, volume, hist_closes, hist_volumes=None):
        mock_stock = MagicMock()
        mock_stock.fast_info.last_price = current_price
        mock_stock.fast_info.last_volume = volume
        n = len(hist_closes)
        mock_stock.history.return_value = pd.DataFrame({
            "Close": hist_closes,
            "Volume": hist_volumes if hist_volumes is not None else [volume] * n,
        })
        return mock_stock

    def test_shows_current_price(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(110.0, 1_000_000, [100.0] * 70)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "110" in result

    def test_shows_volume_in_M(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(110.0, 5_500_000, [100.0] * 70)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "5.5M" in result

    def test_shows_all_period_labels(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(110.0, 1_000_000, [100.0] * 70)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "1주 전" in result
        assert "1개월 전" in result
        assert "3개월 전" in result

    def test_up_arrow_when_price_higher_than_history(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(110.0, 1_000_000, [100.0] * 70)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "🔺" in result

    def test_down_arrow_when_price_lower_than_history(self):
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(90.0, 1_000_000, [100.0] * 70)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "▼" in result

    def test_shows_volume_change_per_period(self):
        hist_vols = [2_000_000] * 70
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(110.0, 5_000_000, [100.0] * 70, hist_vols)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "2.0M" in result

    def test_shows_volume_yesterday_change(self):
        hist_vols = [2_000_000] * 69 + [4_000_000]
        with patch("nicknews.stocks.yf.Ticker") as mock_yf:
            mock_yf.return_value = self._mock_ticker(110.0, 5_000_000, [100.0] * 70, hist_vols)
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "+25.00%" in result

    def test_error_returns_failure_message(self):
        with patch("nicknews.stocks.yf.Ticker", side_effect=Exception("network error")):
            result = get_stock_detail("Apple Inc.", "AAPL")
        assert "조회 실패" in result


# --- is_significant ---

class TestIsSignificant:
    def _mock_ticker(self, current, prev_close, volume, hist_closes, hist_volumes):
        mock_stock = MagicMock()
        mock_stock.fast_info.last_price = current
        mock_stock.fast_info.previous_close = prev_close
        mock_stock.fast_info.last_volume = volume
        mock_stock.history.return_value = pd.DataFrame({
            "Close": hist_closes,
            "Volume": hist_volumes,
        })
        return mock_stock

    def _flat_history(self, price=100.0, volume=1_000_000, n=21):
        return [price] * n, [volume] * n

    def test_price_above_threshold_returns_true(self):
        closes, vols = self._flat_history()
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            103.0, 100.0, 1_000_000, closes, vols
        )):
            assert is_significant("AAPL") is True

    def test_price_below_threshold_returns_false(self):
        closes, vols = self._flat_history()
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            101.0, 100.0, 1_000_000, closes, vols
        )):
            assert is_significant("AAPL") is False

    def test_volume_above_threshold_returns_true(self):
        closes, vols = self._flat_history(volume=1_000_000)
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            101.0, 100.0, 2_000_000, closes, vols
        )):
            assert is_significant("AAPL") is True

    def test_price_zscore_above_threshold_returns_true(self):
        # std ≈ 0.001%, price_pct = 1.5% → zscore >> 2, below price threshold
        vols = [1_000_000] * 20
        closes = [100.0 + i * 0.001 for i in range(20)]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            101.5, 100.0, 1_000_000, closes, vols
        )):
            assert is_significant("AAPL") is True

    def test_volume_zscore_above_threshold_returns_true(self):
        closes = [100.0] * 20
        # volumes with tiny std, then today's volume is huge
        vols = [1_000_000 + i * 100 for i in range(20)]
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            101.0, 100.0, 10_000_000, closes, vols
        )):
            assert is_significant("AAPL") is True

    def test_insufficient_history_returns_true(self):
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            100.0, 100.0, 1_000_000, [100.0] * 3, [1_000_000] * 3
        )):
            assert is_significant("AAPL") is True

    def test_error_returns_true(self):
        with patch("nicknews.stocks.yf.Ticker", side_effect=Exception("network error")):
            assert is_significant("AAPL") is True

    def test_zero_volume_avg_does_not_crash(self):
        closes = [100.0] * 21
        vols = [0] * 21
        with patch("nicknews.stocks.yf.Ticker", return_value=self._mock_ticker(
            101.0, 100.0, 0, closes, vols
        )):
            result = is_significant("AAPL")
            assert isinstance(result, bool)
