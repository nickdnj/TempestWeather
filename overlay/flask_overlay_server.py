import os

from flask import Flask, Response, request, send_file

from tempest_listener import get_latest_observation
from tempest_overlay_image import build_display_payload, render_overlay_image
from overlay_forecast import (
    build_daily_forecast_payload,
    build_5day_forecast_payload,
    render_daily_forecast_overlay,
    render_5day_forecast_overlay,
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
        "  /overlay.png - Current conditions overlay\n"
        "  /overlay/daily - Daily forecast overlay\n"
        "  /overlay/5day - 5-day forecast overlay\n"
        "Query parameters: width, height, theme (dark/light), units (imperial/metric)",
        mimetype="text/plain",
    )


@app.route("/overlay.png")
def overlay_png():
    width = _parse_int(
        request.args.get("width"), DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH
    )
    height = _parse_int(
        request.args.get("height"), DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT
    )
    theme = request.args.get("theme", "dark")
    units = request.args.get("units", "imperial")
    header_line_one = request.args.get("arg1", "").strip()
    header_line_two = request.args.get("arg2", "").strip()
    tide_station = request.args.get("tideStation") or request.args.get("tide_station")

    observation = get_latest_observation()
    payload = build_display_payload(
        observation,
        units,
        header_line_one,
        header_line_two,
        tide_station,
    )
    image_stream = render_overlay_image(payload, width, height, theme)

    response = send_file(image_stream, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/overlay/daily")
def overlay_daily():
    """
    Daily forecast overlay endpoint.
    Displays today's forecast with high/low temps, conditions, and precipitation probability.
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
    
    payload = build_daily_forecast_payload(units)
    image_stream = render_daily_forecast_overlay(payload, width, height, theme)
    
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


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
