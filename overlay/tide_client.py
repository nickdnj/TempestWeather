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


@dataclass(frozen=True)
class TideStage:
    """Current tide stage information for fishing."""
    stage: str  # "Incoming", "Outgoing", "High Slack", "Low Slack"
    next_event: str  # "High tide" or "Low tide"
    next_time: datetime
    height: Optional[str]  # Tide height if available
    trend: str  # "Rising" or "Falling"
    icon_name: str  # Icon for current stage


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


def get_tide_stage(station_id: str) -> Optional[TideStage]:
    """
    Get current tide stage (incoming, outgoing, slack) for fishing report.
    
    Tide stages:
    - Incoming: Water rising toward high tide (BEST for fishing)
    - Outgoing: Water falling toward low tide (GOOD for fishing)
    - High Slack: ~30 min around high tide (FAIR for fishing)
    - Low Slack: ~30 min around low tide (FAIR for fishing)
    
    Args:
        station_id: NOAA tide station ID
    
    Returns:
        TideStage with current stage information, or None if unavailable
    """
    if not station_id:
        return None
    
    # Get current and next tide events
    next_tide = get_next_tide_event(station_id)
    if not next_tide:
        return None
    
    # Get all today's tides to find previous tide
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
        # Fallback to simple stage based on next tide only
        return _simple_tide_stage(next_tide)
    
    predictions = payload.get("predictions") or []
    now_local = _now_local()
    
    # Find previous and next tide events
    previous_tide = None
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
            previous_tide = (dt, tide_type, prediction.get("v", ""))
        else:
            break
    
    if not previous_tide:
        return _simple_tide_stage(next_tide)
    
    # Calculate time since previous tide and until next tide
    prev_time, prev_type, prev_height = previous_tide
    time_since_prev = (now_local - prev_time).total_seconds() / 60  # minutes
    time_until_next = (next_tide.event_time - now_local).total_seconds() / 60  # minutes
    
    # Determine stage
    # Slack period is roughly 30 minutes around high/low tide
    if time_since_prev < 30:
        # Just passed previous tide - slack period
        if prev_type == "H":
            stage = "High Slack"
            icon = "high_tide.png"
        else:
            stage = "Low Slack"
            icon = "low_tide.png"
    elif time_until_next < 30:
        # Approaching next tide - slack period
        if "High" in next_tide.event_type:
            stage = "High Slack"
            icon = "high_tide.png"
        else:
            stage = "Low Slack"
            icon = "low_tide.png"
    else:
        # Mid-tide - either incoming or outgoing
        if "High" in next_tide.event_type:
            stage = "Incoming"
            trend = "Rising"
            icon = "high_tide.png"
        else:
            stage = "Outgoing"
            trend = "Falling"
            icon = "low_tide.png"
    
    # Determine trend
    if "Slack" in stage:
        if "High" in stage:
            trend = "Falling"  # Just turned, starting to fall
        else:
            trend = "Rising"  # Just turned, starting to rise
    else:
        trend = "Rising" if stage == "Incoming" else "Falling"
    
    # Format height if available
    height_str = f"{float(prev_height):.1f} ft" if prev_height else None
    
    return TideStage(
        stage=stage,
        next_event=next_tide.event_type,
        next_time=next_tide.event_time,
        height=height_str,
        trend=trend,
        icon_name=icon
    )


def _simple_tide_stage(next_tide: TideEvent) -> TideStage:
    """
    Simplified tide stage when we only have next tide info.
    
    Args:
        next_tide: Next tide event
    
    Returns:
        TideStage with basic information
    """
    now_local = _now_local()
    time_until = (next_tide.event_time - now_local).total_seconds() / 60
    
    # If next tide is high, we're incoming; if low, we're outgoing
    if "High" in next_tide.event_type:
        if time_until < 30:
            stage = "High Slack"
        else:
            stage = "Incoming"
        trend = "Rising"
    else:
        if time_until < 30:
            stage = "Low Slack"
        else:
            stage = "Outgoing"
        trend = "Falling"
    
    return TideStage(
        stage=stage,
        next_event=next_tide.event_type,
        next_time=next_tide.event_time,
        height=None,
        trend=trend,
        icon_name=next_tide.icon_name
    )


def _now_local() -> datetime:
    return datetime.now(tz=DEFAULT_TIMEZONE)


__all__ = ["TideEvent", "TideStage", "get_next_tide_event", "get_tide_stage"]
