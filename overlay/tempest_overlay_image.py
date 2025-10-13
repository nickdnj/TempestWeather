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
) -> Dict[str, str]:
    units = "metric" if units.lower() == "metric" else "imperial"

    icon_name = _select_icon_name(observation)

    if observation is None:
        cache_key = ("waiting", units, icon_name, header_line_one, header_line_two)
        return {
            "icon_name": icon_name,
            "temperature": "--",
            "wind": "--",
            "humidity": "--",
            "updated": "Waiting for data…",
            "header1": header_line_one,
            "header2": header_line_two,
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

    updated_local = observation.observed_at.astimezone()
    updated = updated_local.strftime("%Y-%m-%d %H:%M %Z")

    cache_key = (
        observation.cache_token,
        units,
        icon_name,
        header_line_one,
        header_line_two,
    )

    return {
        "icon_name": icon_name,
        "temperature": temperature,
        "wind": wind,
        "humidity": humidity,
        "updated": updated,
        "header1": header_line_one,
        "header2": header_line_two,
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

    padding = max(int(height * 0.12), 16)
    primary_color = style["text"]

    header_line_one = payload.get("header1", "").strip()
    header_line_two = payload.get("header2", "").strip()
    header_lines = [line for line in (header_line_one, header_line_two) if line]

    icon_target_size = int(height * 0.6)
    icon = _load_icon(payload["icon_name"], icon_target_size)
    icon_width, icon_height = icon.size
    icon_x = padding * 2

    header_left = icon_x
    current_y = padding
    header_gap = max(int(height * 0.04), 8)
    available_header_width = width - header_left - padding

    for line in header_lines:
        size = max(int(height * 0.18), 20)
        font = _load_font(size)
        while size > 14 and _text_size(font, line)[0] > available_header_width:
            size -= 2
            font = _load_font(size)
        draw.text((header_left, current_y), line, font=font, fill=primary_color)
        current_y += size + header_gap

    if header_lines:
        current_y += header_gap

    inner_top = max(current_y, padding * 1.6)

    inner_left = icon_x + icon_width + padding

    temp_text = payload["temperature"]
    wind_text = payload["wind"]
    humidity_text = payload["humidity"]

    available_width = width - padding - inner_left
    primary_font_size = max(int(height * 0.32), 28)
    min_font_size = 18
    while primary_font_size > min_font_size:
        main_font = _load_font(primary_font_size)
        spacing = max(int(padding * 0.7), 16)
        small_spacing = max(int(primary_font_size * 0.15), 8)
        wind_icon_size = max(int(primary_font_size * 0.8), 18)
        humidity_icon_size = max(int(primary_font_size * 0.8), 18)

        temp_width, _ = _text_size(main_font, temp_text)
        wind_width, _ = _text_size(main_font, wind_text)
        humidity_width, _ = _text_size(main_font, humidity_text)

        total_primary_width = (
            temp_width
            + spacing
            + wind_icon_size
            + small_spacing
            + wind_width
            + spacing
            + humidity_icon_size
            + small_spacing
            + humidity_width
        )
        if total_primary_width <= available_width:
            break
        primary_font_size -= 2

    main_font = _load_font(primary_font_size)
    spacing = max(int(padding * 0.7), 16)
    small_spacing = max(int(primary_font_size * 0.15), 8)
    wind_icon_size = max(int(primary_font_size * 0.8), 18)
    humidity_icon_size = max(int(primary_font_size * 0.8), 18)
    footer_font_size = max(int(primary_font_size * 0.6), 14)
    footer_font = _load_font(footer_font_size)
    footer_offset = max(int(footer_font_size * 0.5), 10)

    icon_y = inner_top + max((primary_font_size - icon_height) // 2, 0)
    image.paste(icon, (int(icon_x), int(icon_y)), icon)

    draw.text((inner_left, inner_top), temp_text, font=main_font, fill=primary_color)
    temp_width, _ = _text_size(main_font, temp_text)
    cursor_x = inner_left + temp_width + spacing

    wind_icon = _load_icon("wind.png", wind_icon_size)
    wind_icon_y = inner_top + max((primary_font_size - wind_icon.size[1]) // 2, 0)
    image.paste(wind_icon, (int(cursor_x), int(wind_icon_y)), wind_icon)
    cursor_x += wind_icon.size[0] + small_spacing

    draw.text((cursor_x, inner_top), wind_text, font=main_font, fill=primary_color)
    wind_width, _ = _text_size(main_font, wind_text)
    cursor_x += wind_width + spacing

    humidity_icon = _load_icon("humidity.png", humidity_icon_size)
    humidity_icon_y = inner_top + max((primary_font_size - humidity_icon.size[1]) // 2, 0)
    image.paste(humidity_icon, (int(cursor_x), int(humidity_icon_y)), humidity_icon)
    cursor_x += humidity_icon.size[0] + small_spacing

    draw.text((cursor_x, inner_top), humidity_text, font=main_font, fill=primary_color)

    updated_line = f"Updated: {payload['updated']}"
    footer_y = inner_top + primary_font_size + footer_offset
    draw.text((inner_left, footer_y), updated_line, font=footer_font, fill=primary_color)

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
