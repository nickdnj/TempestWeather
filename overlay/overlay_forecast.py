"""
Forecast overlay module for Tempest weather data.
Fetches forecast data from Tempest public API and renders overlay images
matching the style of the current conditions overlay.
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont

# Reuse the same rendering utilities from the existing overlay module
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.LANCZOS

# Import shared utilities from existing overlay code
from tempest_overlay_image import (
    FONT_PATH,
    ICONS_DIR,
    THEME_STYLES,
    _load_font,
    _text_size,
    _load_icon,
)
from tide_client import get_next_tide_event, TideEvent

# Tempest API configuration
TEMPEST_API_BASE = "https://swd.weatherflow.com/swd/rest/better_forecast"
TEMPEST_API_KEY = os.getenv("TEMPEST_API_KEY", "")
TEMPEST_STATION_ID = os.getenv("TEMPEST_STATION_ID", "")
TEMPEST_LOCATION_STATE = os.getenv("TEMPEST_LOCATION_STATE", "")  # e.g., "NJ"


def _format_location_with_state(location: str) -> str:
    """
    Format location name with state abbreviation if configured.
    
    Args:
        location: Base location name (e.g., "Monmouth Beach")
    
    Returns:
        Formatted location (e.g., "Monmouth Beach, NJ")
    """
    if not location:
        return location
    
    if TEMPEST_LOCATION_STATE:
        return f"{location}, {TEMPEST_LOCATION_STATE}"
    
    return location


# Icon mapping from Tempest API icon names to local icon files
FORECAST_ICON_MAP = {
    "clear-day": "clear.png",
    "clear-night": "night.png",
    "cloudy": "clouds.png",
    "foggy": "fog.png",
    "partly-cloudy-day": "clouds.png",
    "partly-cloudy-night": "night.png",
    "possibly-rainy-day": "drizzle.png",
    "possibly-rainy-night": "drizzle.png",
    "possibly-sleet-day": "snow.png",
    "possibly-sleet-night": "snow.png",
    "possibly-snow-day": "snow.png",
    "possibly-snow-night": "snow.png",
    "possibly-thunderstorm-day": "thunderstorm.png",
    "possibly-thunderstorm-night": "thunderstorm.png",
    "rainy": "rain.png",
    "sleet": "snow.png",
    "snow": "snow.png",
    "thunderstorm": "thunderstorm.png",
    "windy": "wind.png",
}


def fetch_forecast_data(units: str = "imperial") -> Optional[Dict]:
    """
    Fetch forecast data from Tempest public API.
    
    Args:
        units: 'imperial' or 'metric'
    
    Returns:
        Forecast data dictionary or None if request fails
    """
    if not TEMPEST_API_KEY or not TEMPEST_STATION_ID:
        return None
    
    # Map to Tempest API units format
    if units == "metric":
        units_temp = "c"
        units_wind = "kph"
        units_pressure = "mb"
        units_precip = "mm"
        units_distance = "km"
    else:
        units_temp = "f"
        units_wind = "mph"
        units_pressure = "inhg"
        units_precip = "in"
        units_distance = "mi"
    
    params = {
        "station_id": TEMPEST_STATION_ID,
        "token": TEMPEST_API_KEY,
        "units_temp": units_temp,
        "units_wind": units_wind,
        "units_pressure": units_pressure,
        "units_precip": units_precip,
        "units_distance": units_distance,
    }
    
    try:
        response = requests.get(TEMPEST_API_BASE, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        print(f"Error fetching forecast data: {e}")
        return None


def build_daily_forecast_payload(units: str = "imperial") -> Dict:
    """
    Build payload for daily forecast overlay.
    
    Args:
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with forecast data formatted for rendering
    """
    forecast_data = fetch_forecast_data(units)
    
    if not forecast_data or "forecast" not in forecast_data:
        return {
            "error": True,
            "title": "Daily Forecast",
            "message": "Unable to fetch forecast data",
            "cache_key": ("error", "daily", units),
        }
    
    # Extract location information for credit line
    location_name = _format_location_with_state(forecast_data.get("location_name", ""))
    station_id = TEMPEST_STATION_ID
    
    daily_forecasts = forecast_data.get("forecast", {}).get("daily", [])
    if not daily_forecasts:
        return {
            "error": True,
            "title": "Daily Forecast",
            "message": "No forecast data available",
            "cache_key": ("empty", "daily", units),
        }
    
    # Get today's forecast
    today = daily_forecasts[0]
    
    # Extract data
    high_temp = today.get("air_temp_high")
    low_temp = today.get("air_temp_low")
    conditions = today.get("conditions", "Unknown")
    precip_prob = today.get("precip_probability", 0)
    icon_name = today.get("icon", "unknown")
    
    # Format temperature
    unit_symbol = "°F" if units == "imperial" else "°C"
    temp_range = f"{int(high_temp)}{unit_symbol} / {int(low_temp)}{unit_symbol}" if high_temp and low_temp else "--"
    
    # Map icon name to local icon file
    local_icon = FORECAST_ICON_MAP.get(icon_name, "unknown.png")
    
    # Get day name
    day_start = today.get("day_start_local")
    if day_start:
        day_dt = datetime.fromtimestamp(day_start, tz=timezone.utc).astimezone()
        day_name = "Today"
    else:
        day_name = "Today"
    
    cache_key = (
        "daily",
        today.get("day_num"),
        today.get("month_num"),
        high_temp,
        low_temp,
        conditions,
        precip_prob,
        units,
    )
    
    return {
        "error": False,
        "title": "Today's Forecast",
        "day_name": day_name,
        "temp_range": temp_range,
        "conditions": conditions,
        "precip_prob": f"{precip_prob}%",
        "icon_name": local_icon,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def build_5hour_forecast_payload(units: str = "imperial") -> Dict:
    """
    Build payload for 5-hour forecast overlay.
    
    Args:
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with 5-hour forecast data formatted for rendering
    """
    forecast_data = fetch_forecast_data(units)
    
    if not forecast_data or "forecast" not in forecast_data:
        return {
            "error": True,
            "title": "5-Hour Forecast",
            "message": "Unable to fetch forecast data",
            "cache_key": ("error", "5hour", units),
        }
    
    # Extract location information for credit line
    location_name = _format_location_with_state(forecast_data.get("location_name", ""))
    station_id = TEMPEST_STATION_ID
    
    hourly_forecasts = forecast_data.get("forecast", {}).get("hourly", [])
    if len(hourly_forecasts) < 5:
        return {
            "error": True,
            "title": "5-Hour Forecast",
            "message": "Insufficient forecast data",
            "cache_key": ("insufficient", "5hour", units),
        }
    
    # Build list of 5 hours
    hours = []
    unit_symbol = "°F" if units == "imperial" else "°C"
    wind_unit = "mph" if units == "imperial" else "km/h"
    
    for i, hour_data in enumerate(hourly_forecasts[:5]):
        temp = hour_data.get("air_temperature")
        wind_speed = hour_data.get("wind_avg")
        wind_direction = hour_data.get("wind_direction")
        conditions = hour_data.get("conditions", "Unknown")
        icon_name = hour_data.get("icon", "unknown")
        time_timestamp = hour_data.get("time")
        
        # Format time from Unix timestamp (Docker container runs in station's timezone)
        if time_timestamp:
            try:
                # Simple conversion - container TZ matches station TZ
                hour_dt = datetime.fromtimestamp(time_timestamp)
                time_label = hour_dt.strftime("%I %p").lstrip("0")  # "10 AM", "3 PM"
            except Exception as e:
                time_label = f"Hour {i+1}"
        else:
            time_label = f"Hour {i+1}"
        
        # Format temperature
        temp_text = f"{int(temp)}{unit_symbol}" if temp is not None else "--"
        
        # Format wind with direction
        if wind_speed is not None and wind_direction is not None:
            wind_dir = _degrees_to_compass(wind_direction)
            wind_text = f"{int(wind_speed)} {wind_unit} {wind_dir}"
        else:
            wind_text = "--"
        
        # Map icon
        local_icon = FORECAST_ICON_MAP.get(icon_name, "unknown.png")
        
        hours.append({
            "time_label": time_label,
            "temp_text": temp_text,
            "wind_text": wind_text,
            "conditions": conditions,
            "icon_name": local_icon,
        })
    
    cache_key = (
        "5hour",
        tuple((h["time_label"], h["temp_text"], h["wind_text"]) for h in hours),
        units,
    )
    
    return {
        "error": False,
        "title": "5-Hour Forecast",
        "hours": hours,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def _degrees_to_compass(degrees: float) -> str:
    """
    Convert wind direction in degrees to compass direction.
    
    Args:
        degrees: Wind direction in degrees (0-360)
    
    Returns:
        Compass direction string (N, NE, E, etc.)
    """
    sectors = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW",
    ]
    idx = int((degrees + 11.25) / 22.5) % 16
    return sectors[idx]


def build_5day_forecast_payload(units: str = "imperial") -> Dict:
    """
    Build payload for 5-day forecast overlay.
    
    Args:
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with 5-day forecast data formatted for rendering
    """
    forecast_data = fetch_forecast_data(units)
    
    if not forecast_data or "forecast" not in forecast_data:
        return {
            "error": True,
            "title": "5-Day Forecast",
            "message": "Unable to fetch forecast data",
            "cache_key": ("error", "5day", units),
        }
    
    # Extract location information for credit line
    location_name = _format_location_with_state(forecast_data.get("location_name", ""))
    station_id = TEMPEST_STATION_ID
    
    daily_forecasts = forecast_data.get("forecast", {}).get("daily", [])
    if len(daily_forecasts) < 5:
        return {
            "error": True,
            "title": "5-Day Forecast",
            "message": "Insufficient forecast data",
            "cache_key": ("insufficient", "5day", units),
        }
    
    # Build list of 5 days
    days = []
    unit_symbol = "°F" if units == "imperial" else "°C"
    
    for i, day_data in enumerate(daily_forecasts[:5]):
        high_temp = day_data.get("air_temp_high")
        low_temp = day_data.get("air_temp_low")
        conditions = day_data.get("conditions", "Unknown")
        icon_name = day_data.get("icon", "unknown")
        day_start = day_data.get("day_start_local")
        
        # Get day name
        if day_start:
            day_dt = datetime.fromtimestamp(day_start, tz=timezone.utc).astimezone()
            if i == 0:
                day_name = "Today"
            elif i == 1:
                day_name = "Tomorrow"
            else:
                day_name = day_dt.strftime("%a")  # Mon, Tue, etc.
        else:
            day_name = f"Day {i+1}"
        
        # Format temperature
        temp_text = f"{int(high_temp)}/{int(low_temp)}{unit_symbol}" if high_temp and low_temp else "--"
        
        # Map icon
        local_icon = FORECAST_ICON_MAP.get(icon_name, "unknown.png")
        
        days.append({
            "day_name": day_name,
            "temp_text": temp_text,
            "conditions": conditions,
            "icon_name": local_icon,
        })
    
    cache_key = (
        "5day",
        tuple((d["day_name"], d["temp_text"], d["conditions"]) for d in days),
        units,
    )
    
    return {
        "error": False,
        "title": "5-Day Forecast",
        "days": days,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def render_daily_forecast_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render daily forecast overlay image matching the style of current conditions overlay.
    
    Args:
        payload: Daily forecast data from build_daily_forecast_payload
        width: Image width in pixels
        height: Image height in pixels
        theme: 'dark' or 'light'
    
    Returns:
        BytesIO buffer containing PNG image
    """
    theme = theme.lower()
    style = THEME_STYLES.get(theme, THEME_STYLES["dark"])
    
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    padding = max(int(height * 0.06), 24)
    primary_color = style["text"]
    
    if payload.get("error"):
        # Render error message
        title_font_size = max(int(height * 0.25), 48)
        title_font = _load_font(title_font_size)
        message_font_size = max(int(height * 0.15), 32)
        message_font = _load_font(message_font_size)
        
        title = payload.get("title", "Forecast Error")
        message = payload.get("message", "Unable to load forecast")
        
        # Center title
        title_width, title_height = _text_size(title_font, title)
        title_x = (width - title_width) // 2
        title_y = padding
        draw.text((title_x, title_y), title, font=title_font, fill=primary_color)
        
        # Center message
        message_width, message_height = _text_size(message_font, message)
        message_x = (width - message_width) // 2
        message_y = title_y + title_height + padding
        draw.text((message_x, message_y), message, font=message_font, fill=primary_color)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    
    # Render successful daily forecast
    inner_left = padding * 2
    current_y = padding
    
    # Title
    title_font_size = max(int(height * 0.18), 48)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "Today's Forecast")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.05), 20)
    
    # Calculate space needed at bottom for credit line with breathing room
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)  # Breathing room above credit
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding
    
    # Weather icon and info row
    remaining_height = height - current_y - bottom_reserved
    primary_font_size = max(int(remaining_height * 0.4), 36)
    main_font = _load_font(primary_font_size)
    icon_size = max(int(remaining_height * 0.7), 64)
    spacing = max(int(primary_font_size * 0.5), 30)
    small_spacing = max(int(primary_font_size * 0.3), 20)
    
    # Load and place icon
    icon_name = payload.get("icon_name", "unknown.png")
    condition_icon = _load_icon(icon_name, icon_size)
    icon_y = current_y + max((remaining_height - icon_size) // 2, 0)
    image.paste(condition_icon, (inner_left, icon_y), condition_icon)
    
    cursor_x = inner_left + icon_size + spacing
    
    # Temperature range
    temp_range = payload.get("temp_range", "--")
    draw.text((cursor_x, current_y), temp_range, font=main_font, fill=primary_color)
    temp_width, _ = _text_size(main_font, temp_range)
    cursor_x += temp_width + spacing
    
    # Conditions
    conditions = payload.get("conditions", "Unknown")
    draw.text((cursor_x, current_y), conditions, font=main_font, fill=primary_color)
    conditions_width, _ = _text_size(main_font, conditions)
    cursor_x += conditions_width + spacing
    
    # Precipitation probability
    precip_prob = payload.get("precip_prob", "--")
    precip_text = f"Rain: {precip_prob}"
    draw.text((cursor_x, current_y), precip_text, font=main_font, fill=primary_color)
    
    # Add credit line at the bottom with location, station ID, and timestamp
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    
    # Get current time in local timezone
    current_time = datetime.now().strftime("%I:%M %p").lstrip("0")  # "10:23 AM"
    
    # Build credit text with location, station info, and timestamp
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network | {current_time}"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network | {current_time}"
    else:
        credit_text = f"Data from Tempest Weather Network | {current_time}"
    
    # Make credit line bright, bold, and highly visible
    credit_font_size = max(int(height * 0.08), 16)  # Larger font
    credit_font = _load_font(credit_font_size)
    
    # Use pure white with full opacity for maximum visibility
    credit_color = (255, 255, 255, 255)
    
    # Center the credit text at the bottom with small margin
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - max(int(height * 0.03), 10)
    
    # Draw text multiple times with slight offsets to simulate bold effect
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def render_5day_forecast_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render 5-day forecast overlay image matching the style of current conditions overlay.
    
    Args:
        payload: 5-day forecast data from build_5day_forecast_payload
        width: Image width in pixels
        height: Image height in pixels
        theme: 'dark' or 'light'
    
    Returns:
        BytesIO buffer containing PNG image
    """
    theme = theme.lower()
    style = THEME_STYLES.get(theme, THEME_STYLES["dark"])
    
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    padding = max(int(height * 0.06), 24)
    primary_color = style["text"]
    
    if payload.get("error"):
        # Render error message
        title_font_size = max(int(height * 0.25), 48)
        title_font = _load_font(title_font_size)
        message_font_size = max(int(height * 0.15), 32)
        message_font = _load_font(message_font_size)
        
        title = payload.get("title", "Forecast Error")
        message = payload.get("message", "Unable to load forecast")
        
        # Center title
        title_width, title_height = _text_size(title_font, title)
        title_x = (width - title_width) // 2
        title_y = padding
        draw.text((title_x, title_y), title, font=title_font, fill=primary_color)
        
        # Center message
        message_width, message_height = _text_size(message_font, message)
        message_x = (width - message_width) // 2
        message_y = title_y + title_height + padding
        draw.text((message_x, message_y), message, font=message_font, fill=primary_color)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    
    # Render successful 5-day forecast
    inner_left = padding * 2
    current_y = padding
    
    # Title
    title_font_size = max(int(height * 0.15), 36)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "5-Day Forecast")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.04), 16)
    
    # Calculate layout for 5 days
    days = payload.get("days", [])
    if not days:
        days = []
    
    # Calculate space needed at bottom for credit line with breathing room
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)  # Breathing room above credit
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding
    
    remaining_height = height - current_y - bottom_reserved
    available_width = width - inner_left - padding
    
    # Each day gets equal width
    num_days = len(days)
    if num_days == 0:
        num_days = 5
    
    day_width = available_width // num_days
    day_spacing = max(int(day_width * 0.05), 10)
    content_width = day_width - day_spacing
    
    # Font sizes
    day_name_font_size = max(int(remaining_height * 0.15), 20)
    day_name_font = _load_font(day_name_font_size)
    temp_font_size = max(int(remaining_height * 0.13), 18)
    temp_font = _load_font(temp_font_size)
    icon_size = max(int(remaining_height * 0.4), 48)
    
    # Render each day
    for i, day in enumerate(days):
        day_x = inner_left + (i * day_width)
        day_center_x = day_x + content_width // 2
        
        # Day name (centered)
        day_name = day.get("day_name", f"Day {i+1}")
        day_name_width, _ = _text_size(day_name_font, day_name)
        name_x = day_center_x - day_name_width // 2
        draw.text((name_x, current_y), day_name, font=day_name_font, fill=primary_color)
        
        icon_y = current_y + day_name_font_size + max(int(height * 0.03), 12)
        
        # Weather icon (centered)
        icon_name = day.get("icon_name", "unknown.png")
        icon = _load_icon(icon_name, icon_size)
        icon_x = day_center_x - icon_size // 2
        image.paste(icon, (icon_x, icon_y), icon)
        
        # Temperature (centered)
        temp_y = icon_y + icon_size + max(int(height * 0.02), 8)
        temp_text = day.get("temp_text", "--")
        temp_width, _ = _text_size(temp_font, temp_text)
        temp_x = day_center_x - temp_width // 2
        draw.text((temp_x, temp_y), temp_text, font=temp_font, fill=primary_color)
    
    # Add credit line at the bottom with location, station ID, and timestamp
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    
    # Get current time in local timezone
    current_time = datetime.now().strftime("%I:%M %p").lstrip("0")  # "10:23 AM"
    
    # Build credit text with location, station info, and timestamp
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network | {current_time}"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network | {current_time}"
    else:
        credit_text = f"Data from Tempest Weather Network | {current_time}"
    
    # Make credit line bright, bold, and highly visible
    credit_font_size = max(int(height * 0.08), 16)  # Larger font
    credit_font = _load_font(credit_font_size)
    
    # Use pure white with full opacity for maximum visibility
    credit_color = (255, 255, 255, 255)
    
    # Center the credit text at the bottom with small margin
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - max(int(height * 0.03), 10)
    
    # Draw text multiple times with slight offsets to simulate bold effect
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def render_5hour_forecast_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render 5-hour forecast overlay image matching the style of 5-day forecast overlay.
    
    Args:
        payload: 5-hour forecast data from build_5hour_forecast_payload
        width: Image width in pixels
        height: Image height in pixels
        theme: 'dark' or 'light'
    
    Returns:
        BytesIO buffer containing PNG image
    """
    theme = theme.lower()
    style = THEME_STYLES.get(theme, THEME_STYLES["dark"])
    
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    padding = max(int(height * 0.06), 24)
    primary_color = style["text"]
    
    if payload.get("error"):
        # Render error message
        title_font_size = max(int(height * 0.25), 48)
        title_font = _load_font(title_font_size)
        message_font_size = max(int(height * 0.15), 32)
        message_font = _load_font(message_font_size)
        
        title = payload.get("title", "Forecast Error")
        message = payload.get("message", "Unable to load forecast")
        
        # Center title
        title_width, title_height = _text_size(title_font, title)
        title_x = (width - title_width) // 2
        title_y = padding
        draw.text((title_x, title_y), title, font=title_font, fill=primary_color)
        
        # Center message
        message_width, message_height = _text_size(message_font, message)
        message_x = (width - message_width) // 2
        message_y = title_y + title_height + padding
        draw.text((message_x, message_y), message, font=message_font, fill=primary_color)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    
    # Render successful 5-hour forecast
    inner_left = padding * 2
    current_y = padding
    
    # Title
    title_font_size = max(int(height * 0.15), 36)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "5-Hour Forecast")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.04), 16)
    
    # Calculate layout for 5 hours
    hours = payload.get("hours", [])
    if not hours:
        hours = []
    
    # Calculate space needed at bottom for credit line with breathing room
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)  # Breathing room above credit
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding
    
    remaining_height = height - current_y - bottom_reserved
    available_width = width - inner_left - padding
    
    # Each hour gets equal width
    num_hours = len(hours)
    if num_hours == 0:
        num_hours = 5
    
    hour_width = available_width // num_hours
    hour_spacing = max(int(hour_width * 0.05), 10)
    content_width = hour_width - hour_spacing
    
    # Font sizes (similar to 5-day but adjusted for more data per column)
    time_font_size = max(int(remaining_height * 0.12), 18)
    time_font = _load_font(time_font_size)
    temp_font_size = max(int(remaining_height * 0.11), 16)
    temp_font = _load_font(temp_font_size)
    wind_font_size = max(int(remaining_height * 0.09), 14)
    wind_font = _load_font(wind_font_size)
    icon_size = max(int(remaining_height * 0.35), 48)
    
    # Render each hour
    for i, hour in enumerate(hours):
        hour_x = inner_left + (i * hour_width)
        hour_center_x = hour_x + content_width // 2
        
        # Time label (centered)
        time_label = hour.get("time_label", f"Hour {i+1}")
        time_width, _ = _text_size(time_font, time_label)
        time_x = hour_center_x - time_width // 2
        draw.text((time_x, current_y), time_label, font=time_font, fill=primary_color)
        
        icon_y = current_y + time_font_size + max(int(height * 0.03), 12)
        
        # Weather icon (centered)
        icon_name = hour.get("icon_name", "unknown.png")
        icon = _load_icon(icon_name, icon_size)
        icon_x = hour_center_x - icon_size // 2
        image.paste(icon, (icon_x, icon_y), icon)
        
        # Temperature (centered)
        temp_y = icon_y + icon_size + max(int(height * 0.02), 8)
        temp_text = hour.get("temp_text", "--")
        temp_width, _ = _text_size(temp_font, temp_text)
        temp_x = hour_center_x - temp_width // 2
        draw.text((temp_x, temp_y), temp_text, font=temp_font, fill=primary_color)
        
        # Wind speed and direction (centered)
        wind_y = temp_y + temp_font_size + max(int(height * 0.015), 6)
        wind_text = hour.get("wind_text", "--")
        wind_width, _ = _text_size(wind_font, wind_text)
        wind_x = hour_center_x - wind_width // 2
        draw.text((wind_x, wind_y), wind_text, font=wind_font, fill=primary_color)
    
    # Add credit line at the bottom with location, station ID, and timestamp
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    
    # Get current time in local timezone
    current_time = datetime.now().strftime("%I:%M %p").lstrip("0")  # "10:23 AM"
    
    # Build credit text with location, station info, and timestamp
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network | {current_time}"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network | {current_time}"
    else:
        credit_text = f"Data from Tempest Weather Network | {current_time}"
    
    # Make credit line bright, bold, and highly visible
    credit_font_size = max(int(height * 0.08), 16)  # Larger font
    credit_font = _load_font(credit_font_size)
    
    # Use pure white with full opacity for maximum visibility
    credit_color = (255, 255, 255, 255)
    
    # Center the credit text at the bottom with small margin
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - max(int(height * 0.03), 10)
    
    # Draw text multiple times with slight offsets to simulate bold effect
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def build_current_conditions_payload(observation, units: str = "imperial") -> Dict:
    """
    Build payload for current conditions overlay using Tempest API.
    Fetches current conditions, icon, and location from API for accuracy.
    
    Args:
        observation: TempestObservation from local UDP listener (used as fallback)
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with current conditions data formatted for rendering
    """
    # Fetch data from Tempest API for accurate icon and location
    forecast_data = fetch_forecast_data(units)
    
    station_id = TEMPEST_STATION_ID
    unit_symbol = "°F" if units == "imperial" else "°C"
    wind_unit = "mph" if units == "imperial" else "km/h"
    
    if not forecast_data or "current_conditions" not in forecast_data:
        # Fallback to "waiting" state
        return {
            "error": False,
            "title": "Current Conditions",
            "temperature": "--",
            "wind": "--",
            "humidity": "--",
            "icon_name": "unknown.png",
            "location_name": _format_location_with_state(forecast_data.get("location_name", "")) if forecast_data else "",
            "station_id": station_id,
            "cache_key": ("waiting", units),
        }
    
    # Extract location from API
    location_name = _format_location_with_state(forecast_data.get("location_name", ""))
    
    # Get current conditions from API
    current = forecast_data.get("current_conditions", {})
    
    # Temperature
    temp = current.get("air_temperature")
    temperature = f"{int(temp)}{unit_symbol}" if temp is not None else "--"
    
    # Wind
    wind_speed = current.get("wind_avg")
    wind_direction = current.get("wind_direction")
    if wind_speed is not None:
        wind_text = f"{int(wind_speed)} {wind_unit}"
        if wind_direction is not None:
            wind_text += f" {_degrees_to_compass(wind_direction)}"
        wind = wind_text
    else:
        wind = "--"
    
    # Humidity
    humidity_val = current.get("relative_humidity")
    humidity = f"{int(humidity_val)}%" if humidity_val is not None else "--"
    
    # Icon from API (much more accurate than deriving from sensors!)
    icon_api_name = current.get("icon", "unknown")
    icon_name = FORECAST_ICON_MAP.get(icon_api_name, "unknown.png")
    
    cache_key = (
        current.get("time"),
        temp,
        wind_speed,
        humidity_val,
        units,
    )
    
    return {
        "error": False,
        "title": "Current Conditions",
        "temperature": temperature,
        "wind": wind,
        "humidity": humidity,
        "icon_name": icon_name,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def _degrees_to_compass(degrees: Optional[float]) -> str:
    """Convert degrees to compass direction."""
    if degrees is None:
        return ""
    sectors = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW",
    ]
    idx = int((degrees + 11.25) / 22.5) % 16
    return sectors[idx]


def render_current_conditions_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render current conditions overlay in the same style as forecast overlays.
    
    Args:
        payload: Current conditions data from build_current_conditions_payload
        width: Image width in pixels
        height: Image height in pixels
        theme: 'dark' or 'light'
    
    Returns:
        BytesIO buffer containing PNG image
    """
    theme = theme.lower()
    style = THEME_STYLES.get(theme, THEME_STYLES["dark"])
    
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    padding = max(int(height * 0.06), 24)
    primary_color = style["text"]
    
    # Title
    inner_left = padding * 2
    current_y = padding
    
    title_font_size = max(int(height * 0.18), 48)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "Current Conditions")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.05), 20)
    
    # Weather data row
    remaining_height = height - current_y - padding
    primary_font_size = max(int(remaining_height * 0.4), 36)
    main_font = _load_font(primary_font_size)
    icon_size = max(int(remaining_height * 0.6), 64)
    spacing = max(int(primary_font_size * 0.5), 30)
    small_spacing = max(int(primary_font_size * 0.3), 20)
    
    # Load and place weather icon
    icon_name = payload.get("icon_name", "unknown.png")
    condition_icon = _load_icon(icon_name, icon_size)
    icon_y = current_y + max((remaining_height - icon_size) // 3, 0)
    image.paste(condition_icon, (inner_left, icon_y), condition_icon)
    
    cursor_x = inner_left + icon_size + spacing
    
    # Temperature
    temperature = payload.get("temperature", "--")
    draw.text((cursor_x, current_y), temperature, font=main_font, fill=primary_color)
    temp_width, _ = _text_size(main_font, temperature)
    cursor_x += temp_width + spacing
    
    # Wind icon and text
    wind_icon = _load_icon("wind.png", int(icon_size * 0.5))
    wind_icon_y = current_y + max((primary_font_size - wind_icon.size[1]) // 2, 0)
    image.paste(wind_icon, (int(cursor_x), int(wind_icon_y)), wind_icon)
    cursor_x += wind_icon.size[0] + small_spacing
    
    wind = payload.get("wind", "--")
    draw.text((cursor_x, current_y), wind, font=main_font, fill=primary_color)
    wind_width, _ = _text_size(main_font, wind)
    cursor_x += wind_width + spacing
    
    # Humidity icon and text
    humidity_icon = _load_icon("humidity.png", int(icon_size * 0.5))
    humidity_icon_y = current_y + max((primary_font_size - humidity_icon.size[1]) // 2, 0)
    image.paste(humidity_icon, (int(cursor_x), int(humidity_icon_y)), humidity_icon)
    cursor_x += humidity_icon.size[0] + small_spacing
    
    humidity = payload.get("humidity", "--")
    draw.text((cursor_x, current_y), humidity, font=main_font, fill=primary_color)
    
    # Add credit line at the bottom with location, station ID, and timestamp
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    
    # Get current time in local timezone
    current_time = datetime.now().strftime("%I:%M %p").lstrip("0")
    
    # Build credit text with location, station info, and timestamp
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network | {current_time}"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network | {current_time}"
    else:
        credit_text = f"Data from Tempest Weather Network | {current_time}"
    
    # Make credit line bright, bold, and highly visible
    credit_font_size = max(int(height * 0.08), 16)
    credit_font = _load_font(credit_font_size)
    credit_color = (255, 255, 255, 255)
    
    # Center the credit text at the bottom with margin
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - max(int(height * 0.03), 10)
    
    # Draw text multiple times with slight offsets to simulate bold effect
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _fetch_station_name(station_id: str) -> str:
    """
    Fetch station name from NOAA API.
    Falls back to station ID if fetch fails.
    
    Args:
        station_id: NOAA station ID
    
    Returns:
        Station name or station ID as fallback
    """
    try:
        url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
        params = {"id": station_id}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract station name from the response
        stations = data.get("stations", [])
        if stations and len(stations) > 0:
            return stations[0].get("name", station_id)
    except Exception:
        pass
    
    # Fallback to station ID
    return f"Station {station_id}"


def build_tides_payload(station_ids: List[str]) -> Dict:
    """
    Build payload for multi-station tide overlay.
    
    Args:
        station_ids: List of NOAA tide station IDs (up to 4)
    
    Returns:
        Dictionary with tide data for each station
    """
    # Limit to 4 stations
    station_ids = station_ids[:4]
    
    if not station_ids:
        return {
            "error": True,
            "title": "Tide Forecast",
            "message": "No stations specified",
            "cache_key": ("error", "tides"),
        }
    
    stations_data = []
    
    for station_id in station_ids:
        station_id = station_id.strip()
        if not station_id:
            continue
        
        # Fetch station name
        station_name = _fetch_station_name(station_id)
        
        # Fetch next tide event
        tide_event = get_next_tide_event(station_id)
        
        if tide_event:
            station_data = {
                "station_id": station_id,
                "station_name": station_name,
                "tide_type": tide_event.label,  # "High tide" or "Low tide"
                "tide_time": tide_event.event_time.strftime("%I:%M %p").lstrip("0"),
                "icon_name": tide_event.icon_name,  # "high_tide.png" or "low_tide.png"
            }
        else:
            # No tide data available
            station_data = {
                "station_id": station_id,
                "station_name": station_name,
                "tide_type": "No data",
                "tide_time": "--",
                "icon_name": "unknown.png",
            }
        
        stations_data.append(station_data)
    
    if not stations_data:
        return {
            "error": True,
            "title": "Tide Forecast",
            "message": "No valid stations",
            "cache_key": ("error", "tides"),
        }
    
    cache_key = tuple(
        (s["station_id"], s["tide_type"], s["tide_time"]) 
        for s in stations_data
    )
    
    return {
        "error": False,
        "title": "Tide Forecast",
        "stations": stations_data,
        "cache_key": cache_key,
    }


def render_tides_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render multi-station tide overlay with 4 columns.
    
    Args:
        payload: Tide data from build_tides_payload
        width: Image width in pixels
        height: Image height in pixels
        theme: 'dark' or 'light'
    
    Returns:
        BytesIO buffer containing PNG image
    """
    theme = theme.lower()
    style = THEME_STYLES.get(theme, THEME_STYLES["dark"])
    
    # Create transparent image
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    padding = max(int(height * 0.06), 24)
    primary_color = style["text"]
    
    # Handle error state
    if payload.get("error"):
        title_font_size = max(int(height * 0.18), 48)
        title_font = _load_font(title_font_size)
        message_font_size = max(int(height * 0.12), 32)
        message_font = _load_font(message_font_size)
        
        title = payload.get("title", "Tide Forecast")
        message = payload.get("message", "Unable to fetch tide data")
        
        title_width, title_height = _text_size(title_font, title)
        message_width, message_height = _text_size(message_font, message)
        
        title_x = (width - title_width) // 2
        title_y = (height - title_height - message_height - padding) // 2
        message_x = (width - message_width) // 2
        message_y = title_y + title_height + padding
        
        draw.text((title_x, title_y), title, font=title_font, fill=primary_color)
        draw.text((message_x, message_y), message, font=message_font, fill=primary_color)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    
    # Render successful tide forecast
    inner_left = padding * 2
    current_y = padding
    
    # Title
    title_font_size = max(int(height * 0.18), 48)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "Tide Forecast")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.05), 20)
    
    # Calculate space needed at bottom for credit line with breathing room
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)  # Breathing room above credit
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding
    
    remaining_height = height - current_y - bottom_reserved
    available_width = width - inner_left - padding
    
    # Each station gets equal width
    stations = payload.get("stations", [])
    num_stations = len(stations)
    if num_stations == 0:
        num_stations = 4
    
    station_width = available_width // num_stations
    station_spacing = max(int(station_width * 0.05), 10)
    content_width = station_width - station_spacing
    
    # Font sizes
    station_name_font_size = max(int(remaining_height * 0.12), 18)
    station_name_font = _load_font(station_name_font_size)
    station_id_font_size = max(int(remaining_height * 0.08), 14)
    station_id_font = _load_font(station_id_font_size)
    tide_label_font_size = max(int(remaining_height * 0.10), 16)
    tide_label_font = _load_font(tide_label_font_size)
    tide_time_font_size = max(int(remaining_height * 0.11), 16)
    tide_time_font = _load_font(tide_time_font_size)
    icon_size = max(int(remaining_height * 0.4), 48)
    
    # Render each station
    for i, station in enumerate(stations):
        station_x = inner_left + (i * station_width)
        station_center_x = station_x + content_width // 2
        
        content_y = current_y
        
        # Station name (centered, may wrap)
        station_name = station.get("station_name", "Unknown")
        # Simple word wrapping for long names
        name_words = station_name.split()
        name_lines = []
        current_line = ""
        for word in name_words:
            test_line = f"{current_line} {word}".strip()
            test_width, _ = _text_size(station_name_font, test_line)
            if test_width <= content_width:
                current_line = test_line
            else:
                if current_line:
                    name_lines.append(current_line)
                current_line = word
        if current_line:
            name_lines.append(current_line)
        
        # Draw name lines
        for line in name_lines[:2]:  # Max 2 lines
            line_width, _ = _text_size(station_name_font, line)
            name_x = station_center_x - line_width // 2
            draw.text((name_x, content_y), line, font=station_name_font, fill=primary_color)
            content_y += station_name_font_size
        
        content_y += max(int(height * 0.02), 8)
        
        # Station ID (centered)
        station_id = f"Station {station.get('station_id', '')}"
        station_id_width, _ = _text_size(station_id_font, station_id)
        station_id_x = station_center_x - station_id_width // 2
        draw.text((station_id_x, content_y), station_id, font=station_id_font, fill=primary_color)
        content_y += station_id_font_size + max(int(height * 0.03), 12)
        
        # Tide icon (centered)
        icon_name = station.get("icon_name", "unknown.png")
        tide_icon = _load_icon(icon_name, icon_size)
        icon_x = station_center_x - icon_size // 2
        image.paste(tide_icon, (icon_x, content_y), tide_icon)
        content_y += icon_size + max(int(height * 0.02), 8)
        
        # Tide type label (centered)
        tide_type = station.get("tide_type", "No data")
        tide_type_width, _ = _text_size(tide_label_font, tide_type)
        tide_type_x = station_center_x - tide_type_width // 2
        draw.text((tide_type_x, content_y), tide_type, font=tide_label_font, fill=primary_color)
        content_y += tide_label_font_size + max(int(height * 0.01), 4)
        
        # Tide time (centered)
        tide_time = station.get("tide_time", "--")
        tide_time_width, _ = _text_size(tide_time_font, tide_time)
        tide_time_x = station_center_x - tide_time_width // 2
        draw.text((tide_time_x, content_y), tide_time, font=tide_time_font, fill=primary_color)
    
    # Add credit line at the bottom with location and timestamp
    current_time = datetime.now().strftime("%I:%M %p").lstrip("0")
    
    # Get location from Tempest API (for consistent location across all overlays)
    forecast_data = fetch_forecast_data("imperial")
    if forecast_data:
        location = _format_location_with_state(forecast_data.get("location_name", ""))
    else:
        location = ""
    
    # Build credit text with location and NOAA attribution
    if location:
        credit_text = f"{location} | Tide data from NOAA | {current_time}"
    else:
        credit_text = f"Tide data from NOAA | {current_time}"
    
    # Make credit line bright, bold, and highly visible
    credit_font = _load_font(credit_font_size)
    credit_color = (255, 255, 255, 255)
    
    # Center the credit text at the bottom
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - credit_bottom_margin
    
    # Draw text multiple times with slight offsets to simulate bold effect
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
