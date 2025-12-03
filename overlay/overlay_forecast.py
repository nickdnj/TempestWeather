"""
Forecast overlay module for Tempest weather data.
Fetches forecast data from Tempest public API and renders overlay images
matching the style of the current conditions overlay.
"""
from __future__ import annotations

import io
import math
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
from tide_client import get_next_tide_event, TideEvent, get_tide_stage
from astronomy_client import get_moon_data, get_solunar_periods
from water_temp_client import get_water_temp_with_activity
from pressure_trend import calculate_pressure_trend, format_pressure

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


def _generate_temperature_icon(size: int) -> Image.Image:
    """Generate a simple thermometer icon."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    
    # White outline color
    outline_color = (255, 255, 255, 255)
    line_width = max(2, size // 32)
    
    # Thermometer bulb (bottom circle)
    bulb_size = size // 3
    bulb_center = (size // 2, size - bulb_size // 2 - line_width)
    bulb_bbox = [
        bulb_center[0] - bulb_size // 2,
        bulb_center[1] - bulb_size // 2,
        bulb_center[0] + bulb_size // 2,
        bulb_center[1] + bulb_size // 2
    ]
    
    # Draw bulb outline
    draw.ellipse(bulb_bbox, outline=outline_color, width=line_width)
    
    # Thermometer stem (rectangle)
    stem_width = size // 6
    stem_left = size // 2 - stem_width // 2
    stem_right = size // 2 + stem_width // 2
    stem_top = size // 4
    stem_bottom = bulb_center[1] - bulb_size // 2
    
    # Draw stem outline (rectangular)
    draw.rectangle(
        [stem_left, stem_top, stem_right, stem_bottom],
        outline=outline_color,
        width=line_width
    )
    
    # Small indicator lines on stem
    num_markers = 3
    for i in range(1, num_markers):
        y = stem_top + (stem_bottom - stem_top) * i / num_markers
        marker_len = stem_width * 1.5
        draw.line(
            [stem_left - marker_len // 2, y, stem_left, y],
            fill=outline_color,
            width=max(1, line_width // 2)
        )
    
    return icon


def _generate_uv_index_icon(size: int) -> Image.Image:
    """Generate a simple sun with rays icon for UV index."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    
    # White outline color
    outline_color = (255, 255, 255, 255)
    line_width = max(2, size // 32)
    
    center_x = size // 2
    center_y = size // 2
    sun_radius = size // 4
    
    # Draw sun circle
    sun_bbox = [
        center_x - sun_radius,
        center_y - sun_radius,
        center_x + sun_radius,
        center_y + sun_radius
    ]
    draw.ellipse(sun_bbox, outline=outline_color, width=line_width)
    
    # Draw rays (8 rays)
    num_rays = 8
    ray_length = size // 8
    for i in range(num_rays):
        # Calculate angle for each ray
        angle_deg = i * (360 / num_rays)
        angle_rad = math.radians(angle_deg)
        
        # Calculate ray start and end points
        start_radius = sun_radius + line_width // 2
        end_radius = sun_radius + ray_length
        
        start_x = center_x + start_radius * math.cos(angle_rad)
        start_y = center_y + start_radius * math.sin(angle_rad)
        end_x = center_x + end_radius * math.cos(angle_rad)
        end_y = center_y + end_radius * math.sin(angle_rad)
        
        draw.line([start_x, start_y, end_x, end_y], fill=outline_color, width=line_width)
    
    return icon


def _generate_pressure_icon(size: int) -> Image.Image:
    """Generate a simple barometer/arrow icon for pressure."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    
    # White outline color
    outline_color = (255, 255, 255, 255)
    line_width = max(2, size // 32)
    
    center_x = size // 2
    center_y = size // 2
    
    # Draw circular gauge
    gauge_radius = size // 3
    gauge_bbox = [
        center_x - gauge_radius,
        center_y - gauge_radius,
        center_x + gauge_radius,
        center_y + gauge_radius
    ]
    draw.arc(gauge_bbox, start=180, end=360, fill=outline_color, width=line_width)
    
    # Draw arrow pointing up (indicating pressure measurement)
    arrow_length = gauge_radius * 0.8
    arrow_start_y = center_y
    arrow_end_y = center_y - arrow_length
    
    # Arrow shaft
    draw.line(
        [center_x, arrow_start_y, center_x, arrow_end_y],
        fill=outline_color,
        width=line_width
    )
    
    # Arrowhead (pointing up) - draw as lines for better outline effect
    arrowhead_size = size // 8
    arrowhead_left = (center_x - arrowhead_size // 2, arrow_end_y + arrowhead_size // 2)
    arrowhead_right = (center_x + arrowhead_size // 2, arrow_end_y + arrowhead_size // 2)
    arrowhead_top = (center_x, arrow_end_y)
    
    # Draw arrowhead outline
    draw.line([arrowhead_top, arrowhead_left], fill=outline_color, width=line_width)
    draw.line([arrowhead_top, arrowhead_right], fill=outline_color, width=line_width)
    draw.line([arrowhead_left, arrowhead_right], fill=outline_color, width=line_width)
    
    return icon


def _ensure_generated_icon(icon_name: str) -> None:
    """Ensure a generated icon exists on disk, creating it if necessary."""
    icon_path = os.path.join(ICONS_DIR, icon_name)
    
    # If icon already exists, skip generation
    if os.path.isfile(icon_path):
        return
    
    # Generate icon if it's one of our generated types
    size = 64  # Standard size for on-disk storage, will be resized as needed
    
    # Ensure icons directory exists
    os.makedirs(ICONS_DIR, exist_ok=True)
    
    if icon_name == "temperature.png":
        icon = _generate_temperature_icon(size)
        icon.save(icon_path, "PNG")
    elif icon_name == "uv_index.png":
        icon = _generate_uv_index_icon(size)
        icon.save(icon_path, "PNG")
    elif icon_name == "pressure.png":
        icon = _generate_pressure_icon(size)
        icon.save(icon_path, "PNG")


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
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
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
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
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
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
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
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
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
        # Use station ID in URL path, not as query parameter
        url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}.json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract station name from the response
        stations = data.get("stations", [])
        if stations and len(stations) > 0:
            return stations[0].get("name", f"Station {station_id}")
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
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
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


def build_current_conditions_expanded_payload(observation, units: str = "imperial") -> Dict:
    """
    Build payload for expanded current conditions overlay using Tempest API.
    Includes additional metrics like Feels Like, UV, Pressure, Rain.
    
    Args:
        observation: TempestObservation from local UDP listener (used as fallback)
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with expanded current conditions data formatted for rendering
    """
    # Fetch data from Tempest API for accurate icon and location
    forecast_data = fetch_forecast_data(units)
    
    station_id = TEMPEST_STATION_ID
    unit_symbol = "°F" if units == "imperial" else "°C"
    wind_unit = "mph" if units == "imperial" else "km/h"
    pressure_unit = "inHg" if units == "imperial" else "mb"
    rain_unit = "in" if units == "imperial" else "mm"
    
    if not forecast_data or "current_conditions" not in forecast_data:
        # Fallback to "waiting" state
        return {
            "error": False,
            "title": "Current Conditions",
            "temperature": "--",
            "wind": "--",
            "humidity": "--",
            "feels_like": "--",
            "uv": "--",
            "pressure": "--",
            "rain_today": "--",
            "icon_name": "unknown.png",
            "location_name": _format_location_with_state(forecast_data.get("location_name", "")) if forecast_data else "",
            "station_id": station_id,
            "cache_key": ("waiting", "expanded", units),
        }
    
    # Extract location from API
    location_name = _format_location_with_state(forecast_data.get("location_name", ""))
    
    # Get current conditions from API
    current = forecast_data.get("current_conditions", {})
    
    # Temperature
    temp = current.get("air_temperature")
    temperature = f"{int(temp)}{unit_symbol}" if temp is not None else "--"
    
    # Feels Like
    feels_like_val = current.get("feels_like")
    feels_like = f"{int(feels_like_val)}{unit_symbol}" if feels_like_val is not None else "--"
    
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
    
    # UV Index
    uv_val = current.get("uv")
    uv = f"{uv_val:.1f}" if uv_val is not None else "--"
    
    # Pressure
    pressure_val = current.get("sea_level_pressure")
    pressure = f"{pressure_val:.2f} {pressure_unit}" if pressure_val is not None else "--"
    if units == "metric" and pressure_val is not None:
         pressure = f"{int(pressure_val)} {pressure_unit}"

    # Rain Today
    rain_val = current.get("precip_accum_local_day")
    rain_today = f"{rain_val:.2f} {rain_unit}" if rain_val is not None else "--"
    
    # Icon from API
    icon_api_name = current.get("icon", "unknown")
    icon_name = FORECAST_ICON_MAP.get(icon_api_name, "unknown.png")
    
    # Conditions text (e.g. "Cloudy") - API doesn't always provide this directly in current_conditions,
    # but we can infer or map it. For now, we'll use the icon name as a proxy or empty if not available.
    # Actually, let's check if 'conditions' is in current_conditions.
    conditions = current.get("conditions", "")
    if not conditions:
        # Fallback: Capitalize icon name (e.g. "cloudy" -> "Cloudy")
        conditions = icon_api_name.replace("-", " ").title()

    cache_key = (
        current.get("time"),
        temp,
        feels_like_val,
        wind_speed,
        humidity_val,
        uv_val,
        pressure_val,
        rain_val,
        units,
    )
    
    return {
        "error": False,
        "title": "Current Conditions",
        "temperature": temperature,
        "conditions": conditions,
        "wind": wind,
        "humidity": humidity,
        "feels_like": feels_like,
        "uv": uv,
        "pressure": pressure,
        "rain_today": rain_today,
        "icon_name": icon_name,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def render_current_conditions_expanded_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render expanded current conditions overlay with a grid layout.
    
    Args:
        payload: Expanded current conditions data
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
    
    title_font_size = max(int(height * 0.15), 36) # Smaller title like 5-day
    title_font = _load_font(title_font_size)
    title = payload.get("title", "Current Conditions")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.04), 16)
    
    # Calculate space needed at bottom for credit line
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding
    
    remaining_height = height - current_y - bottom_reserved
    available_width = width - inner_left - padding
    
    # Layout: Left Column (25%) for Main Temp/Icon, Right Column (75%) for Grid
    left_col_width = int(available_width * 0.25)
    right_col_width = available_width - left_col_width
    
    # --- Left Column: Icon, Temp, Conditions ---
    left_center_x = inner_left + left_col_width // 2
    
    # Icon (smaller to prevent overlap)
    icon_size = max(int(remaining_height * 0.4), 48)
    icon_name = payload.get("icon_name", "unknown.png")
    condition_icon = _load_icon(icon_name, icon_size)
    icon_x = left_center_x - icon_size // 2
    icon_y = current_y + max((remaining_height - icon_size) // 2 - int(remaining_height * 0.1), 0)
    image.paste(condition_icon, (icon_x, icon_y), condition_icon)
    
    # Temperature (below icon)
    temp_font_size = max(int(remaining_height * 0.22), 28)
    temp_font = _load_font(temp_font_size)
    temperature = payload.get("temperature", "--")
    temp_width, temp_height = _text_size(temp_font, temperature)
    temp_x = left_center_x - temp_width // 2
    temp_y = icon_y + icon_size + max(int(height * 0.01), 4)
    draw.text((temp_x, temp_y), temperature, font=temp_font, fill=primary_color)
    
    # Conditions Text (below temp)
    cond_font_size = max(int(remaining_height * 0.09), 14)
    cond_font = _load_font(cond_font_size)
    conditions = payload.get("conditions", "")
    cond_width, _ = _text_size(cond_font, conditions)
    cond_x = left_center_x - cond_width // 2
    cond_y = temp_y + temp_height + max(int(height * 0.01), 4)
    draw.text((cond_x, cond_y), conditions, font=cond_font, fill=primary_color)
    
    # --- Right Column: 2x3 Grid ---
    # Grid items: Wind, Humidity, Feels Like, UV, Pressure, Rain
    grid_x_start = inner_left + left_col_width
    grid_width = right_col_width
    
    num_cols = 3
    num_rows = 2
    cell_width = grid_width // num_cols
    cell_height = remaining_height // num_rows
    
    grid_items = [
        {"label": "Wind", "value": payload.get("wind", "--"), "icon": "wind.png"},
        {"label": "Humidity", "value": payload.get("humidity", "--"), "icon": "humidity.png"},
        {"label": "Feels Like", "value": payload.get("feels_like", "--"), "icon": None},
        {"label": "UV Index", "value": payload.get("uv", "--"), "icon": None},
        {"label": "Pressure", "value": payload.get("pressure", "--"), "icon": None},
        {"label": "Rain Today", "value": payload.get("rain_today", "--"), "icon": None},
    ]
    
    # Smaller font sizes to prevent overlap
    label_font_size = max(int(cell_height * 0.15), 12)
    label_font = _load_font(label_font_size)
    value_font_size = max(int(cell_height * 0.20), 14)
    value_font = _load_font(value_font_size)
    
    for i, item in enumerate(grid_items):
        row = i // num_cols
        col = i % num_cols
        
        cell_x = grid_x_start + (col * cell_width)
        cell_y = current_y + (row * cell_height)
        cell_center_x = cell_x + cell_width // 2
        cell_center_y = cell_y + cell_height // 2
        
        # Calculate total height of content to center vertically with more spacing
        spacing_between = max(int(cell_height * 0.08), 6)
        content_height = label_font_size + spacing_between + value_font_size
        start_y = cell_center_y - content_height // 2
        
        # Draw Label
        label = item["label"]
        label_width, _ = _text_size(label_font, label)
        draw.text((cell_center_x - label_width // 2, start_y), label, font=label_font, fill=primary_color)
        
        # Draw Value (with optional icon)
        value = item["value"]
        value_y = start_y + label_font_size + spacing_between
        
        if item["icon"]:
            # Icon + Value - align icon with text baseline
            icon_size_small = int(value_font_size * 0.9)  # Slightly smaller icon
            icon = _load_icon(item["icon"], icon_size_small)
            val_width, val_height = _text_size(value_font, value)
            
            # Increase spacing significantly to prevent overlap
            icon_spacing = max(int(cell_width * 0.08), 10)
            
            total_width = icon_size_small + icon_spacing + val_width
            
            start_x = cell_center_x - total_width // 2
            
            # Align icon vertically with text (adjust for text baseline)
            icon_y = value_y + (val_height - icon_size_small) // 2
            image.paste(icon, (start_x, icon_y), icon)
            draw.text((start_x + icon_size_small + icon_spacing, value_y), value, font=value_font, fill=primary_color)
        else:
            # Just Value
            val_width, _ = _text_size(value_font, value)
            draw.text((cell_center_x - val_width // 2, value_y), value, font=value_font, fill=primary_color)

    # Add credit line at the bottom
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network | {current_time}"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network | {current_time}"
    else:
        credit_text = f"Data from Tempest Weather Network | {current_time}"
    
    credit_font = _load_font(credit_font_size)
    credit_color = (255, 255, 255, 255)
    
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - max(int(height * 0.03), 10)
    
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def build_current_conditions_super_payload(observation, units: str = "imperial") -> Dict:
    """
    Build payload for super-expanded current conditions overlay using Tempest API.
    Includes ALL available metrics: Temperature, Feels Like, Wind, Wind Gust, Humidity, 
    Dew Point, UV, Pressure, Rain Today, Solar Radiation, Lightning.
    
    Args:
        observation: TempestObservation from local UDP listener (used for real-time local data)
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with comprehensive current conditions data formatted for rendering
    """
    # Fetch data from Tempest API for accurate icon and location
    forecast_data = fetch_forecast_data(units)
    
    station_id = TEMPEST_STATION_ID
    unit_symbol = "°F" if units == "imperial" else "°C"
    wind_unit = "mph" if units == "imperial" else "km/h"
    pressure_unit = "inHg" if units == "imperial" else "mb"
    rain_unit = "in" if units == "imperial" else "mm"
    
    if not forecast_data or "current_conditions" not in forecast_data:
        # Fallback to "waiting" state
        return {
            "error": False,
            "title": "Current Conditions",
            "temperature": "--",
            "wind": "--",
            "wind_gust": "--",
            "humidity": "--",
            "feels_like": "--",
            "dew_point": "--",
            "uv": "--",
            "solar": "--",
            "pressure": "--",
            "rain_today": "--",
            "lightning": "--",
            "icon_name": "unknown.png",
            "location_name": _format_location_with_state(forecast_data.get("location_name", "")) if forecast_data else "",
            "station_id": station_id,
            "cache_key": ("waiting", "super", units),
        }
    
    # Extract location from API
    location_name = _format_location_with_state(forecast_data.get("location_name", ""))
    
    # Get current conditions from API
    current = forecast_data.get("current_conditions", {})
    
    # Temperature
    temp = current.get("air_temperature")
    temperature = f"{int(temp)}{unit_symbol}" if temp is not None else "--"
    
    # Feels Like
    feels_like_val = current.get("feels_like")
    feels_like = f"{int(feels_like_val)}{unit_symbol}" if feels_like_val is not None else "--"
    
    # Dew Point
    dew_point_val = current.get("dew_point")
    dew_point = f"{int(dew_point_val)}{unit_symbol}" if dew_point_val is not None else "--"
    
    # Wind Average
    wind_speed = current.get("wind_avg")
    wind_direction = current.get("wind_direction")
    if wind_speed is not None:
        wind_text = f"{int(wind_speed)} {wind_unit}"
        if wind_direction is not None:
            wind_text += f" {_degrees_to_compass(wind_direction)}"
        wind = wind_text
    else:
        wind = "--"
    
    # Wind Gust
    wind_gust_val = current.get("wind_gust")
    if wind_gust_val is not None:
        wind_gust = f"{int(wind_gust_val)} {wind_unit}"
    else:
        wind_gust = "--"
    
    # Humidity
    humidity_val = current.get("relative_humidity")
    humidity = f"{int(humidity_val)}%" if humidity_val is not None else "--"
    
    # UV Index
    uv_val = current.get("uv")
    uv = f"{uv_val:.1f}" if uv_val is not None else "--"
    
    # Solar Radiation
    solar_val = current.get("solar_radiation")
    solar = f"{int(solar_val)} W/m²" if solar_val is not None else "--"
    
    # Pressure
    pressure_val = current.get("sea_level_pressure")
    pressure = f"{pressure_val:.2f} {pressure_unit}" if pressure_val is not None else "--"
    if units == "metric" and pressure_val is not None:
         pressure = f"{int(pressure_val)} {pressure_unit}"

    # Rain Today
    rain_val = current.get("precip_accum_local_day")
    rain_today = f"{rain_val:.2f} {rain_unit}" if rain_val is not None else "--"
    
    # Lightning (last 3 hours) - need to check if available in API
    lightning_val = current.get("lightning_strike_count_last_3hr")
    if lightning_val is not None:
        lightning = f"{int(lightning_val)} strikes" if lightning_val > 0 else "None"
    else:
        lightning = "--"
    
    # Icon from API
    icon_api_name = current.get("icon", "unknown")
    icon_name = FORECAST_ICON_MAP.get(icon_api_name, "unknown.png")
    
    # Conditions text
    conditions = current.get("conditions", "")
    if not conditions:
        conditions = icon_api_name.replace("-", " ").title()

    cache_key = (
        current.get("time"),
        temp,
        feels_like_val,
        dew_point_val,
        wind_speed,
        wind_gust_val,
        humidity_val,
        uv_val,
        solar_val,
        pressure_val,
        rain_val,
        lightning_val,
        units,
    )
    
    return {
        "error": False,
        "title": "Current Conditions",
        "temperature": temperature,
        "conditions": conditions,
        "wind": wind,
        "wind_gust": wind_gust,
        "humidity": humidity,
        "feels_like": feels_like,
        "dew_point": dew_point,
        "uv": uv,
        "solar": solar,
        "pressure": pressure,
        "rain_today": rain_today,
        "lightning": lightning,
        "icon_name": icon_name,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def render_current_conditions_super_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render super-expanded current conditions overlay with 5-column layout.
    Title: "Current Conditions" with weather condition icon next to it (same height).
    Column 1: Temperature label, temperature icon, Temperature, Conditions, Feels Like
    Column 2: Wind label, wind icon, Wind speed/direction, Wind Gust
    Column 3: Humidity label, humidity icon, Humidity, Dew Point
    Column 4: UV Index label, UV index icon, UV Index value, Solar
    Column 5: Pressure label, pressure icon, Pressure, Rain Today
    
    Args:
        payload: Super-expanded current conditions data
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
    
    # Title with icon next to it
    inner_left = padding * 2
    current_y = padding
    
    title_font_size = max(int(height * 0.15), 36)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "Current Conditions")
    
    # Draw title text
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    title_width, title_height = _text_size(title_font, title)
    
    # Place weather condition icon to the right of title (same height)
    icon_name = payload.get("icon_name", "unknown.png")
    title_icon_size = title_font_size  # Match title height
    condition_icon = _load_icon(icon_name, title_icon_size)
    title_icon_spacing = max(int(title_font_size * 0.2), 8)
    title_icon_x = inner_left + title_width + title_icon_spacing
    title_icon_y = current_y + (title_height - title_icon_size) // 2
    image.paste(condition_icon, (int(title_icon_x), int(title_icon_y)), condition_icon)
    
    current_y += title_font_size + max(int(height * 0.04), 16)
    
    # Calculate space needed at bottom for credit line
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding
    
    remaining_height = height - current_y - bottom_reserved
    available_width = width - inner_left - padding
    
    # --- 5-Column Layout ---
    num_columns = 5
    column_width = available_width // num_columns
    column_spacing = max(int(column_width * 0.05), 10)
    content_width = column_width - column_spacing
    
    # Font sizes - use same size for all column text
    primary_font_size = max(int(remaining_height * 0.13), 18)
    primary_font = _load_font(primary_font_size)
    column_icon_size = max(int(remaining_height * 0.35), 48)
    
    # Ensure generated icons exist
    _ensure_generated_icon("temperature.png")
    _ensure_generated_icon("uv_index.png")
    _ensure_generated_icon("pressure.png")
    
    # --- Column 1: Temperature ---
    col1_x = inner_left
    col1_center_x = col1_x + content_width // 2
    content_y = current_y + max(int(height * 0.03), 12)
    
    # Temperature label
    temp_label = "Temperature"
    temp_label_width, _ = _text_size(primary_font, temp_label)
    draw.text((col1_center_x - temp_label_width // 2, content_y), temp_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + max(int(height * 0.015), 6)
    
    # Temperature icon
    temp_icon = _load_icon("temperature.png", column_icon_size)
    temp_icon_x = col1_center_x - column_icon_size // 2
    image.paste(temp_icon, (temp_icon_x, content_y), temp_icon)
    content_y += column_icon_size + max(int(height * 0.02), 8)
    
    # Temperature value
    temperature = payload.get("temperature", "--")
    temp_width, temp_height = _text_size(primary_font, temperature)
    draw.text((col1_center_x - temp_width // 2, content_y), temperature, font=primary_font, fill=primary_color)
    content_y += temp_height + max(int(height * 0.015), 6)
    
    # Conditions
    conditions = payload.get("conditions", "")
    cond_width, cond_height = _text_size(primary_font, conditions)
    draw.text((col1_center_x - cond_width // 2, content_y), conditions, font=primary_font, fill=primary_color)
    content_y += cond_height + max(int(height * 0.015), 6)
    
    # Feels Like
    feels_like = payload.get("feels_like", "--")
    feels_text = "Feels Like"
    feels_width, _ = _text_size(primary_font, feels_text)
    draw.text((col1_center_x - feels_width // 2, content_y), feels_text, font=primary_font, fill=primary_color)
    content_y += primary_font_size + 4
    feels_val_width, _ = _text_size(primary_font, feels_like)
    draw.text((col1_center_x - feels_val_width // 2, content_y), feels_like, font=primary_font, fill=primary_color)
    
    # --- Column 2: Wind ---
    col2_x = inner_left + column_width
    col2_center_x = col2_x + content_width // 2
    content_y = current_y + max(int(height * 0.03), 12)
    
    # Wind label
    wind_label = "Wind"
    wind_label_width, _ = _text_size(primary_font, wind_label)
    draw.text((col2_center_x - wind_label_width // 2, content_y), wind_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + max(int(height * 0.015), 6)
    
    # Wind icon (larger size to match other column icons)
    wind_icon = _load_icon("wind.png", column_icon_size)
    wind_icon_x = col2_center_x - column_icon_size // 2
    image.paste(wind_icon, (wind_icon_x, content_y), wind_icon)
    content_y += column_icon_size + max(int(height * 0.02), 8)
    
    # Wind value
    wind = payload.get("wind", "--")
    wind_val_width, wind_val_height = _text_size(primary_font, wind)
    draw.text((col2_center_x - wind_val_width // 2, content_y), wind, font=primary_font, fill=primary_color)
    content_y += wind_val_height + max(int(height * 0.02), 8)
    
    # Wind Gust label
    gust_label = "Wind Gust"
    gust_label_width, _ = _text_size(primary_font, gust_label)
    draw.text((col2_center_x - gust_label_width // 2, content_y), gust_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + 4
    
    # Wind Gust value
    wind_gust = payload.get("wind_gust", "--")
    gust_width, _ = _text_size(primary_font, wind_gust)
    draw.text((col2_center_x - gust_width // 2, content_y), wind_gust, font=primary_font, fill=primary_color)
    
    # --- Column 3: Humidity / Dew Point ---
    col3_x = inner_left + (column_width * 2)
    col3_center_x = col3_x + content_width // 2
    content_y = current_y + max(int(height * 0.03), 12)
    
    # Humidity label
    hum_label = "Humidity"
    hum_label_width, _ = _text_size(primary_font, hum_label)
    draw.text((col3_center_x - hum_label_width // 2, content_y), hum_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + max(int(height * 0.015), 6)
    
    # Humidity icon (larger size to match other column icons)
    hum_icon = _load_icon("humidity.png", column_icon_size)
    hum_icon_x = col3_center_x - column_icon_size // 2
    image.paste(hum_icon, (hum_icon_x, content_y), hum_icon)
    content_y += column_icon_size + max(int(height * 0.02), 8)
    
    # Humidity value
    humidity = payload.get("humidity", "--")
    hum_val_width, hum_val_height = _text_size(primary_font, humidity)
    draw.text((col3_center_x - hum_val_width // 2, content_y), humidity, font=primary_font, fill=primary_color)
    content_y += hum_val_height + max(int(height * 0.02), 8)
    
    # Dew Point label
    dew_label = "Dew Point"
    dew_label_width, _ = _text_size(primary_font, dew_label)
    draw.text((col3_center_x - dew_label_width // 2, content_y), dew_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + 4
    
    # Dew Point value
    dew_point = payload.get("dew_point", "--")
    dew_width, _ = _text_size(primary_font, dew_point)
    draw.text((col3_center_x - dew_width // 2, content_y), dew_point, font=primary_font, fill=primary_color)
    
    # --- Column 4: UV Index / Solar ---
    col4_x = inner_left + (column_width * 3)
    col4_center_x = col4_x + content_width // 2
    content_y = current_y + max(int(height * 0.03), 12)
    
    # UV Index label
    uv_label = "UV Index"
    uv_label_width, _ = _text_size(primary_font, uv_label)
    draw.text((col4_center_x - uv_label_width // 2, content_y), uv_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + max(int(height * 0.015), 6)
    
    # UV Index icon
    uv_icon = _load_icon("uv_index.png", column_icon_size)
    uv_icon_x = col4_center_x - column_icon_size // 2
    image.paste(uv_icon, (uv_icon_x, content_y), uv_icon)
    content_y += column_icon_size + max(int(height * 0.02), 8)
    
    # UV value
    uv = payload.get("uv", "--")
    uv_width, uv_height = _text_size(primary_font, uv)
    draw.text((col4_center_x - uv_width // 2, content_y), uv, font=primary_font, fill=primary_color)
    content_y += uv_height + max(int(height * 0.02), 8)
    
    # Solar label
    solar_label = "Solar"
    solar_label_width, _ = _text_size(primary_font, solar_label)
    draw.text((col4_center_x - solar_label_width // 2, content_y), solar_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + 4
    
    # Solar value
    solar = payload.get("solar", "--")
    solar_width, _ = _text_size(primary_font, solar)
    draw.text((col4_center_x - solar_width // 2, content_y), solar, font=primary_font, fill=primary_color)
    
    # --- Column 5: Pressure & Rain ---
    col5_x = inner_left + (column_width * 4)
    col5_center_x = col5_x + content_width // 2
    content_y = current_y + max(int(height * 0.03), 12)
    
    # Pressure label
    press_label = "Pressure"
    press_label_width, _ = _text_size(primary_font, press_label)
    draw.text((col5_center_x - press_label_width // 2, content_y), press_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + max(int(height * 0.015), 6)
    
    # Pressure icon
    press_icon = _load_icon("pressure.png", column_icon_size)
    press_icon_x = col5_center_x - column_icon_size // 2
    image.paste(press_icon, (press_icon_x, content_y), press_icon)
    content_y += column_icon_size + max(int(height * 0.02), 8)
    
    # Pressure value
    pressure = payload.get("pressure", "--")
    press_width, press_height = _text_size(primary_font, pressure)
    draw.text((col5_center_x - press_width // 2, content_y), pressure, font=primary_font, fill=primary_color)
    content_y += press_height + max(int(height * 0.02), 8)
    
    # Rain Today label
    rain_label = "Rain Today"
    rain_label_width, _ = _text_size(primary_font, rain_label)
    draw.text((col5_center_x - rain_label_width // 2, content_y), rain_label, font=primary_font, fill=primary_color)
    content_y += primary_font_size + 4
    
    # Rain Today value
    rain_today = payload.get("rain_today", "--")
    rain_width, _ = _text_size(primary_font, rain_today)
    draw.text((col5_center_x - rain_width // 2, content_y), rain_today, font=primary_font, fill=primary_color)
    
    # Add credit line at the bottom
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network | {current_time}"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network | {current_time}"
    else:
        credit_text = f"Data from Tempest Weather Network | {current_time}"
    
    credit_font = _load_font(credit_font_size)
    credit_color = (255, 255, 255, 255)
    
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - max(int(height * 0.03), 10)
    
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def build_fishing_report_payload(observation, units: str = "imperial") -> Dict:
    """
    Build payload for fishing report overlay.
    Includes tide stage, barometric pressure, moon phase, water temp, and solunar times.
    
    Args:
        observation: TempestObservation from local UDP listener
        units: 'imperial' or 'metric'
    
    Returns:
        Dictionary with fishing data formatted for rendering
    """
    # Get configuration
    fishing_location = os.getenv("FISHING_LOCATION_NAME", "Shrewsbury River")
    fishing_lat = float(os.getenv("FISHING_LOCATION_LAT", "40.3646"))
    fishing_lon = float(os.getenv("FISHING_LOCATION_LON", "-74.0068"))
    tide_station = os.getenv("FISHING_TIDE_STATION", "8531662")
    water_temp_station = os.getenv("FISHING_WATER_TEMP_STATION", "8531680")
    station_state = os.getenv("TEMPEST_LOCATION_STATE", "NJ")
    
    # Fetch tide station name
    tide_station_name = _fetch_station_name(tide_station)
    
    # Format location with state
    if station_state:
        location_name = f"{fishing_location}, {station_state}"
    else:
        location_name = fishing_location
    
    unit_symbol = "°F" if units == "imperial" else "°C"
    
    # 1. Get tide stage
    tide_stage = get_tide_stage(tide_station)
    if tide_stage:
        tide_stage_text = tide_stage.stage
        tide_next_event = tide_stage.next_event
        tide_next_time = tide_stage.next_time.strftime("%I:%M %p").lstrip("0")
        tide_height = tide_stage.height or "--"
        tide_icon = tide_stage.icon_name
    else:
        tide_stage_text = "Unknown"
        tide_next_event = "--"
        tide_next_time = "--"
        tide_height = "--"
        tide_icon = "unknown.png"
    
    # 2. Get barometric pressure from Tempest
    if observation and observation.pressure_hpa:
        # Convert hPa to inHg
        pressure_inhg = observation.pressure_hpa * 0.02953
        # For trend calculation, we'd ideally have historical data
        # For now, analyze current pressure only
        pressure_data = calculate_pressure_trend(pressure_inhg, None, mb_to_inhg=False)
        pressure_text = format_pressure(pressure_inhg, units)
        pressure_trend = pressure_data.trend
        pressure_trend_arrow = pressure_data.trend_arrow
        pressure_rating = pressure_data.fishing_rating
    else:
        pressure_text = "--"
        pressure_trend = "Unknown"
        pressure_trend_arrow = "?"
        pressure_rating = "Unknown"
    
    # 3. Get moon data and solunar periods
    import pytz
    timezone = pytz.timezone(os.getenv("TZ", "America/New_York"))
    
    moon_data = get_moon_data(fishing_lat, fishing_lon, timezone)
    if moon_data:
        moon_phase = moon_data.phase_name
        moon_illumination = f"{moon_data.illumination:.0f}%"
        moon_icon = moon_data.icon_name
    else:
        moon_phase = "Unknown"
        moon_illumination = "--"
        moon_icon = "unknown.png"
    
    solunar_data = get_solunar_periods(fishing_lat, fishing_lon, timezone)
    if solunar_data:
        solunar_major = solunar_data.major_label
        solunar_minor = solunar_data.minor_label
    else:
        solunar_major = "N/A"
        solunar_minor = "N/A"
    
    # 4. Get water temperature
    water_temp, water_activity = get_water_temp_with_activity(water_temp_station, units)
    if water_temp:
        water_temp_text = f"{water_temp:.0f}{unit_symbol}"
    else:
        water_temp_text = "--"
        water_activity = "Unknown"
    
    # 5. Get wind from Tempest
    if observation and observation.wind_speed_ms:
        if units == "metric":
            wind_speed = observation.wind_speed_ms * 3.6  # m/s to km/h
            wind_unit = "km/h"
        else:
            wind_speed = observation.wind_speed_ms * 2.23694  # m/s to mph
            wind_unit = "mph"
        
        if observation.wind_direction_deg is not None:
            wind_dir = _degrees_to_compass(observation.wind_direction_deg)
            wind_text = f"{int(wind_speed)} {wind_unit} {wind_dir}"
        else:
            wind_text = f"{int(wind_speed)} {wind_unit}"
    else:
        wind_text = "--"
    
    # Generate cache key
    cache_key = (
        "fishing",
        tide_stage_text,
        tide_next_time,
        pressure_text,
        moon_phase,
        water_temp_text,
        wind_text,
        units
    )
    
    return {
        "error": False,
        "title": "Fishing Report",
        "location_name": location_name,
        # Tide
        "tide_stage": tide_stage_text,
        "tide_next_event": tide_next_event,
        "tide_next_time": tide_next_time,
        "tide_height": tide_height,
        "tide_icon": tide_icon,
        "tide_station_name": tide_station_name,
        # Barometric
        "pressure": pressure_text,
        "pressure_trend": pressure_trend,
        "pressure_trend_arrow": pressure_trend_arrow,
        "pressure_rating": pressure_rating,
        # Moon
        "moon_phase": moon_phase,
        "moon_illumination": moon_illumination,
        "moon_icon": moon_icon,
        # Water Temperature
        "water_temp": water_temp_text,
        "water_activity": water_activity,
        # Solunar
        "solunar_major": solunar_major,
        "solunar_minor": solunar_minor,
        # Wind
        "wind": wind_text,
        # Cache
        "cache_key": cache_key,
    }


def render_fishing_report_overlay(
    payload: Dict, width: int, height: int, theme: str
) -> io.BytesIO:
    """
    Render fishing report overlay with 5-column layout plus wind row.
    
    Columns: Tide | Barometer | Moon Phase | Water Temp | Solunar
    Bottom: Wind conditions
    
    Args:
        payload: Fishing data from build_fishing_report_payload
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
        
        title = payload.get("title", "Fishing Report")
        message = payload.get("message", "Unable to load fishing data")
        
        title_width, title_height = _text_size(title_font, title)
        title_x = (width - title_width) // 2
        title_y = padding
        draw.text((title_x, title_y), title, font=title_font, fill=primary_color)
        
        message_width, message_height = _text_size(message_font, message)
        message_x = (width - message_width) // 2
        message_y = title_y + title_height + padding
        draw.text((message_x, message_y), message, font=message_font, fill=primary_color)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    
    # Title
    inner_left = padding * 2
    current_y = padding
    
    title_font_size = max(int(height * 0.15), 36)
    title_font = _load_font(title_font_size)
    title = payload.get("title", "Fishing Report")
    draw.text((inner_left, current_y), title, font=title_font, fill=primary_color)
    current_y += title_font_size + max(int(height * 0.04), 16)
    
    # Calculate space for credit line and wind row
    credit_font_size = max(int(height * 0.08), 16)
    credit_bottom_margin = max(int(height * 0.03), 10)
    credit_top_spacing = max(int(height * 0.08), 30)
    wind_row_height = max(int(height * 0.12), 40)
    bottom_reserved = credit_font_size + credit_top_spacing + credit_bottom_margin + padding + wind_row_height
    
    remaining_height = height - current_y - bottom_reserved
    available_width = width - inner_left - padding
    
    # 5-Column Layout
    num_columns = 5
    column_width = available_width // num_columns
    column_spacing = max(int(column_width * 0.05), 10)
    content_width = column_width - column_spacing
    
    # Font sizes
    label_font_size = max(int(remaining_height * 0.12), 16)
    label_font = _load_font(label_font_size)
    value_font_size = max(int(remaining_height * 0.16), 20)
    value_font = _load_font(value_font_size)
    sub_font_size = max(int(remaining_height * 0.12), 14)
    sub_font = _load_font(sub_font_size)
    icon_size = max(int(remaining_height * 0.35), 48)
    
    # Column 1: Tide
    col1_x = inner_left
    col1_center_x = col1_x + content_width // 2
    col_y = current_y
    
    # Label
    label = "TIDE"
    label_width, _ = _text_size(label_font, label)
    draw.text((col1_center_x - label_width // 2, col_y), label, font=label_font, fill=primary_color)
    col_y += label_font_size + max(int(height * 0.02), 8)
    
    # Icon
    tide_icon = _load_icon(payload.get("tide_icon", "high_tide.png"), icon_size)
    icon_x = col1_center_x - icon_size // 2
    image.paste(tide_icon, (icon_x, col_y), tide_icon)
    col_y += icon_size + max(int(height * 0.02), 8)
    
    # Stage
    stage = payload.get("tide_stage", "--")
    stage_width, _ = _text_size(value_font, stage)
    draw.text((col1_center_x - stage_width // 2, col_y), stage, font=value_font, fill=primary_color)
    col_y += value_font_size + 4
    
    # Next event
    next_event = f"{payload.get('tide_next_event', '--')} @ {payload.get('tide_next_time', '--')}"
    next_width, _ = _text_size(sub_font, next_event)
    draw.text((col1_center_x - next_width // 2, col_y), next_event, font=sub_font, fill=primary_color)
    
    # Column 2: Barometric Pressure
    col2_x = inner_left + column_width
    col2_center_x = col2_x + content_width // 2
    col_y = current_y
    
    label = "BAROMETER"
    label_width, _ = _text_size(label_font, label)
    draw.text((col2_center_x - label_width // 2, col_y), label, font=label_font, fill=primary_color)
    col_y += label_font_size + max(int(height * 0.02), 8)
    
    # Use wind icon as placeholder for barometer (or create barometer.png)
    pressure_icon = _load_icon("wind.png", icon_size)
    icon_x = col2_center_x - icon_size // 2
    image.paste(pressure_icon, (icon_x, col_y), pressure_icon)
    col_y += icon_size + max(int(height * 0.02), 8)
    
    # Pressure
    pressure = payload.get("pressure", "--")
    pressure_width, _ = _text_size(value_font, pressure)
    draw.text((col2_center_x - pressure_width // 2, col_y), pressure, font=value_font, fill=primary_color)
    col_y += value_font_size + 4
    
    # Trend and rating
    trend_text = f"{payload.get('pressure_trend_arrow', '?')} {payload.get('pressure_trend', 'Unknown')}"
    trend_width, _ = _text_size(sub_font, trend_text)
    draw.text((col2_center_x - trend_width // 2, col_y), trend_text, font=sub_font, fill=primary_color)
    col_y += sub_font_size + 2
    rating = payload.get("pressure_rating", "--")
    rating_width, _ = _text_size(sub_font, rating)
    draw.text((col2_center_x - rating_width // 2, col_y), rating, font=sub_font, fill=primary_color)
    
    # Column 3: Moon Phase
    col3_x = inner_left + (column_width * 2)
    col3_center_x = col3_x + content_width // 2
    col_y = current_y
    
    label = "MOON PHASE"
    label_width, _ = _text_size(label_font, label)
    draw.text((col3_center_x - label_width // 2, col_y), label, font=label_font, fill=primary_color)
    col_y += label_font_size + max(int(height * 0.02), 8)
    
    # Moon icon
    moon_icon = _load_icon(payload.get("moon_icon", "unknown.png"), icon_size)
    icon_x = col3_center_x - icon_size // 2
    image.paste(moon_icon, (icon_x, col_y), moon_icon)
    col_y += icon_size + max(int(height * 0.02), 8)
    
    # Phase name
    phase = payload.get("moon_phase", "--")
    phase_width, _ = _text_size(value_font, phase)
    draw.text((col3_center_x - phase_width // 2, col_y), phase, font=value_font, fill=primary_color)
    col_y += value_font_size + 4
    
    # Illumination
    illumination = payload.get("moon_illumination", "--")
    illum_width, _ = _text_size(sub_font, illumination)
    draw.text((col3_center_x - illum_width // 2, col_y), illumination, font=sub_font, fill=primary_color)
    
    # Column 4: Water Temperature
    col4_x = inner_left + (column_width * 3)
    col4_center_x = col4_x + content_width // 2
    col_y = current_y
    
    label = "WATER TEMP"
    label_width, _ = _text_size(label_font, label)
    draw.text((col4_center_x - label_width // 2, col_y), label, font=label_font, fill=primary_color)
    col_y += label_font_size + max(int(height * 0.02), 8)
    
    # Use humidity icon as placeholder for thermometer
    temp_icon = _load_icon("humidity.png", icon_size)
    icon_x = col4_center_x - icon_size // 2
    image.paste(temp_icon, (icon_x, col_y), temp_icon)
    col_y += icon_size + max(int(height * 0.02), 8)
    
    # Temperature
    temp = payload.get("water_temp", "--")
    temp_width, _ = _text_size(value_font, temp)
    draw.text((col4_center_x - temp_width // 2, col_y), temp, font=value_font, fill=primary_color)
    col_y += value_font_size + 4
    
    # Activity
    activity = payload.get("water_activity", "--")
    activity_width, _ = _text_size(sub_font, activity)
    draw.text((col4_center_x - activity_width // 2, col_y), activity, font=sub_font, fill=primary_color)
    
    # Column 5: Solunar
    col5_x = inner_left + (column_width * 4)
    col5_center_x = col5_x + content_width // 2
    col_y = current_y
    
    label = "SOLUNAR"
    label_width, _ = _text_size(label_font, label)
    draw.text((col5_center_x - label_width // 2, col_y), label, font=label_font, fill=primary_color)
    col_y += label_font_size + max(int(height * 0.02), 8)
    
    # Use clear icon as sun placeholder for solunar
    solunar_icon = _load_icon("clear.png", icon_size)
    icon_x = col5_center_x - icon_size // 2
    image.paste(solunar_icon, (icon_x, col_y), solunar_icon)
    col_y += icon_size + max(int(height * 0.02), 8)
    
    # Major period
    major_text = f"Major: {payload.get('solunar_major', 'N/A')}"
    major_width, _ = _text_size(value_font, major_text)
    draw.text((col5_center_x - major_width // 2, col_y), major_text, font=value_font, fill=primary_color)
    col_y += value_font_size + 4
    
    # Minor period
    minor_text = f"Minor: {payload.get('solunar_minor', 'N/A')}"
    minor_width, _ = _text_size(sub_font, minor_text)
    draw.text((col5_center_x - minor_width // 2, col_y), minor_text, font=sub_font, fill=primary_color)
    
    # Wind row (full width, below columns)
    wind_y = height - bottom_reserved + wind_row_height // 4
    wind_font_size = max(int(wind_row_height * 0.4), 20)
    wind_font = _load_font(wind_font_size)
    wind_text = f"Wind: {payload.get('wind', '--')}"
    wind_width, _ = _text_size(wind_font, wind_text)
    wind_x = (width - wind_width) // 2
    draw.text((wind_x, wind_y), wind_text, font=wind_font, fill=primary_color)
    
    # Credit line
    location = payload.get("location_name", "")
    tide_station_name = payload.get("tide_station_name", "")
    now = datetime.now()
    day = str(now.day)  # Remove leading zero from day
    hour = str(int(now.strftime("%I")))  # Remove leading zero from hour
    current_time = f"{now.strftime('%a %b')} {day} {hour}:{now.strftime('%M%p')}"  # "Wed Dec 3 1:55PM"
    
    if tide_station_name:
        credit_text = f"{location} | Tide: {tide_station_name} | {current_time}"
    else:
        credit_text = f"{location} | Tide: NOAA | {current_time}"
    
    credit_font = _load_font(credit_font_size)
    credit_color = (255, 255, 255, 255)
    
    credit_width, credit_height = _text_size(credit_font, credit_text)
    credit_x = (width - credit_width) // 2
    credit_y = height - credit_height - credit_bottom_margin
    
    for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, font=credit_font, fill=credit_color)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
