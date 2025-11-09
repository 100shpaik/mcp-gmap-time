from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Tuple

from zoneinfo import ZoneInfo


@dataclass
class LatLng:
    lat: float
    lng: float

    def as_str(self) -> str:
        return f"{self.lat},{self.lng}"


@dataclass
class Place:
    query: str
    formatted_address: str
    location: LatLng
    place_id: str | None = None


def minute_grid(
    date_str: str,
    start_hhmm: str,
    end_hhmm: str,
    interval_minutes: int,
    tz: str = "America/Los_Angeles",
) -> List[datetime]:
    """Return a list of timezone-aware datetimes at given interval on date.

    date_str: YYYY-MM-DD
    start_hhmm / end_hhmm: HH:MM (24h)
    """
    tzinfo = ZoneInfo(tz)
    y, m, d = map(int, date_str.split("-"))
    sh, sm = map(int, start_hhmm.split(":"))
    eh, em = map(int, end_hhmm.split(":"))
    start = datetime(y, m, d, sh, sm, tzinfo=tzinfo)
    end = datetime(y, m, d, eh, em, tzinfo=tzinfo)
    if end <= start:
        raise ValueError("end must be after start")
    out: List[datetime] = []
    cursor = start
    step = timedelta(minutes=interval_minutes)
    while cursor <= end:
        out.append(cursor)
        cursor += step
    return out


def sleep_backoff(i: int) -> None:
    """Simple progressive sleep to be kind to APIs when looping."""
    time.sleep(min(0.25 * i, 2.0))
