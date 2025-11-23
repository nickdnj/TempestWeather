import os

from flask import Flask, Response, request, send_file

from tempest_listener import get_latest_observation
from overlay_forecast import (
    build_5day_forecast_payload,
    build_5hour_forecast_payload,
    build_current_conditions_payload,
    build_tides_payload,
    render_5day_forecast_overlay,
    render_5hour_forecast_overlay,
    render_current_conditions_overlay,
    build_current_conditions_expanded_payload,
    render_current_conditions_expanded_overlay,
    build_current_conditions_super_payload,
    render_current_conditions_super_overlay,
    render_tides_overlay,
)

app = Flask(__name__)

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 200
MIN_WIDTH, MAX_WIDTH = 320, 1920
MIN_HEIGHT, MAX_HEIGHT = 120, 600


def _parse_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


@app.route("/")
def index() -> Response:
    return Response(
        "Tempest Weather Overlay service.\n"
        "Available endpoints:\n"
        "  /overlay/current - Current conditions overlay\n"
        "  /overlay/current_expanded - Expanded current conditions overlay (more data)\n"
        "  /overlay/current_super - Super-expanded current conditions (all Tempest metrics)\n"
        "  /overlay/5hour - 5-hour forecast overlay\n"
        "  /overlay/5day - 5-day forecast overlay\n"
        "  /overlay/tides - Multi-station tide forecast (up to 4 stations)\n"
        "Query parameters: width, height, theme (dark/light), units (imperial/metric)\n"
        "  /overlay/tides accepts: station (repeatable, e.g., ?station=8531942&station=8534720)",
        mimetype="text/plain",
    )


@app.route("/overlay/5hour")
def overlay_5hour():
    """
    5-hour forecast overlay endpoint.
    Displays the next 5 hours of forecast with time, weather icon, temperature, and wind.
    Supports same query parameters as /overlay.png: width, height, theme, units.
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    
    payload = build_5hour_forecast_payload(units)
    image_stream = render_5hour_forecast_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/overlay/5day")
def overlay_5day():
    """
    5-day forecast overlay endpoint.
    Displays a 5-day forecast with day names, high/low temps, and weather icons.
    Supports same query parameters as /overlay.png: width, height, theme, units.
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    
    payload = build_5day_forecast_payload(units)
    image_stream = render_5day_forecast_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/overlay/current")
def overlay_current():
    """
    Current conditions overlay endpoint.
    Displays current conditions using Tempest API for accurate icon and location.
    Location name and weather icon are automatically fetched from the API.
    Supports query parameters: width, height, theme, units, location (optional override).
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    
    # Build payload from Tempest API (includes location and accurate icon)
    observation = get_latest_observation()  # Kept for potential fallback
    payload = build_current_conditions_payload(observation, units)
    
    # Optional location override via query parameter
    location = request.args.get("location", "").strip()
    if location:
        payload["location_name"] = location
    
    image_stream = render_current_conditions_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/overlay/current_expanded")
def overlay_current_expanded():
    """
    Expanded current conditions overlay endpoint.
    Displays current conditions with additional metrics (Feels Like, UV, Pressure, Rain).
    Uses a grid layout for better data density.
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    
    # Build payload from Tempest API
    observation = get_latest_observation()
    payload = build_current_conditions_expanded_payload(observation, units)
    
    # Optional location override via query parameter
    location = request.args.get("location", "").strip()
    if location:
        payload["location_name"] = location
    
    image_stream = render_current_conditions_expanded_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/overlay/current_super")
def overlay_current_super():
    """
    Super-expanded current conditions overlay endpoint.
    Displays ALL available Tempest metrics in a comprehensive 3x3 grid:
    Temperature, Wind, Wind Gust, Humidity, Feels Like, Dew Point,
    UV Index, Solar Radiation, Pressure, Rain Today, Lightning.
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    
    # Build payload from Tempest API
    observation = get_latest_observation()
    payload = build_current_conditions_super_payload(observation, units)
    
    # Optional location override via query parameter
    location = request.args.get("location", "").strip()
    if location:
        payload["location_name"] = location
    
    image_stream = render_current_conditions_super_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/overlay/tides")
def overlay_tides():
    """
    Multi-station tide forecast overlay endpoint.
    Displays up to 4 NOAA tide stations in columnar format.
    Each station shows: name, station ID, tide icon, tide type, and time.
    Accepts repeatable 'station' query parameter for NOAA station IDs.
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    
    # Get station IDs from query parameters (repeatable parameter)
    station_ids = request.args.getlist("station")
    
    # Build payload with tide data for all stations
    payload = build_tides_payload(station_ids)
    
    # Render the overlay
    image_stream = render_tides_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
