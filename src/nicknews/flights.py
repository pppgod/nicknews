import html
import json
from datetime import date, datetime, timedelta

import requests

# 공항/도시명 -> IATA 코드: Travelpayouts(Aviasales) 공개 autocomplete API (안정적, 공식 문서 있음).
# 단, 한글 검색어를 지원하지 않아("인천" 검색 시 빈 결과) 자주 쓰는 한글 지명은 아래 사전을 먼저 찾고,
# 없으면 Travelpayouts로 폴백한다 (영어 지명·IATA 코드는 Travelpayouts에서 바로 지원됨).
AUTOCOMPLETE_URL = "https://autocomplete.travelpayouts.com/places2"

# (한글 지명 -> (IATA 코드, 표시명)) 자주 쓰는 국내/해외 여행지 위주로 구성한 사전.
KOREAN_AIRPORTS = {
    # 국내
    "인천": ("ICN", "인천"), "김포": ("GMP", "김포"),
    "부산": ("PUS", "부산"), "김해": ("PUS", "부산"),
    "제주": ("CJU", "제주"), "대구": ("TAE", "대구"),
    "청주": ("CJJ", "청주"), "광주": ("KWJ", "광주"),
    "여수": ("RSU", "여수"), "무안": ("MWX", "무안"), "양양": ("YNY", "양양"),
    # 일본
    "도쿄": ("NRT", "도쿄"), "나리타": ("NRT", "도쿄"), "하네다": ("HND", "도쿄"),
    "오사카": ("KIX", "오사카"), "후쿠오카": ("FUK", "후쿠오카"),
    "삿포로": ("CTS", "삿포로"), "오키나와": ("OKA", "오키나와"), "나고야": ("NGO", "나고야"),
    # 동남아
    "방콕": ("BKK", "방콕"), "다낭": ("DAD", "다낭"), "나트랑": ("CXR", "나트랑"),
    "호치민": ("SGN", "호치민"), "하노이": ("HAN", "하노이"), "푸꾸옥": ("PQC", "푸꾸옥"),
    "세부": ("CEB", "세부"), "마닐라": ("MNL", "마닐라"), "보라카이": ("MPH", "보라카이"),
    "싱가포르": ("SIN", "싱가포르"), "쿠알라룸푸르": ("KUL", "쿠알라룸푸르"),
    "코타키나발루": ("BKI", "코타키나발루"), "발리": ("DPS", "발리"), "덴파사르": ("DPS", "발리"),
    "홍콩": ("HKG", "홍콩"), "마카오": ("MFM", "마카오"), "타이베이": ("TPE", "타이베이"),
    "괌": ("GUM", "괌"), "사이판": ("SPN", "사이판"),
    # 중국
    "상하이": ("PVG", "상하이"), "베이징": ("PEK", "베이징"), "칭다오": ("TAO", "칭다오"),
    # 미주/오세아니아
    "하와이": ("HNL", "호놀룰루"), "호놀룰루": ("HNL", "호놀룰루"),
    "뉴욕": ("JFK", "뉴욕"), "로스앤젤레스": ("LAX", "로스앤젤레스"), "엘에이": ("LAX", "로스앤젤레스"),
    "라스베가스": ("LAS", "라스베가스"), "시애틀": ("SEA", "시애틀"), "시드니": ("SYD", "시드니"),
    # 유럽
    "파리": ("CDG", "파리"), "런던": ("LHR", "런던"), "로마": ("FCO", "로마"),
    "프랑크푸르트": ("FRA", "프랑크푸르트"), "이스탄불": ("IST", "이스탄불"),
}

# 가격 조회: flight.naver.com이 자체적으로 쓰는 비공식/미문서화 내부 API.
# 공식 공개 API가 아니라서 예고 없이 형식이 바뀌거나 막힐 수 있음 — 개인용 저빈도 사용 전제.
NAVER_SEARCH_URL = "https://flight-api.naver.com/flight/international/searchFlights"
_NAVER_HEADERS = {
    "accept": "text/event-stream",
    "accept-language": "ko,en;q=0.9,en-US;q=0.8",
    "content-type": "application/json",
    "origin": "https://flight.naver.com",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Chromium";v="128"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
}
_INVALID_PRICE = 1e100  # 결과 없을 때 naver가 채워두는 float('inf')류 placeholder 걸러내는 기준

MAX_HISTORY = 40  # 저장할 최근 가격 이력 개수 (약 40일치)


def parse_yymmdd(value: str) -> date:
    """'260901' -> date(2026, 9, 1). 형식이 올바르지 않으면 ValueError."""
    if not (value and len(value) == 6 and value.isdigit()):
        raise ValueError(f"날짜 형식이 올바르지 않습니다 (yymmdd): {value}")
    return datetime.strptime(value, "%y%m%d").date()


def format_yymmdd(d: date) -> str:
    return d.strftime("%y%m%d")


def search_airport(query):
    """공항/도시명 또는 IATA 코드 -> (iata_code, display_name). 실패 시 (None, None)."""
    hit = KOREAN_AIRPORTS.get(query.strip())
    if hit:
        return hit
    try:
        res = requests.get(
            AUTOCOMPLETE_URL,
            params={"term": query, "locale": "ko", "types[]": ["airport", "city"]},
            timeout=10,
        )
        items = res.json()
        if not items:
            return None, None
        item = items[0]
        code = item.get("code")
        name = item.get("name") or item.get("city_name") or query
        if not code:
            return None, None
        return code, name
    except Exception:
        return None, None


def resolve_route(origin_query, dest_query):
    """출발지/목적지 조회 -> (origin_code, origin_name, dest_code, dest_name).
    둘 중 하나라도 실패하면 None."""
    o_code, o_name = search_airport(origin_query)
    d_code, d_name = search_airport(dest_query)
    if not o_code or not d_code:
        return None
    return o_code, o_name, d_code, d_name


def _naver_payload(origin, destination, depart_date: date, return_date: date = None):
    itineraries = [{
        "departureLocationCode": origin, "arrivalLocationCode": destination,
        "departureLocationType": "airport", "arrivalLocationType": "airport",
        "departureDate": depart_date.strftime("%Y%m%d"),
    }]
    if return_date:
        itineraries.append({
            "departureLocationCode": destination, "arrivalLocationCode": origin,
            "departureLocationType": "airport", "arrivalLocationType": "airport",
            "departureDate": return_date.strftime("%Y%m%d"),
        })
    return {
        "tripType": "RT" if return_date else "OW",
        "device": "pc", "seatClass": "Y",
        "adultCount": 1, "childCount": 0, "infantCount": 0,
        "isNonstop": False, "openReturnDays": 0, "initialRequest": True,
        "itineraries": itineraries,
        "flightFilter": {
            "filter": {
                "airlines": [], "departureAirports": [], "arrivalAirports": [],
                "departureTime": [], "fareTypes": [], "flightDurationSeconds": [],
                "hasCardBenefit": True, "isIndividual": False, "isLowCarbonEmission": False,
                "isSameAirlines": False, "isSameDepArrAirport": True, "isTravelClub": False,
                "minFare": {}, "viaCount": [], "selectedItineraries": [],
            },
            "limit": 200, "skip": 0, "sort": {"adultMinFare": 1},
        },
    }


def _naver_referer(origin, destination, depart_date: date, return_date: date = None):
    path = f"{origin}-{destination}-{depart_date.strftime('%Y%m%d')}"
    if return_date:
        path += f"/{destination}-{origin}-{return_date.strftime('%Y%m%d')}"
    return f"https://flight.naver.com/flights/international/{path}?adult=1&isDirect=false&fareType=Y"


PRIORITY_AIRLINE_CODE = "KE"  # 대한항공 — 항공사 정렬 시 최우선 표시
MAX_OFFERS_PER_AIRLINE = 2


def _format_time(hhmm) -> str:
    return f"{hhmm[:2]}:{hhmm[2:]}" if hhmm and len(hhmm) == 4 else ""


def _itinerary_time_label(itinerary):
    """편도 조합의 '출발→도착' 시각 라벨. 도착일이 출발일과 다르면 +1 표시. 정보 없으면 None."""
    segments = (itinerary or {}).get("segments")
    if not segments:
        return None
    dep, arr = segments[0].get("departure", {}), segments[-1].get("arrival", {})
    dep_t, arr_t = _format_time(dep.get("time")), _format_time(arr.get("time"))
    if not dep_t or not arr_t:
        return None
    label = f"{dep_t}→{arr_t}"
    if dep.get("date") and arr.get("date") and dep["date"] != arr["date"]:
        label += "+1"
    return label


def _extract_fare_offers(data):
    """SSE 최종 이벤트 -> {"price": 전체 최저가, "offers": [...]}. 가격 정보 없으면 None.
    offers는 항공사별 최저가 상위 MAX_OFFERS_PER_AIRLINE개씩, PRIORITY_AIRLINE_CODE(대한항공)를
    맨 앞에 두고 나머지는 항공사 최저가 오름차순으로 정렬한다."""
    status = data.get("status", {})
    overall_min = status.get("priceRange", {}).get("min")
    if overall_min is None or overall_min >= _INVALID_PRICE:
        return None

    airline_map = status.get("airlinesCodeMap", {})
    itineraries = {it.get("itineraryId"): it for it in data.get("itineraries", [])}

    by_airline = {}
    for mapping in data.get("fareMappings", []):
        ids = mapping.get("itineraryIds", "").split("-")
        outbound = itineraries.get(ids[0])
        inbound = itineraries.get(ids[1]) if len(ids) > 1 else None
        segments = (outbound or {}).get("segments")
        if not segments:
            continue
        code = segments[0].get("marketingCarrier", {}).get("airlineCode")
        if not code:
            continue
        for fare in mapping.get("fares", []):
            adult = fare.get("adult", {})
            price = adult.get("promotionTotalFare", adult.get("totalFare"))
            if price is None:
                continue
            by_airline.setdefault(code, []).append({
                "price": price,
                "depart_label": _itinerary_time_label(outbound),
                "return_label": _itinerary_time_label(inbound) if inbound else None,
            })

    for code, offers in by_airline.items():
        offers.sort(key=lambda o: o["price"])
        by_airline[code] = offers[:MAX_OFFERS_PER_AIRLINE]

    ordered_codes = sorted(
        by_airline,
        key=lambda c: (c != PRIORITY_AIRLINE_CODE, by_airline[c][0]["price"]),
    )

    offers = []
    for code in ordered_codes:
        name = airline_map.get(code, code)
        for o in by_airline[code]:
            offers.append({"airline": name, **o})

    return {"price": overall_min, "offers": offers}


def search_flight_price(origin, destination, depart_date: date, return_date: date = None):
    """편도/왕복 가격 조회. {"price": 전체 최저가, "offers": [항공사별 최저가 상위 목록]}
    또는 실패 시 None."""
    try:
        headers = dict(_NAVER_HEADERS)
        headers["referer"] = _naver_referer(origin, destination, depart_date, return_date)
        payload = _naver_payload(origin, destination, depart_date, return_date)

        res = requests.post(NAVER_SEARCH_URL, headers=headers, json=payload, timeout=(10, 25), stream=True)
        if res.status_code not in (200, 201):
            return None
        res.encoding = "utf-8"

        last = None
        for line in res.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                data = json.loads(line[len("data:"):].strip())
            except Exception:
                continue
            last = data
            if data.get("status", {}).get("isCompleted"):
                break

        if not last:
            return None
        return _extract_fare_offers(last)
    except Exception:
        return None


def get_flight_price(flight: dict):
    """저장된 flight dict(출발/도착 IATA 코드 등)로 현재 가격 조회.
    {"price": 전체 최저가, "offers": [...]} 또는 실패 시 None."""
    depart_date = parse_yymmdd(flight["depart"])
    return_date = parse_yymmdd(flight["return"]) if flight.get("return") else None
    return search_flight_price(flight["origin"], flight["destination"], depart_date, return_date)


def record_price(flight: dict, price):
    """flight["history"]에 오늘자 가격을 기록한다 (같은 날짜 항목이 있으면 덮어씀).
    최근 MAX_HISTORY개만 유지되도록 정리, flight를 in-place로 수정한다."""
    today_str = format_yymmdd(date.today())
    history = [h for h in flight.get("history", []) if h["date"] != today_str]
    history.append({"date": today_str, "price": price})
    history.sort(key=lambda h: h["date"])
    flight["history"] = history[-MAX_HISTORY:]


def _arrow(v):
    return "🔺" if v >= 0 else "▼"


def _change_str(current, past):
    if past and past > 0:
        pct = (current - past) / past * 100
        return f"{_arrow(pct)} {pct:+.2f}%"
    return None


def _closest_entry(history, target_date: date, tolerance_days: int):
    best, best_diff = None, None
    for h in history:
        try:
            d = parse_yymmdd(h["date"])
        except Exception:
            continue
        diff = abs((d - target_date).days)
        if diff <= tolerance_days and (best_diff is None or diff < best_diff):
            best, best_diff = h, diff
    return best


def route_label(flight: dict) -> str:
    o_name = html.escape(flight.get("origin_name") or flight["origin"])
    d_name = html.escape(flight.get("destination_name") or flight["destination"])
    return f"{o_name} → {d_name}"


def date_label(flight: dict) -> str:
    depart = parse_yymmdd(flight["depart"]).strftime("%y.%m.%d")
    if flight.get("return"):
        ret = parse_yymmdd(flight["return"]).strftime("%y.%m.%d")
        return f"{depart} ~ {ret} (왕복)"
    return f"{depart} (편도)"


def _format_price(price) -> str:
    return f"{price:,.0f}원"


def _offer_line(offer: dict) -> str:
    time_bits = []
    if offer.get("depart_label"):
        time_bits.append(f"가는편 {offer['depart_label']}")
    if offer.get("return_label"):
        time_bits.append(f"오는편 {offer['return_label']}")
    time_str = f"  {'  '.join(time_bits)}" if time_bits else ""
    return f"  {_format_price(offer['price'])}{time_str}"


def format_flight_price_message(flight: dict, fare: dict) -> str:
    """fare: search_flight_price/get_flight_price가 반환한 {"price", "offers"} dict."""
    today = date.today()
    history = flight.get("history", [])
    current_price = fare["price"]

    lines = [f"✈️ <b>{route_label(flight)}</b>  {date_label(flight)}"]

    offers = fare.get("offers") or []
    if offers:
        lines.append("")
        last_airline = None
        for offer in offers:
            if offer["airline"] != last_airline:
                last_airline = offer["airline"]
                lines.append(f"🔹 <b>{html.escape(last_airline)}</b>")
            lines.append(_offer_line(offer))
    else:
        lines.append(f"현재 최저가  <b>{_format_price(current_price)}</b>")

    comparisons = []
    for label, days_ago, tolerance in [("1일 전", 1, 0), ("1주일 전", 7, 2), ("1개월 전", 30, 3)]:
        entry = _closest_entry(history, today - timedelta(days=days_ago), tolerance)
        if not entry:
            continue
        change = _change_str(current_price, entry["price"])
        if change:
            comparisons.append(f"  {label}  {_format_price(entry['price'])}  ({change})")

    if comparisons:
        lines.append("")
        lines.append("\n".join(comparisons))

    return "\n".join(lines)
