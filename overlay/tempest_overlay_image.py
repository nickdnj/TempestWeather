from __future__ import annotations

import io
import os
import threading
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont

try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS  # Pillow >= 9.1
except AttributeError:  # pragma: no cover - legacy Pillow fallback
    RESAMPLING_FILTER = Image.LANCZOS

from tempest_listener import TempestObservation
from tide_client import get_next_tide_event

FONT_PATH = os.path.join(os.path.dirname(__file__), "../fonts/Arial.ttf")
ICONS_DIR = os.path.join(os.path.dirname(__file__), "../weather_icons")

# Icon names for precipitation codes; fallback handled separately.
PRECIP_ICON_MAP = {
    1: "rain.png",
    2: "snow.png",
    3: "thunderstorm.png",
}

# Theme presets for background and text colors.
THEME_STYLES = {
    "dark": {
        "background": (18, 24, 38, 220),
        "text": (235, 240, 255, 255),
    },
    "light": {
        "background": (246, 248, 252, 220),
        "text": (24, 33, 54, 255),
    },
}

_cache_lock = threading.Lock()
_image_cache: Dict[tuple, bytes] = {}
_icon_cache: Dict[tuple, Image.Image] = {}


def _text_size(font: ImageFont.ImageFont, text: str) -> tuple[int, int]:
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    return font.getsize(text)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _c_to_f(value_c: float) -> float:
    return value_c * 9 / 5 + 32


def _ms_to_mph(value_ms: float) -> float:
    return value_ms * 2.23694


def _ms_to_kmh(value_ms: float) -> float:
    return value_ms * 3.6


def _degrees_to_compass(degrees: Optional[float]) -> str:
    if degrees is None:
        return "--"
    sectors = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    idx = int((degrees + 11.25) / 22.5) % 16
    return sectors[idx]


def build_display_payload(
    observation: Optional[TempestObservation],
    units: str,
    header_line_one: str = "",
    header_line_two: str = "",
    tide_station: Optional[str] = None,
) -> Dict[str, str]:
    units = "metric" if units.lower() == "metric" else "imperial"
    
    # Get location and station info for credit line
    location_name = header_line_one  # Use first header line as location
    station_id = os.getenv("TEMPEST_STATION_ID", "")

    icon_name = _select_icon_name(observation)
    tide_event = get_next_tide_event(tide_station) if tide_station else None
    tide_icon_name: Optional[str] = None
    tide_event_text: Optional[str] = None
    tide_time_text: Optional[str] = None
    if tide_event:
        tide_icon_name = tide_event.icon_name
        tide_event_text = tide_event.event_type
        tide_time_text = tide_event.event_time.strftime("%I:%M %p").lstrip("0")

    tide_cache_key = (
        tide_event.event_type if tide_event else None,
        tide_event.event_time.isoformat() if tide_event else None,
    )

    if observation is None:
        cache_key = (
            "waiting",
            units,
            icon_name,
            header_line_one,
            header_line_two,
            tide_cache_key,
        )
        return {
            "icon_name": icon_name,
            "temperature": "--",
            "wind": "--",
            "humidity": "--",
            "updated": "Waiting for data…",
            "header1": header_line_one,
            "header2": header_line_two,
            "tide_event": tide_event_text,
            "tide_time": tide_time_text,
            "tide_icon_name": tide_icon_name,
            "location_name": location_name,
            "station_id": station_id,
            "cache_key": cache_key,
        }

    temperature = "--"
    if observation.temperature_c is not None:
        if units == "metric":
            temperature = f"{round(observation.temperature_c):.0f}°C"
        else:
            temperature = f"{round(_c_to_f(observation.temperature_c)):.0f}°F"

    wind_speed = "--"
    if observation.wind_speed_ms is not None:
        if units == "metric":
            wind_speed = f"{_ms_to_kmh(observation.wind_speed_ms):.0f} km/h"
        else:
            wind_speed = f"{_ms_to_mph(observation.wind_speed_ms):.0f} mph"
    wind = (
        f"{wind_speed} {_degrees_to_compass(observation.wind_direction_deg)}"
        if wind_speed != "--"
        else "--"
    )

    humidity = (
        f"{observation.humidity:.0f}%"
        if observation.humidity is not None
        else "--"
    )

    # Convert UTC timestamp to local timezone (container runs in station's timezone)
    updated_local = observation.observed_at.astimezone()
    # Format: "2025-10-22 09:50 AM EDT" (using 12-hour format with AM/PM)
    updated = updated_local.strftime("%Y-%m-%d %I:%M %p %Z").replace(" 0", " ")

    cache_key = (
        observation.cache_token,
        units,
        icon_name,
        header_line_one,
        header_line_two,
        tide_cache_key,
    )

    return {
        "icon_name": icon_name,
        "temperature": temperature,
        "wind": wind,
        "humidity": humidity,
        "updated": updated,
        "header1": header_line_one,
        "header2": header_line_two,
        "tide_event": tide_event_text,
        "tide_time": tide_time_text,
        "tide_icon_name": tide_icon_name,
        "location_name": location_name,
        "station_id": station_id,
        "cache_key": cache_key,
    }


def render_overlay_image(
    payload: Dict[str, str], width: int, height: int, theme: str
) -> io.BytesIO:
    theme = theme.lower()
    style = THEME_STYLES.get(theme, THEME_STYLES["dark"])

    cache_key = (width, height, theme, payload["cache_key"])
    with _cache_lock:
        cached = _image_cache.get(cache_key)
        if cached:
            stream = io.BytesIO(cached)
            stream.seek(0)
            return stream

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    padding = max(int(height * 0.06), 24)
    header_gap = max(int(height * 0.05), 24)
    row_gap = max(int(height * 0.04), 18)
    primary_color = style["text"]

    header_line_one = payload.get("header1", "").strip()
    header_line_two = payload.get("header2", "").strip()
    header_lines = [line for line in (header_line_one, header_line_two) if line]

    header_left = padding * 2
    current_y = padding
    available_header_width = width - header_left - padding

    for line in header_lines:
        size = max(int(height * 0.18), 64)
        font = _load_font(size)
        while size > 28 and _text_size(font, line)[0] > available_header_width:
            size -= 2
            font = _load_font(size)
        draw.text((header_left, current_y), line, font=font, fill=primary_color)
        current_y += size + header_gap

    if header_lines:
        current_y += row_gap

    weather_top = current_y
    remaining_height = max(height - weather_top - padding, int(height * 0.35))
    timestamp_font_size = max(int(remaining_height * 0.2), 24)
    timestamp_spacing = max(int(timestamp_font_size * 0.7), 20)
    weather_row_height = max(remaining_height - timestamp_font_size - timestamp_spacing, int(height * 0.32))

    temp_text = payload["temperature"]
    wind_text = payload["wind"]
    humidity_text = payload["humidity"]
    tide_event_text = (payload.get("tide_event") or "").strip()
    tide_time_text = (payload.get("tide_time") or "").strip()
    tide_icon_name = payload.get("tide_icon_name") if tide_event_text and tide_time_text else None

    def measure(font_size: int):
        icon_size = max(int(font_size * 1.2), int(weather_row_height * 0.55))
        spacing = max(int(font_size * 0.45), 30)
        small_spacing = max(int(font_size * 0.22), 14)
        wind_icon_size = max(int(font_size * 0.95), 32)
        humidity_icon_size = max(int(font_size * 0.95), 32)
        tide_spacing = max(int(font_size * 0.5), spacing)
        tide_icon_size = max(int(font_size * 0.95), 32) if tide_icon_name else 0

        main_font = _load_font(font_size)
        temp_width, _ = _text_size(main_font, temp_text)
        wind_width, _ = _text_size(main_font, wind_text)
        humidity_width, _ = _text_size(main_font, humidity_text)

        weather_width = (
            icon_size
            + spacing
            + temp_width
            + spacing
            + wind_icon_size
            + small_spacing
            + wind_width
            + spacing
            + humidity_icon_size
            + small_spacing
            + humidity_width
        )

        row_height = max(icon_size, font_size)
        tide_block_width = 0
        tide_block_height = font_size
        tide_time_font_size = 0
        tide_time_font = None
        tide_line_gap = 0
        if tide_icon_name:
            tide_time_font_size = max(int(font_size * 0.6), 22)
            tide_time_font = _load_font(tide_time_font_size)
            tide_line_gap = max(int(font_size * 0.15), 10)
            event_width, _ = _text_size(main_font, tide_event_text)
            time_width, _ = _text_size(tide_time_font, tide_time_text)
            tide_block_width = tide_icon_size + small_spacing + max(event_width, time_width)
            tide_block_height = font_size + tide_line_gap + tide_time_font_size
            row_height = max(row_height, tide_block_height)
            total_width = weather_width + tide_spacing + tide_block_width
        else:
            total_width = weather_width

        return total_width, {
            "font_size": font_size,
            "icon_size": icon_size,
            "main_font": main_font,
            "spacing": spacing,
            "small_spacing": small_spacing,
            "wind_icon_size": wind_icon_size,
            "humidity_icon_size": humidity_icon_size,
            "tide_spacing": tide_spacing,
            "tide_icon_size": tide_icon_size,
            "tide_time_font_size": tide_time_font_size,
            "tide_time_font": tide_time_font,
            "tide_block_width": tide_block_width,
            "tide_block_height": tide_block_height,
            "row_height": row_height,
            "tide_line_gap": tide_line_gap,
            "weather_width": weather_width,
        }

    inner_left = padding * 2
    available_width = width - padding - inner_left
    target_font_size = min(int(weather_row_height * 0.68), int(height * 0.34))
    font_size = target_font_size
    layout = None
    while font_size >= 30:
        total_width, metrics = measure(font_size)
        if total_width <= available_width and metrics["row_height"] <= weather_row_height:
            layout = metrics
            break
        font_size -= 2

    if layout is None:
        _, layout = measure(max(int(weather_row_height * 0.55), 30))

    primary_font_size = layout["font_size"]
    icon_size = layout["icon_size"]
    main_font = layout["main_font"]
    spacing = layout["spacing"]
    small_spacing = layout["small_spacing"]
    wind_icon_size = layout["wind_icon_size"]
    humidity_icon_size = layout["humidity_icon_size"]
    tide_spacing = layout["tide_spacing"]
    tide_icon_size = layout["tide_icon_size"]
    tide_time_font_size = layout["tide_time_font_size"] or max(int(primary_font_size * 0.6), 22)
    tide_time_font = layout["tide_time_font"] or _load_font(tide_time_font_size)
    tide_block_width = layout["tide_block_width"]
    tide_block_height = layout["tide_block_height"]
    tide_line_gap = layout["tide_line_gap"]
    weather_width = layout["weather_width"]
    row_height = layout["row_height"]

    footer_font_size = max(int(primary_font_size * 0.52), 18)
    footer_font = _load_font(footer_font_size)
    footer_offset = max(int(footer_font_size * 0.9), 22)

    condition_icon = _load_icon(payload["icon_name"], icon_size)
    icon_y = weather_top + max((row_height - icon_size) // 2, 0)
    image.paste(condition_icon, (inner_left, icon_y), condition_icon)

    cursor_x = inner_left + icon_size + spacing
    draw.text((cursor_x, weather_top), temp_text, font=main_font, fill=primary_color)
    temp_width, _ = _text_size(main_font, temp_text)
    cursor_x += temp_width + spacing

    wind_icon = _load_icon("wind.png", wind_icon_size)
    wind_icon_y = weather_top + max((row_height - wind_icon.size[1]) // 2, 0)
    image.paste(wind_icon, (int(cursor_x), int(wind_icon_y)), wind_icon)
    cursor_x += wind_icon.size[0] + small_spacing

    draw.text((cursor_x, weather_top), wind_text, font=main_font, fill=primary_color)
    wind_width, _ = _text_size(main_font, wind_text)
    cursor_x += wind_width + spacing

    humidity_icon = _load_icon("humidity.png", humidity_icon_size)
    humidity_icon_y = weather_top + max((row_height - humidity_icon.size[1]) // 2, 0)
    image.paste(humidity_icon, (int(cursor_x), int(humidity_icon_y)), humidity_icon)
    cursor_x += humidity_icon.size[0] + small_spacing

    draw.text((cursor_x, weather_top), humidity_text, font=main_font, fill=primary_color)
    weather_end_x = cursor_x + _text_size(main_font, humidity_text)[0]

    weather_row_bottom = weather_top + row_height

    if tide_icon_name:
        tide_icon = _load_icon(tide_icon_name, tide_icon_size)
        tide_start = max(weather_end_x + tide_spacing, width - padding - tide_block_width)
        icon_y = weather_top + max((row_height - tide_icon.size[1]) // 2, 0)
        image.paste(tide_icon, (int(tide_start), int(icon_y)), tide_icon)
        text_x = tide_start + tide_icon.size[0] + small_spacing
        draw.text((text_x, weather_top), tide_event_text, font=main_font, fill=primary_color)
        draw.text(
            (text_x, weather_top + primary_font_size + tide_line_gap),
            tide_time_text,
            font=tide_time_font,
            fill=primary_color,
        )
        tide_bottom = weather_top + tide_block_height
        weather_row_bottom = max(weather_row_bottom, tide_bottom)

    timestamp_y = weather_row_bottom + timestamp_spacing
    timestamp_font = _load_font(timestamp_font_size)
    updated_line = f"Updated: {payload['updated']}"
    if timestamp_y + timestamp_font_size > height - padding:
        timestamp_y = height - padding - timestamp_font_size
    draw.text((inner_left, timestamp_y), updated_line, font=timestamp_font, fill=primary_color)

    # Add credit line at the bottom with location and station ID (bright, bold, highly visible)
    location = payload.get("location_name", "")
    station_id = payload.get("station_id", "")
    
    # Build credit text with location and station info
    if location and station_id:
        credit_text = f"{location} (Station {station_id}) | Tempest Weather Network"
    elif station_id:
        credit_text = f"Station {station_id} | Tempest Weather Network"
    else:
        credit_text = "Data from Tempest Weather Network"
    
    # Make credit line bright, bold, and highly visible (same as forecast overlays)
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

    with _cache_lock:
        _image_cache[cache_key] = buffer.getvalue()

    buffer.seek(0)
    return buffer


def _select_icon_name(observation: Optional[TempestObservation]) -> str:
    if observation is None:
        return "unknown.png"

    precip_icon = PRECIP_ICON_MAP.get(observation.precipitation_type)
    if precip_icon:
        return precip_icon

    if _is_night(observation):
        return "night.png"

    if observation.wind_speed_ms and observation.wind_speed_ms > 8:
        return "wind.png"

    if observation.humidity and observation.humidity >= 95:
        return "mist.png"

    if observation.solar_radiation_wm2 and observation.solar_radiation_wm2 >= 600:
        return "clear.png"

    if observation.humidity and observation.humidity >= 75:
        return "clouds.png"

    return "clear.png"


def _load_icon(name: str, size: int) -> Image.Image:
    key = (name, size)
    with _cache_lock:
        cached = _icon_cache.get(key)
        if cached:
            return cached.copy()

    path = os.path.join(ICONS_DIR, name)
    if not os.path.isfile(path):
        path = os.path.join(ICONS_DIR, "unknown.png")

    try:
        image = Image.open(path).convert("RGBA")
    except (OSError, IOError):
        image = Image.new("RGBA", (size, size), (255, 255, 255, 0))

    if size > 0:
        image = image.resize((size, size), resample=RESAMPLING_FILTER)

    with _cache_lock:
        _icon_cache[key] = image

    return image.copy()


def _is_night(observation: TempestObservation) -> bool:
    local_time = observation.observed_at.astimezone()
    hour = local_time.hour
    is_night_hour = hour >= 20 or hour < 6

    low_light = False
    if observation.solar_radiation_wm2 is not None:
        low_light = observation.solar_radiation_wm2 < 50
    if observation.uv_index is not None:
        low_light = low_light or observation.uv_index < 0.2

    return is_night_hour and (low_light or observation.solar_radiation_wm2 is None)
