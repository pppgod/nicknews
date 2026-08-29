from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from nicknews.flights import (
    _arrow,
    _change_str,
    _closest_entry,
    _extract_fare_offers,
    _group_domestic_flights_by_airline,
    _is_domestic_only_error,
    _to_domestic_code,
    date_label,
    format_flight_price_message,
    format_yymmdd,
    get_flight_price,
    parse_yymmdd,
    record_price,
    resolve_route,
    route_label,
    search_airport,
    search_domestic_flight_price,
    search_flight_price,
)


def _autocomplete_response(items):
    m = MagicMock()
    m.json.return_value = items
    return m


def _sse_lines(events):
    lines = []
    for e in events:
        lines.append(f"data: {e}")
        lines.append("")
    return lines


def _naver_response(status_code, price=None, completed=True, airline_code=None, airline_name=None):
    m = MagicMock()
    m.status_code = status_code
    if price is not None:
        import json
        body = {
            "status": {
                "isCompleted": completed,
                "priceRange": {"min": price, "max": price * 2},
                "airlinesCodeMap": {airline_code: airline_name} if airline_code else {},
            },
            "itineraries": [],
            "fareMappings": [],
        }
        if airline_code:
            body["itineraries"] = [{
                "itineraryId": "leg1",
                "segments": [{"marketingCarrier": {"airlineCode": airline_code}}],
            }]
            body["fareMappings"] = [{
                "itineraryIds": "leg1",
                "fares": [{"adult": {"totalFare": price}}],
            }]
        event = json.dumps(body)
        m.iter_lines.return_value = _sse_lines([event])
    else:
        m.iter_lines.return_value = []
    return m


def _domestic_error_response():
    m = MagicMock()
    m.status_code = 400
    m.json.return_value = {"message": {"message": "Invalid request: All routes are domestic airports"}}
    return m


def _domestic_sse_response(status_code, dep_price=None, arr_price=None, flights=None, completed=True):
    m = MagicMock()
    m.status_code = status_code
    if dep_price is not None or arr_price is not None:
        import json
        status = {"isComplete": completed, "airlinesCodeMap": {}}
        if dep_price is not None:
            status["departure"] = {"price": {"min": dep_price}}
        if arr_price is not None:
            status["arrival"] = {"price": {"min": arr_price}}
        body = {"status": status, "flights": flights or []}
        m.iter_lines.return_value = _sse_lines([json.dumps(body)])
    else:
        m.iter_lines.return_value = []
    return m


def _domestic_flight(code, price, dep_time="0900", arr_time="1010", travel_date="20270802"):
    return {
        "segment": {
            "airlineCode": code,
            "departure": {"time": dep_time, "date": travel_date},
            "arrival": {"time": arr_time, "date": travel_date},
        },
        "minFare": price,
    }


AIRPORT_ITEM = {"code": "ICN", "name": "인천", "type": "airport"}


# --- parse_yymmdd / format_yymmdd ---

class TestParseYymmdd:
    def test_parses_valid_date(self):
        assert parse_yymmdd("260901") == date(2026, 9, 1)

    def test_rejects_wrong_length(self):
        with pytest.raises(ValueError):
            parse_yymmdd("2609")

    def test_rejects_non_digit(self):
        with pytest.raises(ValueError):
            parse_yymmdd("26090a")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_yymmdd("")

    def test_rejects_invalid_calendar_date(self):
        with pytest.raises(ValueError):
            parse_yymmdd("261301")  # 13월은 없음


class TestFormatYymmdd:
    def test_roundtrip(self):
        d = date(2026, 9, 1)
        assert format_yymmdd(d) == "260901"
        assert parse_yymmdd(format_yymmdd(d)) == d


# --- search_airport ---

class TestSearchAirport:
    def test_returns_code_and_name(self):
        with patch("nicknews.flights.requests.get", return_value=_autocomplete_response([AIRPORT_ITEM])):
            code, name = search_airport("Incheon")
        assert code == "ICN"
        assert name == "인천"

    def test_korean_dictionary_hit_skips_travelpayouts(self):
        with patch("nicknews.flights.requests.get") as mock_get:
            code, name = search_airport("인천")
        assert code == "ICN"
        assert name == "인천"
        mock_get.assert_not_called()

    def test_korean_dictionary_covers_common_destinations(self):
        assert search_airport("하와이") == ("HNL", "호놀룰루")
        assert search_airport("도쿄") == ("NRT", "도쿄")
        assert search_airport("방콕") == ("BKK", "방콕")

    def test_korean_dictionary_strips_whitespace(self):
        with patch("nicknews.flights.requests.get") as mock_get:
            code, _ = search_airport("  인천  ")
        assert code == "ICN"
        mock_get.assert_not_called()

    def test_no_results_returns_none(self):
        with patch("nicknews.flights.requests.get", return_value=_autocomplete_response([])):
            assert search_airport("존재하지않는공항") == (None, None)

    def test_missing_code_returns_none(self):
        item = {"name": "?"}
        with patch("nicknews.flights.requests.get", return_value=_autocomplete_response([item])):
            assert search_airport("이상한곳") == (None, None)

    def test_falls_back_to_query_when_no_name(self):
        item = {"code": "BER"}
        with patch("nicknews.flights.requests.get", return_value=_autocomplete_response([item])):
            code, name = search_airport("베를린")
        assert code == "BER"
        assert name == "베를린"

    def test_request_error_returns_none(self):
        with patch("nicknews.flights.requests.get", side_effect=Exception("timeout")):
            assert search_airport("베를린") == (None, None)


class TestResolveRoute:
    """resolve_route는 search_airport를 그대로 위임하므로, 한글 사전에 없는 쿼리로
    Travelpayouts 폴백 경로만 검증한다 (사전 히트 여부는 TestSearchAirport에서 검증)."""

    def test_both_found_returns_tuple(self):
        origin_item = {"code": "ICN", "name": "Incheon"}
        dest_item = {"code": "NRT", "name": "Narita"}
        with patch("nicknews.flights.requests.get", side_effect=[
            _autocomplete_response([origin_item]), _autocomplete_response([dest_item]),
        ]):
            result = resolve_route("Incheon", "Narita")
        assert result == ("ICN", "Incheon", "NRT", "Narita")

    def test_origin_not_found_returns_none(self):
        with patch("nicknews.flights.requests.get", side_effect=[
            _autocomplete_response([]), _autocomplete_response([AIRPORT_ITEM]),
        ]):
            assert resolve_route("없는곳", "Incheon") is None

    def test_destination_not_found_returns_none(self):
        with patch("nicknews.flights.requests.get", side_effect=[
            _autocomplete_response([AIRPORT_ITEM]), _autocomplete_response([]),
        ]):
            assert resolve_route("Incheon", "없는곳") is None


# --- _extract_fare_offers ---

def _fare_data(price, entries):
    """entries: [(airline_code, airline_name, fare_price, outbound_itin, inbound_itin), ...]"""
    airline_map = {}
    itineraries = {}
    fare_mappings = []
    for i, (code, name, fare_price, outbound, inbound) in enumerate(entries):
        airline_map[code] = name
        out_id = f"out{i}"
        itineraries[out_id] = {"itineraryId": out_id, "segments": [{
            "marketingCarrier": {"airlineCode": code}, **(outbound or {}),
        }]}
        ids = out_id
        if inbound is not None:
            in_id = f"in{i}"
            itineraries[in_id] = {"itineraryId": in_id, "segments": [{
                "marketingCarrier": {"airlineCode": code}, **inbound,
            }]}
            ids = f"{out_id}-{in_id}"
        fare_mappings.append({"itineraryIds": ids, "fares": [{"adult": {"totalFare": fare_price}}]})
    return {
        "status": {"priceRange": {"min": price}, "airlinesCodeMap": airline_map},
        "itineraries": list(itineraries.values()),
        "fareMappings": fare_mappings,
    }


class TestExtractFareOffers:
    def test_returns_overall_min_price(self):
        data = _fare_data(1020700, [("KE", "대한항공", 1020700, {}, {})])
        assert _extract_fare_offers(data)["price"] == 1020700

    def test_single_offer_has_airline_name(self):
        data = _fare_data(1020700, [("KE", "대한항공", 1020700, {}, {})])
        offers = _extract_fare_offers(data)["offers"]
        assert offers[0]["airline"] == "대한항공"

    def test_unknown_airline_code_falls_back_to_code(self):
        data = _fare_data(100000, [("XX", None, 100000, {}, {})])
        data["status"]["airlinesCodeMap"] = {}  # 코드 매핑 없음
        offers = _extract_fare_offers(data)["offers"]
        assert offers[0]["airline"] == "XX"

    def test_priority_airline_listed_first_even_if_pricier(self):
        data = _fare_data(500000, [
            ("OZ", "아시아나항공", 500000, {}, {}),
            ("KE", "대한항공", 800000, {}, {}),
        ])
        offers = _extract_fare_offers(data)["offers"]
        assert offers[0]["airline"] == "대한항공"

    def test_non_priority_airlines_sorted_by_price(self):
        data = _fare_data(300000, [
            ("OZ", "아시아나항공", 500000, {}, {}),
            ("ZE", "이스타항공", 300000, {}, {}),
        ])
        offers = _extract_fare_offers(data)["offers"]
        assert [o["airline"] for o in offers] == ["이스타항공", "아시아나항공"]

    def test_limits_to_two_offers_per_airline(self):
        entries = [("KE", "대한항공", p, {}, {}) for p in (900000, 800000, 700000)]
        data = _fare_data(700000, entries)
        offers = _extract_fare_offers(data)["offers"]
        assert len(offers) == 2
        assert [o["price"] for o in offers] == [700000, 800000]  # 저가순 상위 2개

    def test_no_fare_mappings_returns_empty_offers(self):
        data = {"status": {"priceRange": {"min": 100000}, "airlinesCodeMap": {}}, "itineraries": [], "fareMappings": []}
        assert _extract_fare_offers(data) == {"price": 100000, "offers": []}

    def test_missing_price_returns_none(self):
        assert _extract_fare_offers({"status": {"priceRange": {}}}) is None

    def test_infinity_placeholder_returns_none(self):
        data = {"status": {"priceRange": {"min": 1.7976931348623157e+308}}}
        assert _extract_fare_offers(data) is None

    def test_time_label_included_for_outbound_and_return(self):
        data = _fare_data(200000, [(
            "KE", "대한항공", 200000,
            {"departure": {"time": "0900", "date": "20260901"}, "arrival": {"time": "1120", "date": "20260901"}},
            {"departure": {"time": "1800", "date": "20260908"}, "arrival": {"time": "2030", "date": "20260908"}},
        )])
        offer = _extract_fare_offers(data)["offers"][0]
        assert offer["depart_label"] == "09:00→11:20"
        assert offer["return_label"] == "18:00→20:30"

    def test_time_label_marks_next_day_arrival(self):
        data = _fare_data(200000, [(
            "KE", "대한항공", 200000,
            {"departure": {"time": "2300", "date": "20260901"}, "arrival": {"time": "0600", "date": "20260902"}},
            None,
        )])
        offer = _extract_fare_offers(data)["offers"][0]
        assert offer["depart_label"] == "23:00→06:00+1"
        assert offer["return_label"] is None


# --- search_flight_price (네이버 항공권 내부 API, SSE) ---

class TestSearchFlightPrice:
    def test_returns_price_from_completed_event(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=185400)):
            fare = search_flight_price("ICN", "NRT", date(2026, 9, 1), date(2026, 9, 8))
        assert fare["price"] == 185400

    def test_includes_airline_offer_when_resolvable(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(
            201, price=185400, airline_code="KE", airline_name="대한항공",
        )):
            fare = search_flight_price("ICN", "NRT", date(2026, 9, 1), date(2026, 9, 8))
        assert fare["offers"][0]["airline"] == "대한항공"

    def test_empty_offers_when_not_resolvable(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=185400)):
            fare = search_flight_price("ICN", "NRT", date(2026, 9, 1), date(2026, 9, 8))
        assert fare["offers"] == []

    def test_one_way_sets_trip_type_ow(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=70500)) as mock_post:
            search_flight_price("ICN", "NRT", date(2026, 9, 1))
        payload = mock_post.call_args.kwargs["json"]
        assert payload["tripType"] == "OW"
        assert len(payload["itineraries"]) == 1

    def test_round_trip_sets_trip_type_rt(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=185400)) as mock_post:
            search_flight_price("ICN", "NRT", date(2026, 9, 1), date(2026, 9, 8))
        payload = mock_post.call_args.kwargs["json"]
        assert payload["tripType"] == "RT"
        assert len(payload["itineraries"]) == 2
        assert payload["itineraries"][1]["departureLocationCode"] == "NRT"

    def test_non_2xx_status_returns_none(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(503)):
            assert search_flight_price("ICN", "NRT", date(2026, 9, 1)) is None

    def test_no_events_returns_none(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=None)):
            assert search_flight_price("ICN", "NRT", date(2026, 9, 1)) is None

    def test_placeholder_infinity_price_returns_none(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=1.7976931348623157e+308)):
            assert search_flight_price("ICN", "NRT", date(2026, 9, 1)) is None

    def test_request_error_returns_none(self):
        with patch("nicknews.flights.requests.post", side_effect=Exception("timeout")):
            assert search_flight_price("ICN", "NRT", date(2026, 9, 1)) is None

    def test_referer_matches_route(self):
        with patch("nicknews.flights.requests.post", return_value=_naver_response(201, price=1000)) as mock_post:
            search_flight_price("ICN", "NRT", date(2026, 9, 1), date(2026, 9, 8))
        referer = mock_post.call_args.kwargs["headers"]["referer"]
        assert "ICN-NRT-20260901" in referer
        assert "NRT-ICN-20260908" in referer

    def test_delegates_to_domestic_search_on_domestic_only_error(self):
        with patch("nicknews.flights.requests.post", return_value=_domestic_error_response()), \
             patch("nicknews.flights.search_domestic_flight_price", return_value={"price": 138500, "offers": []}) as mock_domestic:
            fare = search_flight_price("ICN", "CJU", date(2027, 8, 2))
        assert fare == {"price": 138500, "offers": []}
        mock_domestic.assert_called_once_with("ICN", "CJU", date(2027, 8, 2), None)

    def test_other_400_errors_do_not_delegate(self):
        m = MagicMock()
        m.status_code = 400
        m.json.return_value = {"message": {"message": "some other validation error"}}
        with patch("nicknews.flights.requests.post", return_value=m), \
             patch("nicknews.flights.search_domestic_flight_price") as mock_domestic:
            assert search_flight_price("ICN", "NRT", date(2026, 9, 1)) is None
        mock_domestic.assert_not_called()


# --- _is_domestic_only_error / _to_domestic_code ---

class TestIsDomesticOnlyError:
    def test_detects_domestic_only_message(self):
        assert _is_domestic_only_error(_domestic_error_response()) is True

    def test_other_message_returns_false(self):
        m = MagicMock()
        m.json.return_value = {"message": {"message": "Some other error"}}
        assert _is_domestic_only_error(m) is False

    def test_malformed_response_returns_false(self):
        m = MagicMock()
        m.json.side_effect = Exception("bad json")
        assert _is_domestic_only_error(m) is False


class TestToDomesticCode:
    def test_icn_maps_to_sel(self):
        assert _to_domestic_code("ICN") == "SEL"

    def test_other_codes_unchanged(self):
        assert _to_domestic_code("CJU") == "CJU"
        assert _to_domestic_code("GMP") == "GMP"


# --- _group_domestic_flights_by_airline ---

class TestGroupDomesticFlightsByAirline:
    def test_groups_by_airline_code(self):
        flights = [_domestic_flight("KE", 100000), _domestic_flight("OZ", 90000)]
        grouped = _group_domestic_flights_by_airline(flights)
        assert set(grouped) == {"KE", "OZ"}

    def test_sorts_and_limits_per_airline(self):
        flights = [_domestic_flight("KE", p) for p in (300, 100, 200)]
        grouped = _group_domestic_flights_by_airline(flights, max_per_airline=2)
        assert [f["price"] for f in grouped["KE"]] == [100, 200]

    def test_includes_time_label(self):
        flights = [_domestic_flight("KE", 100000, dep_time="0900", arr_time="1010")]
        grouped = _group_domestic_flights_by_airline(flights)
        assert grouped["KE"][0]["label"] == "09:00→10:10"

    def test_skips_entries_without_airline_or_price(self):
        assert _group_domestic_flights_by_airline([{"segment": {}, "minFare": None}]) == {}


# --- search_domestic_flight_price ---

class TestSearchDomesticFlightPrice:
    def test_normalizes_icn_to_sel(self):
        with patch("nicknews.flights.requests.post", return_value=_domestic_sse_response(201, dep_price=138500)) as mock_post:
            search_domestic_flight_price("ICN", "CJU", date(2027, 8, 2))
        payload = mock_post.call_args.kwargs["json"]
        assert payload["itineraries"][0]["departureAirport"] == "SEL"

    def test_one_way_returns_price_and_offers(self):
        flights = [_domestic_flight("KE", 138500)]
        with patch("nicknews.flights.requests.post", return_value=_domestic_sse_response(201, dep_price=138500, flights=flights)):
            fare = search_domestic_flight_price("GMP", "CJU", date(2027, 8, 2))
        assert fare["price"] == 138500
        assert fare["offers"][0]["airline"] == "KE"
        assert fare["offers"][0]["return_label"] is None

    def test_zero_departure_price_returns_none(self):
        with patch("nicknews.flights.requests.post", return_value=_domestic_sse_response(201, dep_price=0)):
            assert search_domestic_flight_price("GMP", "CJU", date(2027, 8, 2)) is None

    def test_round_trip_sums_leg_prices(self):
        dep_flights = [_domestic_flight("KE", 100000, "0900", "1010", "20270802")]
        arr_flights = [_domestic_flight("KE", 120000, "1800", "1910", "20270810")]
        responses = [
            _domestic_sse_response(201, dep_price=100000, flights=dep_flights),
            _domestic_sse_response(201, arr_price=120000, flights=arr_flights),
        ]
        with patch("nicknews.flights.requests.post", side_effect=responses):
            fare = search_domestic_flight_price("GMP", "CJU", date(2027, 8, 2), date(2027, 8, 10))
        assert fare["price"] == 220000
        assert fare["offers"][0] == {
            "airline": "KE", "price": 220000,
            "depart_label": "09:00→10:10", "return_label": "18:00→19:10",
        }

    def test_round_trip_missing_return_leg_returns_none(self):
        dep_flights = [_domestic_flight("KE", 100000)]
        responses = [
            _domestic_sse_response(201, dep_price=100000, flights=dep_flights),
            _domestic_sse_response(201, arr_price=0),
        ]
        with patch("nicknews.flights.requests.post", side_effect=responses):
            assert search_domestic_flight_price("GMP", "CJU", date(2027, 8, 2), date(2027, 8, 10)) is None

    def test_request_error_returns_none(self):
        with patch("nicknews.flights.requests.post", side_effect=Exception("timeout")):
            assert search_domestic_flight_price("GMP", "CJU", date(2027, 8, 2)) is None


class TestGetFlightPrice:
    def test_uses_stored_flight_fields(self):
        flight = {"origin": "ICN", "destination": "NRT", "depart": "260901", "return": "260908"}
        with patch("nicknews.flights.search_flight_price", return_value={"price": 185400, "offers": []}) as mock_search:
            fare = get_flight_price(flight)
        assert fare["price"] == 185400
        args = mock_search.call_args[0]
        assert args[0] == "ICN"
        assert args[1] == "NRT"
        assert args[2] == date(2026, 9, 1)
        assert args[3] == date(2026, 9, 8)

    def test_one_way_passes_no_return_date(self):
        flight = {"origin": "ICN", "destination": "NRT", "depart": "260901", "return": None}
        with patch("nicknews.flights.search_flight_price", return_value={"price": 70500, "offers": []}) as mock_search:
            get_flight_price(flight)
        assert mock_search.call_args[0][3] is None


class TestRecordPrice:
    @patch("nicknews.flights.date")
    def test_appends_todays_entry(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 29)
        flight = {"history": []}
        record_price(flight, 185400)
        assert flight["history"] == [{"date": "260829", "price": 185400}]

    @patch("nicknews.flights.date")
    def test_overwrites_existing_entry_for_today(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 29)
        flight = {"history": [{"date": "260829", "price": 400000}]}
        record_price(flight, 185400)
        assert flight["history"] == [{"date": "260829", "price": 185400}]

    @patch("nicknews.flights.date")
    def test_keeps_other_days_and_sorts(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 29)
        flight = {"history": [{"date": "260827", "price": 1}, {"date": "260825", "price": 2}]}
        record_price(flight, 3)
        assert [h["date"] for h in flight["history"]] == ["260825", "260827", "260829"]

    @patch("nicknews.flights.date")
    def test_trims_to_max_history(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 29)
        flight = {"history": [
            {"date": format_yymmdd(date(2026, 1, 1) + timedelta(days=i)), "price": i} for i in range(60)
        ]}
        record_price(flight, 999)
        assert len(flight["history"]) == 40


# --- formatting helpers ---

class TestArrow:
    def test_positive_returns_up(self):
        assert _arrow(1.0) == "🔺"

    def test_negative_returns_down(self):
        assert _arrow(-1.0) == "▼"


class TestChangeStr:
    def test_price_up(self):
        assert "+10.00%" in _change_str(110, 100)
        assert _change_str(110, 100).startswith("🔺")

    def test_price_down(self):
        assert "-10.00%" in _change_str(90, 100)
        assert _change_str(90, 100).startswith("▼")

    def test_zero_past_returns_none(self):
        assert _change_str(100, 0) is None

    def test_none_past_returns_none(self):
        assert _change_str(100, None) is None


class TestClosestEntry:
    def test_finds_exact_match(self):
        history = [{"date": "260828", "price": 400000}]
        entry = _closest_entry(history, date(2026, 8, 28), 0)
        assert entry["price"] == 400000

    def test_within_tolerance_matches(self):
        history = [{"date": "260827", "price": 400000}]
        entry = _closest_entry(history, date(2026, 8, 28), 2)
        assert entry["price"] == 400000

    def test_outside_tolerance_returns_none(self):
        history = [{"date": "260820", "price": 400000}]
        assert _closest_entry(history, date(2026, 8, 28), 2) is None

    def test_picks_closest_of_multiple(self):
        history = [{"date": "260826", "price": 1}, {"date": "260827", "price": 2}]
        entry = _closest_entry(history, date(2026, 8, 28), 3)
        assert entry["price"] == 2

    def test_ignores_malformed_dates(self):
        history = [{"date": "bad", "price": 1}, {"date": "260828", "price": 2}]
        entry = _closest_entry(history, date(2026, 8, 28), 0)
        assert entry["price"] == 2


class TestRouteAndDateLabel:
    def test_route_label_uses_names(self):
        flight = {"origin": "ICN", "origin_name": "인천", "destination": "NRT", "destination_name": "나리타"}
        assert route_label(flight) == "인천 → 나리타"

    def test_route_label_falls_back_to_code(self):
        flight = {"origin": "ICN", "destination": "NRT"}
        assert route_label(flight) == "ICN → NRT"

    def test_date_label_round_trip(self):
        flight = {"depart": "260901", "return": "260908"}
        assert date_label(flight) == "26.09.01 ~ 26.09.08 (왕복)"

    def test_date_label_one_way(self):
        flight = {"depart": "260901", "return": None}
        assert date_label(flight) == "26.09.01 (편도)"


class TestFormatFlightPriceMessage:
    def _flight(self, history=None):
        return {
            "origin": "ICN", "origin_name": "인천",
            "destination": "NRT", "destination_name": "나리타",
            "depart": "260901", "return": "260908",
            "history": history or [],
        }

    def _fare(self, price=185400, offers=None):
        return {"price": price, "offers": offers if offers is not None else []}

    def test_shows_route_and_price_without_offers(self):
        msg = format_flight_price_message(self._flight(), self._fare())
        assert "인천 → 나리타" in msg
        assert "185,400원" in msg
        assert "현재 최저가" in msg

    def test_shows_offers_grouped_by_airline(self):
        offers = [
            {"airline": "대한항공", "price": 185400, "depart_label": "09:00→11:20", "return_label": None},
            {"airline": "대한항공", "price": 195400, "depart_label": "10:00→12:20", "return_label": None},
            {"airline": "아시아나항공", "price": 300000, "depart_label": "13:00→15:20", "return_label": None},
        ]
        msg = format_flight_price_message(self._flight(), self._fare(offers=offers))
        assert msg.count("🔹") == 2  # 항공사 그룹 2개
        assert "대한항공" in msg
        assert "아시아나항공" in msg
        assert "09:00→11:20" in msg
        assert "300,000원" in msg
        assert "현재 최저가" not in msg  # offers가 있으면 단일 최저가 줄은 안 씀

    def test_offer_shows_return_time_when_round_trip(self):
        offers = [{"airline": "대한항공", "price": 185400, "depart_label": "09:00→11:20", "return_label": "18:00→20:30"}]
        msg = format_flight_price_message(self._flight(), self._fare(offers=offers))
        assert "가는편 09:00→11:20" in msg
        assert "오는편 18:00→20:30" in msg

    def test_no_history_has_no_comparisons(self):
        msg = format_flight_price_message(self._flight(), self._fare())
        assert "일 전" not in msg
        assert "개월 전" not in msg

    @patch("nicknews.flights.date")
    def test_shows_comparisons_within_tolerance(self, mock_date):
        mock_date.today.return_value = date(2026, 8, 29)
        history = [
            {"date": "260828", "price": 200000},
            {"date": "260822", "price": 210000},
            {"date": "260729", "price": 175000},
        ]
        msg = format_flight_price_message(self._flight(history), self._fare())
        assert "1일 전" in msg
        assert "1주일 전" in msg
        assert "1개월 전" in msg
