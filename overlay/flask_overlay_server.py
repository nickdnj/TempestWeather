import os
from datetime import datetime, timezone

from flask import Flask, Response, request, send_file, jsonify
from flask_cors import CORS

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
    build_fishing_report_payload,
    render_fishing_report_overlay,
    fetch_forecast_data,
)

app = Flask(__name__)
# Enable CORS for API endpoints (useful for cross-container browser access)
CORS(app, resources={r"/api/*": {"origins": "*"}})

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
        "  /overlay/fishing - Fishing report for Shrewsbury River (tide, barometer, moon, water temp, solunar)\n"
        "  /api/data - JSON API endpoint for all weather, tide, and astronomy data (units: imperial/metric)\n"
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


@app.route("/overlay/fishing")
def overlay_fishing():
    """
    Fishing report overlay for Shrewsbury River.
    Displays: tide stage, barometric pressure, moon phase, water temp, and solunar times.
    Query parameters: width, height, theme (dark/light), units (imperial/metric)
    """
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    
    # Get latest Tempest observation for barometric pressure and wind
    observation = get_latest_observation()
    
    # Build payload with all fishing data
    payload = build_fishing_report_payload(observation, units)
    
    # Render the overlay
    image_stream = render_fishing_report_overlay(payload, width, height, theme)
    
    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/api/data")
def api_data():
    """
    Return all weather/environmental data as JSON for external APIs.
    
    Query parameters:
        units (optional): imperial (default) or metric
    
    Returns JSON with current conditions, fishing data, tides, and 5-day forecast.
    """
    units = request.args.get("units", "imperial")
    
    # Get latest observation for fishing report
    observation = get_latest_observation()
    
    # Initialize response structure with defaults
    response_data = {
        "current": {},
        "fishing": {},
        "tides": {"stations": []},
        "forecast_5day": {"days": []},
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    # 1. Get current conditions data
    try:
        expanded_payload = build_current_conditions_expanded_payload(observation, units)
        super_payload = build_current_conditions_super_payload(observation, units)
        
        response_data["current"] = {
            "temperature": expanded_payload.get("temperature", "--"),
            "feels_like": expanded_payload.get("feels_like", "--"),
            "humidity": expanded_payload.get("humidity", "--"),
            "wind": expanded_payload.get("wind", "--"),
            "wind_gust": super_payload.get("wind_gust", "--"),
            "conditions": expanded_payload.get("conditions", "--"),
            "pressure": expanded_payload.get("pressure", "--"),
            "uv_index": expanded_payload.get("uv", "--"),
            "rain_today": expanded_payload.get("rain_today", "--"),
            "location_name": expanded_payload.get("location_name", "Unknown")
        }
    except Exception:
        # Graceful fallback for current conditions
        response_data["current"] = {
            "temperature": "--",
            "feels_like": "--",
            "humidity": "--",
            "wind": "--",
            "wind_gust": "--",
            "conditions": "--",
            "pressure": "--",
            "uv_index": "--",
            "rain_today": "--",
            "location_name": "Unknown"
        }
    
    # 2. Get fishing data
    try:
        fishing_payload = build_fishing_report_payload(observation, units)
        
        response_data["fishing"] = {
            "tide_stage": fishing_payload.get("tide_stage", "--"),
            "next_tide_event": fishing_payload.get("tide_next_event", "--"),
            "next_tide_time": fishing_payload.get("tide_next_time", "--"),
            "tide_height": fishing_payload.get("tide_height", "--"),
            "moon_phase": fishing_payload.get("moon_phase", "--"),
            "moon_illumination": fishing_payload.get("moon_illumination", "--"),
            "water_temp": fishing_payload.get("water_temp", "--"),
            "pressure_trend": fishing_payload.get("pressure_trend", "--"),
            "solunar_major": fishing_payload.get("solunar_major", "--"),
            "solunar_minor": fishing_payload.get("solunar_minor", "--")
        }
    except Exception:
        # Graceful fallback for fishing data
        response_data["fishing"] = {
            "tide_stage": "--",
            "next_tide_event": "--",
            "next_tide_time": "--",
            "tide_height": "--",
            "moon_phase": "--",
            "moon_illumination": "--",
            "water_temp": "--",
            "pressure_trend": "--",
            "solunar_major": "--",
            "solunar_minor": "--"
        }
    
    # 3. Get tides data (using default fishing tide station)
    try:
        tide_station = os.getenv("FISHING_TIDE_STATION", "8531662")
        tides_payload = build_tides_payload([tide_station])
        
        if not tides_payload.get("error") and tides_payload.get("stations"):
            stations = []
            for station in tides_payload.get("stations", []):
                stations.append({
                    "name": station.get("station_name", "Unknown"),
                    "tide_type": station.get("tide_type", "--"),
                    "tide_time": station.get("tide_time", "--")
                })
            response_data["tides"]["stations"] = stations
    except Exception:
        # Graceful fallback - empty stations array
        pass
    
    # 4. Get 5-day forecast data
    try:
        forecast_data = fetch_forecast_data(units)
        forecast_payload = build_5day_forecast_payload(units)
        
        if not forecast_payload.get("error") and forecast_payload.get("days"):
            days = []
            daily_forecasts = forecast_data.get("forecast", {}).get("daily", []) if forecast_data else []
            
            for i, day in enumerate(forecast_payload.get("days", [])):
                # Extract date from forecast data
                date_str = "--"
                if i < len(daily_forecasts):
                    day_start = daily_forecasts[i].get("day_start_local")
                    if day_start:
                        day_dt = datetime.fromtimestamp(day_start, tz=timezone.utc)
                        date_str = day_dt.strftime("%Y-%m-%d")
                
                # Parse high/low from temp_text like "75/58°F"
                temp_text = day.get("temp_text", "--")
                high = "--"
                low = "--"
                if "/" in temp_text and "°" in temp_text:
                    parts = temp_text.split("/")
                    if len(parts) == 2:
                        high = parts[0].strip()
                        low = parts[1].split("°")[0].strip()
                
                days.append({
                    "date": date_str,
                    "high": high,
                    "low": low,
                    "conditions": day.get("conditions", "--")
                })
            response_data["forecast_5day"]["days"] = days
    except Exception:
        # Graceful fallback - empty days array
        pass
    
    return jsonify(response_data)


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
