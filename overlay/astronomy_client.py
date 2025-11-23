"""
Astronomy data client for fishing report overlay.
Fetches moon phase, sunrise/sunset, and calculates solunar periods for fishing.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import requests
import pytz

# Cache configuration
CACHE_TTL_SECONDS = 3600  # 1 hour for moon data
SUNRISE_SUNSET_API = "https://api.sunrise-sunset.org/json"

_cache: dict[str, tuple[float, any]] = {}
_cache_lock = threading.Lock()


@dataclass(frozen=True)
class MoonData:
    """Moon phase and timing information."""
    phase_name: str  # "New Moon", "Waxing Crescent", etc.
    illumination: float  # 0-100%
    icon_name: str  # Icon filename for moon phase
    moonrise: Optional[datetime]
    moonset: Optional[datetime]
    moon_transit: Optional[datetime]  # Moon overhead (major solunar)


@dataclass(frozen=True)
class SolunarPeriods:
    """Solunar feeding period times."""
    next_major: Optional[datetime]  # Next major feeding period (2-3 hours)
    next_minor: Optional[datetime]  # Next minor feeding period (1-2 hours)
    major_label: str  # Display label for major period
    minor_label: str  # Display label for minor period


@dataclass(frozen=True)
class SunData:
    """Sunrise and sunset information."""
    sunrise: datetime
    sunset: datetime
    solar_noon: datetime


def get_moon_data(lat: float, lon: float, timezone: pytz.timezone = None) -> Optional[MoonData]:
    """
    Get current moon phase and timing data.
    
    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone for local times (default: US/Eastern)
    
    Returns:
        MoonData or None if fetch fails
    """
    if timezone is None:
        timezone = pytz.timezone("US/Eastern")
    
    now = time.time()
    cache_key = f"moon_{lat}_{lon}"
    
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
    
    moon_data = _fetch_moon_data(lat, lon, timezone)
    
    if moon_data:
        with _cache_lock:
            _cache[cache_key] = (now, moon_data)
    
    return moon_data


def get_solunar_periods(lat: float, lon: float, timezone: pytz.timezone = None) -> Optional[SolunarPeriods]:
    """
    Calculate solunar feeding periods for fishing.
    
    Major periods: Moon overhead (transit) and underfoot (2-3 hours)
    Minor periods: Moonrise and moonset (1-2 hours)
    
    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone for local times (default: US/Eastern)
    
    Returns:
        SolunarPeriods or None if calculation fails
    """
    if timezone is None:
        timezone = pytz.timezone("US/Eastern")
    
    moon_data = get_moon_data(lat, lon, timezone)
    if not moon_data:
        return None
    
    now = datetime.now(tz=timezone)
    
    # Minor periods: moonrise and moonset
    minor_times = []
    if moon_data.moonrise and moon_data.moonrise > now:
        minor_times.append(moon_data.moonrise)
    if moon_data.moonset and moon_data.moonset > now:
        minor_times.append(moon_data.moonset)
    
    next_minor = min(minor_times) if minor_times else None
    
    # Major period: moon transit (overhead)
    next_major = moon_data.moon_transit if moon_data.moon_transit and moon_data.moon_transit > now else None
    
    # Format labels
    major_label = next_major.strftime("%I:%M %p").lstrip("0") if next_major else "N/A"
    minor_label = next_minor.strftime("%I:%M %p").lstrip("0") if next_minor else "N/A"
    
    return SolunarPeriods(
        next_major=next_major,
        next_minor=next_minor,
        major_label=major_label,
        minor_label=minor_label
    )


def get_sunrise_sunset(lat: float, lon: float, timezone: pytz.timezone = None) -> Optional[SunData]:
    """
    Get sunrise and sunset times for location.
    
    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone for local times (default: US/Eastern)
    
    Returns:
        SunData or None if fetch fails
    """
    if timezone is None:
        timezone = pytz.timezone("US/Eastern")
    
    now = time.time()
    cache_key = f"sun_{lat}_{lon}"
    
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
    
    sun_data = _fetch_sunrise_sunset(lat, lon, timezone)
    
    if sun_data:
        with _cache_lock:
            _cache[cache_key] = (now, sun_data)
    
    return sun_data


def _fetch_moon_data(lat: float, lon: float, timezone: pytz.timezone) -> Optional[MoonData]:
    """Fetch moon data from API and calculate phase."""
    try:
        # Get current date in local timezone
        now = datetime.now(tz=timezone)
        
        # Calculate moon phase using astronomical algorithm
        # This is a simplified version - for production, consider using skyfield or ephem
        phase_info = _calculate_moon_phase(now)
        
        # Try to get moonrise/moonset from sunrise-sunset.org
        # Note: This API doesn't provide moon data directly, so we'll calculate it
        moonrise, moonset, moon_transit = _calculate_moon_times(lat, lon, now)
        
        return MoonData(
            phase_name=phase_info["name"],
            illumination=phase_info["illumination"],
            icon_name=phase_info["icon"],
            moonrise=moonrise,
            moonset=moonset,
            moon_transit=moon_transit
        )
    
    except Exception as e:
        print(f"Error fetching moon data: {e}")
        return None


def _fetch_sunrise_sunset(lat: float, lon: float, timezone: pytz.timezone) -> Optional[SunData]:
    """Fetch sunrise/sunset data from API."""
    try:
        params = {
            "lat": lat,
            "lng": lon,
            "formatted": 0  # Get ISO 8601 format
        }
        
        response = requests.get(SUNRISE_SUNSET_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            return None
        
        results = data["results"]
        
        # Parse UTC times and convert to local timezone
        sunrise_utc = datetime.fromisoformat(results["sunrise"].replace("Z", "+00:00"))
        sunset_utc = datetime.fromisoformat(results["sunset"].replace("Z", "+00:00"))
        solar_noon_utc = datetime.fromisoformat(results["solar_noon"].replace("Z", "+00:00"))
        
        return SunData(
            sunrise=sunrise_utc.astimezone(timezone),
            sunset=sunset_utc.astimezone(timezone),
            solar_noon=solar_noon_utc.astimezone(timezone)
        )
    
    except Exception as e:
        print(f"Error fetching sunrise/sunset data: {e}")
        return None


def _calculate_moon_phase(date: datetime) -> dict:
    """
    Calculate moon phase using astronomical algorithm.
    Based on the algorithm from "Astronomical Algorithms" by Jean Meeus.
    """
    # Julian date
    year = date.year
    month = date.month
    day = date.day + date.hour / 24.0
    
    if month <= 2:
        year -= 1
        month += 12
    
    a = year // 100
    b = 2 - a + (a // 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
    
    # Days since known new moon (January 6, 2000)
    days_since_new = jd - 2451549.5
    new_moons = days_since_new / 29.53058867  # Synodic month length
    phase = (new_moons % 1) * 29.53058867
    
    # Calculate illumination percentage
    illumination = (1 - math.cos(2 * math.pi * phase / 29.53058867)) / 2 * 100
    
    # Determine phase name and icon
    if phase < 1.84566:
        name, icon = "New Moon", "moon_new.png"
    elif phase < 5.53699:
        name, icon = "Waxing Crescent", "moon_waxing_crescent.png"
    elif phase < 9.22831:
        name, icon = "First Quarter", "moon_first_quarter.png"
    elif phase < 12.91963:
        name, icon = "Waxing Gibbous", "moon_waxing_gibbous.png"
    elif phase < 16.61096:
        name, icon = "Full Moon", "moon_full.png"
    elif phase < 20.30228:
        name, icon = "Waning Gibbous", "moon_waning_gibbous.png"
    elif phase < 23.99361:
        name, icon = "Last Quarter", "moon_last_quarter.png"
    else:
        name, icon = "Waning Crescent", "moon_waning_crescent.png"
    
    return {
        "name": name,
        "illumination": round(illumination, 1),
        "icon": icon,
        "phase_days": phase
    }


def _calculate_moon_times(lat: float, lon: float, date: datetime) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """
    Calculate approximate moonrise, moonset, and moon transit times.
    This is a simplified calculation - for production, use skyfield or ephem for accuracy.
    """
    timezone = date.tzinfo
    
    # This is a simplified approach
    # For accurate moon times, we should use a proper astronomy library
    # For now, we'll estimate based on the sun's position shifted by ~50 minutes per day
    
    try:
        # Get sun data as reference
        sun_data = _fetch_sunrise_sunset(lat, lon, timezone)
        if not sun_data:
            return None, None, None
        
        # Moon rises ~50 minutes later each day than the previous day
        # This is an approximation - actual calculation is complex
        phase_info = _calculate_moon_phase(date)
        phase_days = phase_info["phase_days"]
        
        # Estimate moon transit (overhead) time
        # Moon transit shifts ~50 minutes per day relative to sun
        moon_delay = timedelta(minutes=50 * phase_days)
        moon_transit = sun_data.solar_noon + moon_delay
        
        # Estimate moonrise (roughly 6 hours before transit)
        moonrise = moon_transit - timedelta(hours=6)
        
        # Estimate moonset (roughly 6 hours after transit)
        moonset = moon_transit + timedelta(hours=6)
        
        # Adjust to current day if times are in the past
        now = datetime.now(tz=timezone)
        if moonrise < now:
            moonrise += timedelta(days=1)
        if moonset < now:
            moonset += timedelta(days=1)
        if moon_transit < now:
            moon_transit += timedelta(days=1)
        
        return moonrise, moonset, moon_transit
    
    except Exception:
        return None, None, None


__all__ = [
    "MoonData",
    "SolunarPeriods",
    "SunData",
    "get_moon_data",
    "get_solunar_periods",
    "get_sunrise_sunset",
]

