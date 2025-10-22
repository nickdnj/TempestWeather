# Tempest Weather Overlay API

Local-first image generator that turns a Tempest weather station broadcast into a PNG overlay suitable for live streaming. The service is intentionally lightweight—no external API keys, databases, or authentication—and is designed to run as a sidecar next to the Vistter streaming pipeline.

## Architecture
- **Tempest Weather Station** broadcasts UDP packets (`obs_st`) on the local network.
- **Overlay Service** listens for the packets, keeps the latest observation in memory, and renders a PNG overlay on demand.
- **Vistter Stream / FFmpeg** requests the PNG (`/overlay.png`) and composites it onto the camera feed before pushing to YouTube or other RTMP endpoints.

```
[Tempest Station] --(UDP obs_st)--> [Tempest Overlay API] --(PNG over HTTP)--> [FFmpeg/Vistter Stream] --(RTMP)--> Platform
```

## Running the Overlay Service

### Python (local development)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python overlay/flask_overlay_server.py
```
By default the server listens on `0.0.0.0:8080`.

### Docker
```
docker build -t tempest-overlay .
docker run --network host --restart unless-stopped --name tempest-overlay tempest-overlay
```
The container exposes port `8080` (configurable with `FLASK_PORT`) and requires access to the Tempest UDP broadcast, so host networking is recommended.

### Docker Compose (recommended for continuous operation)
```
docker compose up -d
```
This uses `docker-compose.yml` to build the image, run it with host networking, and restart automatically after failures or reboots.

## API

### Current Conditions Overlay (Original)

```
GET /overlay.png
```

**Optional query parameters**

| Parameter | Default | Description                                    |
|-----------|---------|------------------------------------------------|
| `width`   | 800     | Output width in pixels (320–1920)              |
| `height`  | 200     | Output height in pixels (120–600)              |
| `theme`   | dark    | `dark` or `light` background                   |
| `units`   | imperial| Display units (`imperial` or `metric`)         |
| `arg1`    | —       | Optional heading line displayed above the data |
| `arg2`    | —       | Second optional heading line (e.g., location)  |
| `tideStation` | —   | NOAA tide-station ID for next high/low tide    |

**Response**
- `Content-Type: image/png`
- Transparent PNG containing temperature, humidity, wind speed/direction, timestamp, and (if `tideStation` is supplied) the next tide event/time. `arg1`/`arg2` render as heading lines above the data row.
- Condition icons are sourced from `weather_icons/` based on Tempest precipitation, wind, solar, and humidity readings; nighttime packets fall back to `night.png`. Drop in your own PNGs to customize the look.

**Environment variables**
- `FLASK_PORT` (default `8080`) — HTTP port exposed by the overlay container/service.
- `TEMPEST_UDP_BIND` (default listen on all interfaces) — bind address for the UDP listener.
- `TEMPEST_UDP_PORT` (default `50222`) — Tempest UDP broadcast port.

Example:
```
http://localhost:8080/overlay.png?width=960&height=220&theme=light&units=metric
http://localhost:8080/overlay.png?arg1=Monmouth+Beach&arg2=Shrewsbury+River&tideStation=8531942
```

---

### Forecast Overlays (New)

Three additional endpoints provide forecast data using the Tempest public API:

```
GET /overlay/daily   — Today's forecast (high/low, conditions, precipitation)
GET /overlay/5hour   — 5-hour forecast with time, temp, wind, and icons (includes credit line)
GET /overlay/5day    — 5-day forecast with icons and temperatures
```

**Common query parameters**
| Parameter | Default | Description                                    |
|-----------|---------|------------------------------------------------|
| `width`   | 800     | Output width in pixels (320–1920)              |
| `height`  | 200     | Output height in pixels (120–600)              |
| `theme`   | dark    | `dark` or `light` background                   |
| `units`   | imperial| Display units (`imperial` or `metric`)         |

**Additional environment variables (required for forecasts)**
- `TEMPEST_API_KEY` — Your Tempest API token (get from https://tempestwx.com/settings/tokens)
- `TEMPEST_STATION_ID` — Your Tempest station ID

**Response**
- `Content-Type: image/png`
- Transparent PNG with forecast data matching the style of the current conditions overlay

**Examples:**
```
http://localhost:8080/overlay/daily?width=800&height=200&theme=dark&units=imperial
http://localhost:8080/overlay/5hour?width=1200&height=300&theme=dark&units=imperial
http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark&units=imperial
```

**Key differences from `/overlay.png`:**
- Forecast endpoints require internet access and Tempest API credentials
- Forecast data comes from Tempest's cloud API (not local UDP broadcasts)
- Works anywhere (doesn't require local Tempest station)
- Recommended size for 5-day: 1200x300 (wider for all 5 days)

**Documentation:**
- Quick start: See `QUICKSTART.md`
- Full implementation details: See `FORECAST_OVERLAY_IMPLEMENTATION.md`
- Testing guide: See `FORECAST_OVERLAY_TESTING.md`
- Architecture: See `ARCHITECTURE.md`

## Integration with Vistter Stream
- `stream_with_overlay.py` (root, `integration/`, and `vistter/`) defaults to `http://tempest-overlay:8080/overlay.png`.
- Update `OVERLAY_URL` in your `.env` if the service runs elsewhere.
- Ensure the Vistter service and overlay container share a network so FFmpeg can fetch the PNG.

## Development Notes
- The overlay renderer caches PNG outputs per `(width, height, theme, observation)` to avoid redundant render work.
- The Tempest listener runs as a background thread and keeps only the latest observation—no files on disk.
- Fonts live in `fonts/` (`Arial.ttf`). If the font cannot be loaded the service falls back to Pillow's default bitmap font.

## Related Assets
- `integration/` — scripts and unit files for deploying the FFmpeg pipeline.
- `vistter/` — legacy wrapper and documentation for the Vistter streaming project.

For details on the streaming pipeline itself, see `integration/README.md` and `integration/PRODUCT_REQUIREMENTS_SPEC.md`.
