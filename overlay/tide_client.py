"""Utilities for fetching tide predictions from NOAA with simple caching."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests
from dateutil import parser
import pytz

API_ENDPOINT = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
DEFAULT_TIMEZONE = pytz.timezone("US/Eastern")
CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class TideEvent:
    label: str
    event_type: str
    event_time: datetime
    icon_name: str


_cache: dict[str, tuple[float, TideEvent]] = {}
_cache_lock = threading.Lock()


def get_next_tide_event(station_id: str) -> Optional[TideEvent]:
    if not station_id:
        return None
    now = time.time()
    with _cache_lock:
        cached = _cache.get(station_id)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

    event = _fetch_next_tide_event(station_id)
    if event:
        with _cache_lock:
            _cache[station_id] = (now, event)
    return event


def _fetch_next_tide_event(station_id: str) -> Optional[TideEvent]:
    params = {
        "begin_date": _now_local().strftime("%Y%m%d"),
        "end_date": _now_local().strftime("%Y%m%d"),
        "station": station_id,
        "product": "predictions",
        "datum": "MLLW",
        "units": "english",
        "time_zone": "lst_ldt",
        "format": "json",
        "interval": "hilo",
    }
    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    predictions = payload.get("predictions") or []
    now_local = _now_local()
    for prediction in predictions:
        timestamp = prediction.get("t")
        tide_type = prediction.get("type")
        if not timestamp or tide_type not in {"H", "L"}:
            continue
        dt = parser.parse(timestamp)
        if dt.tzinfo is None:
            dt = DEFAULT_TIMEZONE.localize(dt)
        else:
            dt = dt.astimezone(DEFAULT_TIMEZONE)
        if dt <= now_local:
            continue
        label = "High tide" if tide_type == "H" else "Low tide"
        icon_name = "high_tide.png" if tide_type == "H" else "low_tide.png"
        return TideEvent(label=label, event_type=label, event_time=dt, icon_name=icon_name)
    return None


def _now_local() -> datetime:
    return datetime.now(tz=DEFAULT_TIMEZONE)


__all__ = ["TideEvent", "get_next_tide_event"]
