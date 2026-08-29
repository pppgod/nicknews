from unittest.mock import patch

import pytest

from nicknews.commands import (
    cmd_add,
    cmd_addflight,
    cmd_allow,
    cmd_disallow,
    cmd_flight,
    cmd_flights,
    cmd_kr,
    cmd_list,
    cmd_news,
    cmd_remove,
    cmd_removeflight,
    cmd_stock,
    cmd_unwatch,
    cmd_us,
    cmd_watch,
    handle_command,
)

DEFAULT_DATA = {"kr": [], "us": [], "keywords": []}


def _default_flight_data():
    return {"kr": [], "us": [], "keywords": [], "flights": []}


def _messages(mock_send):
    return [call[0][0] for call in mock_send.call_args_list]


class TestCmdAdd:
    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_add(["/add"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_ticker_not_found_sends_error(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.search_ticker", return_value=(None, None)), \
             patch("nicknews.commands.load_user_stocks", return_value=dict(DEFAULT_DATA)):
            cmd_add(["/add", "없는종목"])
        assert any("찾을 수 없습니다" in m for m in _messages(mock_send))

    def test_korean_stock_saved_to_kr(self):
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.search_ticker", return_value=("005930.KS", "삼성전자")), \
             patch("nicknews.commands.get_market", return_value="kr"), \
             patch("nicknews.commands.load_user_stocks", return_value={"kr": [], "us": [], "keywords": []}), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_add(["/add", "삼성전자"])
        saved = mock_save.call_args[0][1]
        assert {"name": "삼성전자", "ticker": "005930.KS"} in saved["kr"]

    def test_us_stock_saved_to_us(self):
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.search_ticker", return_value=("AAPL", "Apple Inc.")), \
             patch("nicknews.commands.get_market", return_value="us"), \
             patch("nicknews.commands.load_user_stocks", return_value={"kr": [], "us": [], "keywords": []}), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_add(["/add", "AAPL"])
        saved = mock_save.call_args[0][1]
        assert {"name": "Apple Inc.", "ticker": "AAPL"} in saved["us"]

    def test_duplicate_stock_not_saved(self):
        existing = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.search_ticker", return_value=("005930.KS", "삼성전자")), \
             patch("nicknews.commands.get_market", return_value="kr"), \
             patch("nicknews.commands.load_user_stocks", return_value=existing), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_add(["/add", "삼성전자"])
        mock_save.assert_not_called()
        assert any("이미 등록" in m for m in _messages(mock_send))

    def test_success_sends_confirmation(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.search_ticker", return_value=("AAPL", "Apple Inc.")), \
             patch("nicknews.commands.get_market", return_value="us"), \
             patch("nicknews.commands.load_user_stocks", return_value={"kr": [], "us": [], "keywords": []}), \
             patch("nicknews.commands.save_user_stocks"):
            cmd_add(["/add", "AAPL"])
        assert any("Apple Inc." in m for m in _messages(mock_send))


class TestCmdRemove:
    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_remove(["/remove"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_removes_registered_stock(self):
        data = {"kr": [{"name": "삼성전자", "ticker": "005930.KS"}], "us": [], "keywords": []}
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_remove(["/remove", "005930.KS"])
        saved = mock_save.call_args[0][1]
        assert saved["kr"] == []

    def test_ticker_removal_case_insensitive(self):
        data = {"kr": [], "us": [{"name": "Apple Inc.", "ticker": "AAPL"}], "keywords": []}
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_remove(["/remove", "aapl"])
        saved = mock_save.call_args[0][1]
        assert saved["us"] == []

    def test_unknown_ticker_not_saved(self):
        data = {"kr": [], "us": [], "keywords": []}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_remove(["/remove", "AAPL"])
        mock_save.assert_not_called()
        assert "등록되지 않은" in mock_send.call_args[0][0]


class TestCmdWatch:
    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_watch(["/watch"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_adds_new_keyword(self):
        data = {"kr": [], "us": [], "keywords": []}
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_watch(["/watch", "엔비디아"])
        saved = mock_save.call_args[0][1]
        assert "엔비디아" in saved["keywords"]

    def test_duplicate_keyword_not_saved(self):
        data = {"kr": [], "us": [], "keywords": ["엔비디아"]}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_watch(["/watch", "엔비디아"])
        mock_save.assert_not_called()
        assert "이미 등록" in mock_send.call_args[0][0]


class TestCmdUnwatch:
    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_unwatch(["/unwatch"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_removes_keyword(self):
        data = {"kr": [], "us": [], "keywords": ["엔비디아"]}
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_unwatch(["/unwatch", "엔비디아"])
        saved = mock_save.call_args[0][1]
        assert "엔비디아" not in saved["keywords"]

    def test_unknown_keyword_not_saved(self):
        data = {"kr": [], "us": [], "keywords": []}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_unwatch(["/unwatch", "엔비디아"])
        mock_save.assert_not_called()
        assert "등록되지 않은" in mock_send.call_args[0][0]


class TestCmdList:
    def test_empty_list_shows_none_message(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=DEFAULT_DATA):
            cmd_list(["/list"])
        msg = mock_send.call_args[0][0]
        assert msg.count("없음") == 3

    def test_registered_items_appear_in_list(self):
        data = {
            "kr": [{"name": "삼성전자", "ticker": "005930.KS"}],
            "us": [{"name": "Apple Inc.", "ticker": "AAPL"}],
            "keywords": ["AI"],
        }
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data):
            cmd_list(["/list"])
        msg = mock_send.call_args[0][0]
        assert "삼성전자" in msg
        assert "Apple Inc." in msg
        assert "AI" in msg


class TestCmdNews:
    def test_calls_send_daily_news(self):
        with patch("nicknews.commands.send_daily_news") as mock:
            cmd_news(["/news"])
        mock.assert_called_once()


class TestCmdKr:
    def test_calls_send_kr_stocks(self):
        with patch("nicknews.commands.send_kr_stocks") as mock:
            cmd_kr(["/kr"])
        mock.assert_called_once()

    def test_always_non_intraday(self):
        with patch("nicknews.commands.send_kr_stocks") as mock:
            cmd_kr(["/kr"])
        assert mock.call_args.kwargs["intraday"] is False


class TestCmdUs:
    def test_calls_send_us_stocks(self):
        with patch("nicknews.commands.send_us_stocks") as mock:
            cmd_us(["/us"])
        mock.assert_called_once()

    def test_always_non_intraday(self):
        with patch("nicknews.commands.send_us_stocks") as mock:
            cmd_us(["/us"])
        assert mock.call_args.kwargs["intraday"] is False


class TestCmdStock:
    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_stock(["/stock"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_ticker_not_found_sends_error(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.search_ticker", return_value=(None, None)):
            cmd_stock(["/stock", "없는종목"])
        assert any("찾을 수 없습니다" in m for m in _messages(mock_send))

    def test_valid_ticker_sends_price(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.search_ticker", return_value=("AAPL", "Apple Inc.")), \
             patch("nicknews.commands.get_stock_detail", return_value="📊 <b>Apple Inc.</b> (AAPL)\n현재가 ▲ 200"):
            cmd_stock(["/stock", "AAPL"])
        assert any("Apple Inc." in m for m in _messages(mock_send))

    def test_multiword_query_joined(self):
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.search_ticker", return_value=("NVDA", "NVIDIA")) as mock_search, \
             patch("nicknews.commands.get_stock_detail", return_value="📊 <b>NVIDIA</b> (NVDA)"):
            cmd_stock(["/stock", "nvidia", "corp"])
        mock_search.assert_called_once_with("nvidia corp")


class TestHandleCommand:
    def test_unknown_command_is_ignored(self):
        with patch("nicknews.commands.send_message") as mock_send:
            handle_command("/unknown")
        mock_send.assert_not_called()

    def test_empty_text_is_ignored(self):
        with patch("nicknews.commands.send_message") as mock_send:
            handle_command("  ")
        mock_send.assert_not_called()

    def test_command_with_bot_name_is_handled(self):
        with patch("nicknews.commands.send_message") as mock_send:
            handle_command("/help@mybot")
        mock_send.assert_called_once()

    def test_uppercase_command_is_handled(self):
        with patch("nicknews.commands.send_message") as mock_send:
            handle_command("/HELP")
        mock_send.assert_called_once()


class TestCmdAddflight:
    RESOLVED = ("ICN", "인천", "NRT", "나리타")

    def test_too_few_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_addflight(["/addflight", "인천", "도쿄"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_invalid_depart_date_sends_error(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_addflight(["/addflight", "인천", "도쿄", "abc"])
        assert any("가는 날짜" in m for m in _messages(mock_send))

    def test_past_depart_date_rejected(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_addflight(["/addflight", "인천", "도쿄", "200101"])
        assert any("이미 지났습니다" in m for m in _messages(mock_send))

    def test_invalid_return_date_sends_error(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_addflight(["/addflight", "인천", "도쿄", "260901", "abc"])
        assert any("오는 날짜" in m for m in _messages(mock_send))

    def test_return_before_depart_rejected(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_addflight(["/addflight", "인천", "도쿄", "260908", "260901"])
        assert any("가는 날짜보다 빠릅니다" in m for m in _messages(mock_send))

    def test_airport_not_found_sends_error(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.resolve_route", return_value=None):
            cmd_addflight(["/addflight", "없는곳", "도쿄", "260901"])
        assert any("공항을 찾을 수 없습니다" in m for m in _messages(mock_send))

    def test_success_saves_flight_and_history(self):
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.resolve_route", return_value=self.RESOLVED), \
             patch("nicknews.commands.get_flight_price", return_value={"price": 380000, "offers": []}), \
             patch("nicknews.commands.load_user_stocks", return_value=_default_flight_data()), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_addflight(["/addflight", "인천", "도쿄", "260901", "260908"])
        saved = mock_save.call_args[0][1]
        flight = saved["flights"][0]
        assert flight["origin"] == "ICN"
        assert flight["destination"] == "NRT"
        assert flight["depart"] == "260901"
        assert flight["return"] == "260908"
        assert flight["history"] == [{"date": flight["history"][0]["date"], "price": 380000}]

    def test_one_way_has_no_return(self):
        with patch("nicknews.commands.send_message"), \
             patch("nicknews.commands.resolve_route", return_value=self.RESOLVED), \
             patch("nicknews.commands.get_flight_price", return_value={"price": 100000, "offers": []}), \
             patch("nicknews.commands.load_user_stocks", return_value=_default_flight_data()), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_addflight(["/addflight", "인천", "도쿄", "260901"])
        assert mock_save.call_args[0][1]["flights"][0]["return"] is None

    def test_price_lookup_failure_still_saves_without_history(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.resolve_route", return_value=self.RESOLVED), \
             patch("nicknews.commands.get_flight_price", return_value=None), \
             patch("nicknews.commands.load_user_stocks", return_value=_default_flight_data()), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_addflight(["/addflight", "인천", "도쿄", "260901"])
        assert mock_save.call_args[0][1]["flights"][0]["history"] == []
        assert any("조회 실패" in m for m in _messages(mock_send))


class TestCmdRemoveflight:
    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_removeflight(["/removeflight"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_non_numeric_arg_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_removeflight(["/removeflight", "abc"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_out_of_range_index_sends_error(self):
        data = _default_flight_data()
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data):
            cmd_removeflight(["/removeflight", "1"])
        assert any("등록되지 않은 번호" in m for m in _messages(mock_send))

    def test_removes_by_index(self):
        flight = {"origin": "ICN", "origin_name": "인천", "destination": "NRT", "destination_name": "나리타"}
        data = {"kr": [], "us": [], "keywords": [], "flights": [flight]}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_removeflight(["/removeflight", "1"])
        assert mock_save.call_args[0][1]["flights"] == []
        assert any("인천 → 나리타" in m for m in _messages(mock_send))


class TestCmdFlights:
    def test_empty_list_shows_message(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=_default_flight_data()):
            cmd_flights(["/flights"])
        assert "추적 중인 항공권이 없습니다" in mock_send.call_args[0][0]

    def test_lists_registered_flights_with_last_price(self):
        flight = {
            "origin": "ICN", "origin_name": "인천", "destination": "NRT", "destination_name": "나리타",
            "depart": "260901", "return": "260908",
            "history": [{"date": "260828", "price": 380000}],
        }
        data = {"kr": [], "us": [], "keywords": [], "flights": [flight]}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data):
            cmd_flights(["/flights"])
        msg = mock_send.call_args[0][0]
        assert "인천 → 나리타" in msg
        assert "380,000원" in msg

    def test_no_history_shows_unconfirmed(self):
        flight = {
            "origin": "ICN", "origin_name": "인천", "destination": "NRT", "destination_name": "나리타",
            "depart": "260901", "return": None, "history": [],
        }
        data = {"kr": [], "us": [], "keywords": [], "flights": [flight]}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data):
            cmd_flights(["/flights"])
        assert "미확인" in mock_send.call_args[0][0]


class TestCmdFlight:
    def _flight(self, history=None):
        return {
            "origin": "ICN", "origin_name": "인천", "destination": "NRT", "destination_name": "나리타",
            "depart": "260901", "return": "260908", "history": history or [],
        }

    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_flight(["/flight"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_non_numeric_arg_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send:
            cmd_flight(["/flight", "abc"])
        assert "사용법" in mock_send.call_args[0][0]

    def test_out_of_range_index_sends_error(self):
        data = _default_flight_data()
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data):
            cmd_flight(["/flight", "1"])
        assert any("등록되지 않은 번호" in m for m in _messages(mock_send))

    def test_success_sends_price_and_saves_history(self):
        data = {"kr": [], "us": [], "keywords": [], "flights": [self._flight()]}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.get_flight_price", return_value={"price": 185400, "offers": []}), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_flight(["/flight", "1"])
        assert any("조회 중" in m for m in _messages(mock_send))
        assert any("185,400원" in m for m in _messages(mock_send))
        saved_flight = mock_save.call_args[0][1]["flights"][0]
        assert saved_flight["history"][-1]["price"] == 185400

    def test_price_lookup_failure_sends_error_and_does_not_save(self):
        data = {"kr": [], "us": [], "keywords": [], "flights": [self._flight()]}
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands.load_user_stocks", return_value=data), \
             patch("nicknews.commands.get_flight_price", return_value=None), \
             patch("nicknews.commands.save_user_stocks") as mock_save:
            cmd_flight(["/flight", "1"])
        assert any("조회 실패" in m for m in _messages(mock_send))
        mock_save.assert_not_called()


class TestCmdAllow:
    def test_non_owner_is_rejected(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands._is_owner", return_value=False):
            cmd_allow(["/allow", "999"], "456")
        assert "관리자" in mock_send.call_args[0][0]

    def test_no_args_sends_usage(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands._is_owner", return_value=True):
            cmd_allow(["/allow"], "111")
        assert "사용법" in mock_send.call_args[0][0]

    def test_owner_can_add_user(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands._is_owner", return_value=True), \
             patch("nicknews.commands.add_allowed_id") as mock_add:
            cmd_allow(["/allow", "999"], "111")
        mock_add.assert_called_once_with("999")
        assert "✅" in mock_send.call_args[0][0]


class TestCmdDisallow:
    def test_non_owner_is_rejected(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands._is_owner", return_value=False):
            cmd_disallow(["/disallow", "999"], "456")
        assert "관리자" in mock_send.call_args[0][0]

    def test_cannot_remove_owner(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands._is_owner", side_effect=lambda x: x == "111"):
            cmd_disallow(["/disallow", "111"], "111")
        assert "관리자 자신" in mock_send.call_args[0][0]

    def test_owner_can_remove_user(self):
        with patch("nicknews.commands.send_message") as mock_send, \
             patch("nicknews.commands._is_owner", side_effect=lambda x: x == "111"), \
             patch("nicknews.commands.remove_allowed_id") as mock_remove:
            cmd_disallow(["/disallow", "999"], "111")
        mock_remove.assert_called_once_with("999")
        assert "✅" in mock_send.call_args[0][0]
