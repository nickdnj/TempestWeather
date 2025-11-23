"""
Water temperature client for fishing report overlay.
Fetches real-time water temperature from NOAA CO-OPS stations.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import requests

# NOAA CO-OPS API endpoint
API_ENDPOINT = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
CACHE_TTL_SECONDS = 900  # 15 minutes

_cache: dict[str, tuple[float, Optional[float]]] = {}
_cache_lock = threading.Lock()


def get_water_temperature(station_id: str, units: str = "metric") -> Optional[float]:
    """
    Get current water temperature from NOAA station.
    
    Args:
        station_id: NOAA CO-OPS station ID (e.g., "8531680" for Sandy Hook)
        units: 'metric' (Celsius) or 'imperial' (Fahrenheit)
    
    Returns:
        Water temperature in specified units, or None if unavailable
    """
    if not station_id:
        return None
    
    now = time.time()
    cache_key = f"{station_id}_{units}"
    
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
    
    temperature = _fetch_water_temperature(station_id, units)
    
    with _cache_lock:
        _cache[cache_key] = (now, temperature)
    
    return temperature


def _fetch_water_temperature(station_id: str, units: str) -> Optional[float]:
    """
    Fetch water temperature from NOAA CO-OPS API.
    
    Args:
        station_id: NOAA station ID
        units: 'metric' or 'imperial'
    
    Returns:
        Temperature or None if fetch fails
    """
    # NOAA API returns Celsius by default
    # We'll convert to Fahrenheit if needed
    params = {
        "station": station_id,
        "product": "water_temperature",
        "date": "latest",
        "time_zone": "lst_ldt",  # Local standard/daylight time
        "format": "json",
        "units": "metric"  # Always fetch in metric, convert if needed
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for error response
        if "error" in data:
            print(f"NOAA water temp API error: {data['error'].get('message', 'Unknown error')}")
            return None
        
        # Extract temperature from response
        if "data" not in data or not data["data"]:
            print(f"No water temperature data available for station {station_id}")
            return None
        
        # Get the most recent reading
        latest_reading = data["data"][0]
        temp_celsius = float(latest_reading.get("v", 0))
        
        if temp_celsius == 0:
            # Zero might indicate missing data
            return None
        
        # Convert to Fahrenheit if needed
        if units == "imperial":
            return temp_celsius * 9/5 + 32
        
        return temp_celsius
    
    except requests.RequestException as e:
        print(f"Error fetching water temperature from NOAA: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error parsing water temperature response: {e}")
        return None


def get_water_temp_with_activity(station_id: str, units: str = "imperial") -> tuple[Optional[float], str]:
    """
    Get water temperature with fish activity indicator.
    
    Fish activity levels based on water temperature:
    - Cold (<45°F / <7°C): "Slow"
    - Cool (45-55°F / 7-13°C): "Fair"
    - Moderate (55-68°F / 13-20°C): "Active"
    - Warm (68-78°F / 20-26°C): "Very Active"
    - Hot (>78°F / >26°C): "Moderate"
    
    Args:
        station_id: NOAA station ID
        units: 'metric' or 'imperial'
    
    Returns:
        Tuple of (temperature, activity_level)
    """
    temp = get_water_temperature(station_id, units)
    
    if temp is None:
        return None, "Unknown"
    
    # Determine activity level based on temperature
    # These are general guidelines for temperate species (striped bass, flounder, etc.)
    if units == "imperial":
        # Fahrenheit thresholds
        if temp < 45:
            activity = "Slow"
        elif temp < 55:
            activity = "Fair"
        elif temp < 68:
            activity = "Active"
        elif temp < 78:
            activity = "Very Active"
        else:
            activity = "Moderate"
    else:
        # Celsius thresholds
        if temp < 7:
            activity = "Slow"
        elif temp < 13:
            activity = "Fair"
        elif temp < 20:
            activity = "Active"
        elif temp < 26:
            activity = "Very Active"
        else:
            activity = "Moderate"
    
    return temp, activity


__all__ = [
    "get_water_temperature",
    "get_water_temp_with_activity",
]

