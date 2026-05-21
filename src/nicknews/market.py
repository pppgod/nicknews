from datetime import datetime
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

KST = ZoneInfo("Asia/Seoul")
EST = ZoneInfo("America/New_York")

_KR_CAL = xcals.get_calendar("XKRX")
_US_CAL = xcals.get_calendar("XNYS")


def is_kr_market_open(now=None):
    if now is None:
        now = datetime.now(KST)
    return bool(_KR_CAL.is_open_at_time(pd.Timestamp(now)))


def is_us_market_open(now=None):
    if now is None:
        now = datetime.now(EST)
    return bool(_US_CAL.is_open_at_time(pd.Timestamp(now)))
