# Architecture Overview - Tempest Weather Overlay System

## System Architecture (Updated)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Container                             │
│                   (Raspberry Pi / Mac)                          │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │         Flask Application (flask_overlay_server.py)       │ │
│  │                      Port 8080                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│          ┌────────────────┼────────────────┐                   │
│          │                │                │                   │
│          ▼                ▼                ▼                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │/overlay.png  │ │/overlay/daily│ │/overlay/5day │          │
│  │  (EXISTING)  │ │    (NEW)     │ │    (NEW)     │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│          │                │                │                   │
│          │                └────────────────┘                   │
│          │                         │                           │
│          ▼                         ▼                           │
│  ┌──────────────┐         ┌──────────────┐                   │
│  │tempest_      │         │overlay_      │                   │
│  │overlay_      │         │forecast.py   │                   │
│  │image.py      │         │   (NEW)      │                   │
│  │(UNCHANGED)   │         └──────────────┘                   │
│  └──────────────┘                 │                           │
│          │                         │                           │
│          │                         │                           │
│          ▼                         ▼                           │
│  ┌──────────────┐         ┌──────────────┐                   │
│  │tempest_      │         │Tempest Public│                   │
│  │listener.py   │         │API           │                   │
│  │(UNCHANGED)   │         │(better_      │                   │
│  └──────────────┘         │forecast)     │                   │
│          │                 └──────────────┘                   │
│          │                         │                           │
│          ▼                         ▼                           │
│  ┌──────────────┐         ┌──────────────┐                   │
│  │Local Tempest │         │Tempest Cloud │                   │
│  │UDP Broadcast │         │API Servers   │                   │
│  │(Port 50222)  │         │(HTTPS)       │                   │
│  └──────────────┘         └──────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │                         │
           │                         │
           ▼                         ▼
   ┌──────────────┐         ┌──────────────┐
   │ Local        │         │ Internet     │
   │ Network      │         │ Connection   │
   │ (Tempest     │         │              │
   │  Station)    │         │              │
   └──────────────┘         └──────────────┘
```

---

## Data Flow

### Current Conditions Overlay (Existing)

```
Tempest Station → UDP Broadcast → tempest_listener.py → 
    → tempest_overlay_image.py → PNG Image
    
Requirements:
- Local Tempest station on same network
- UDP port 50222 accessible
- Works on Raspberry Pi with local station
```

### Daily Forecast Overlay (New)

```
HTTP Request → flask_overlay_server.py → overlay_forecast.py →
    → Tempest Public API → JSON Response → overlay_forecast.py →
    → PNG Image

Requirements:
- TEMPEST_API_KEY environment variable
- TEMPEST_STATION_ID environment variable
- Internet connection
- Works anywhere (Mac, Pi, Cloud)
```

### 5-Day Forecast Overlay (New)

```
HTTP Request → flask_overlay_server.py → overlay_forecast.py →
    → Tempest Public API → JSON Response → overlay_forecast.py →
    → PNG Image

Requirements:
- TEMPEST_API_KEY environment variable
- TEMPEST_STATION_ID environment variable
- Internet connection
- Works anywhere (Mac, Pi, Cloud)
```

---

## Module Dependencies

```
flask_overlay_server.py
├── tempest_listener.py (existing)
│   └── (no external dependencies)
├── tempest_overlay_image.py (existing)
│   ├── PIL (Pillow)
│   ├── tempest_listener.py
│   └── tide_client.py
└── overlay_forecast.py (NEW)
    ├── requests (HTTP client)
    ├── PIL (Pillow)
    └── tempest_overlay_image.py (shared utilities only)
        ├── _load_font()
        ├── _text_size()
        ├── _load_icon()
        └── THEME_STYLES
```

---

## Endpoint Comparison

| Feature | /overlay.png | /overlay/daily | /overlay/5day |
|---------|-------------|----------------|---------------|
| **Status** | Existing | New | New |
| **Data Source** | Local UDP | Public API | Public API |
| **Internet Required** | No | Yes | Yes |
| **Shows** | Current conditions | Today's forecast | 5-day forecast |
| **Width** | 800px (default) | 800px (default) | 1200px (recommended) |
| **Height** | 200px (default) | 200px (default) | 300px (recommended) |
| **Themes** | Dark/Light | Dark/Light | Dark/Light |
| **Units** | Imperial/Metric | Imperial/Metric | Imperial/Metric |
| **Icons** | Weather icons | Weather icons | Weather icons |
| **Refresh Rate** | Real-time | API rate limit | API rate limit |

---

## File Organization

```
TempestWeather/
├── overlay/                          # Main application code
│   ├── flask_overlay_server.py       # Flask app (MODIFIED - added routes)
│   ├── tempest_listener.py           # UDP listener (UNCHANGED)
│   ├── tempest_overlay_image.py      # Current overlay renderer (UNCHANGED)
│   ├── tide_client.py                # Tide data (UNCHANGED)
│   └── overlay_forecast.py           # Forecast overlay renderer (NEW)
│
├── fonts/                            # Font files
│   └── Arial.ttf                     # Shared font
│
├── weather_icons/                    # Weather icon images
│   ├── clear.png                     # Used by all overlays
│   ├── clouds.png
│   ├── rain.png
│   └── ... (all other icons)
│
├── static/                           # Static assets
│   └── captured_images/
│
├── integration/                      # Integration configs
│
├── doc/                              # Original documentation
│
├── Dockerfile                        # Container definition (UNCHANGED)
├── docker-compose.yml                # Compose file
├── requirements.txt                  # Python deps (UNCHANGED - requests already there)
├── config.example.env                # Env vars (MODIFIED - added API vars)
│
├── README.md                         # Original readme
├── FORECAST_OVERLAY_IMPLEMENTATION.md  # Task spec (NEW)
├── FORECAST_OVERLAY_TESTING.md       # Testing guide (NEW)
├── QUICKSTART.md                     # Quick start (NEW)
├── IMPLEMENTATION_SUMMARY.md         # Summary (NEW)
├── ARCHITECTURE.md                   # This file (NEW)
└── test_endpoints.sh                 # Test script (NEW)
```

---

## Shared Resources

### Fonts
All three overlays use:
- `fonts/Arial.ttf` - Primary font
- Dynamic sizing based on available space
- Same loading and caching mechanism

### Icons
All three overlays use:
- Weather icons from `weather_icons/` directory
- Same icon loading utility `_load_icon()`
- Consistent sizing and positioning
- Icon mapping based on weather conditions

### Themes
All three overlays support:

**Dark Theme:**
- Background: `(18, 24, 38, 220)` - Dark blue with transparency
- Text: `(235, 240, 255, 255)` - Light gray/white

**Light Theme:**
- Background: `(246, 248, 252, 220)` - Light gray with transparency
- Text: `(24, 33, 54, 255)` - Dark blue/black

### Rendering Utilities
Shared functions from `tempest_overlay_image.py`:
- `_load_font(size)` - Load and cache fonts
- `_text_size(font, text)` - Measure text dimensions
- `_load_icon(name, size)` - Load and resize icons
- `THEME_STYLES` - Theme color definitions

---

## API Integration

### Tempest Public API

**Base URL:**
```
https://swd.weatherflow.com/swd/rest/better_forecast
```

**Authentication:**
```
token=YOUR_API_KEY
```

**Request Parameters:**
```python
{
    "station_id": "12345",
    "token": "your_api_key",
    "units_temp": "f",      # or "c"
    "units_wind": "mph",    # or "kph", "kts", "ms"
    "units_pressure": "inhg",  # or "mb", "mmhg"
    "units_precip": "in",   # or "mm"
    "units_distance": "mi"  # or "km"
}
```

**Response Structure:**
```json
{
  "status": {
    "status_code": 0,
    "status_message": "SUCCESS"
  },
  "current_conditions": { ... },
  "forecast": {
    "daily": [
      {
        "day_num": 20,
        "month_num": 10,
        "air_temp_high": 75,
        "air_temp_low": 58,
        "precip_probability": 10,
        "conditions": "Partly Cloudy",
        "icon": "partly-cloudy-day"
      }
      // ... more days
    ]
  }
}
```

**Rate Limiting:**
- Reasonable use policy
- Cache responses to avoid excessive calls
- Typical limit: ~100 requests per hour

---

## Environment Variables

### Required for Forecasts
```bash
TEMPEST_API_KEY=your_api_key_here
TEMPEST_STATION_ID=your_station_id_here
```

### Optional
```bash
FLASK_PORT=8080                    # Default: 8080
TEMPEST_UDP_PORT=50222            # Default: 50222
TEMPEST_UDP_BIND=0.0.0.0          # Default: all interfaces
```

---

## Performance Considerations

### Current Conditions Overlay
- **Latency:** < 50ms (in-memory data)
- **Updates:** Real-time via UDP
- **Caching:** Image cache based on data hash
- **Network:** Local only

### Forecast Overlays
- **Latency:** 200-500ms (API call + render)
- **Updates:** On-demand (each request)
- **Caching:** Could be added (not implemented yet)
- **Network:** Internet required

### Optimization Opportunities
1. **Cache forecast responses** (30-60 minutes)
2. **Cache rendered images** (similar to current overlay)
3. **Background refresh** (fetch before needed)
4. **Connection pooling** (reuse HTTP connections)

---

## Security Considerations

### API Key Protection
- ✅ Passed via environment variables (not in code)
- ✅ Not logged or exposed in responses
- ✅ Transmitted over HTTPS only
- ⚠️ Ensure `.env` file is in `.gitignore`

### Network Security
- ✅ API calls over HTTPS only
- ✅ No user input in API requests (station ID is config)
- ✅ No SQL or command injection vectors
- ✅ Image rendering is deterministic

### Container Security
- ✅ Non-root user in container (Python default)
- ✅ Minimal attack surface (Flask + Pillow only)
- ✅ No writable volumes needed
- ⚠️ Keep dependencies updated (Pillow security)

---

## Monitoring & Debugging

### Logging
```python
# API errors are printed to stdout
print(f"Error fetching forecast data: {e}")

# Flask logs all requests
# View with: docker logs <container_id>
```

### Health Checks
```bash
# Index page (should list all endpoints)
curl http://localhost:8080/

# Test each endpoint
curl -I http://localhost:8080/overlay.png
curl -I http://localhost:8080/overlay/daily
curl -I http://localhost:8080/overlay/5day
```

### Common Issues
1. **No forecast data:** Check API credentials
2. **Slow responses:** Check internet connection
3. **Error images:** Read error message in overlay
4. **Original overlay empty:** Check UDP broadcasts

---

## Scalability

### Current Setup
- Single container instance
- Handles multiple concurrent requests
- Flask development server (suitable for low traffic)

### Production Considerations
1. **Use production WSGI server** (gunicorn, uWSGI)
2. **Add response caching** (reduce API calls)
3. **Load balancer** (if high traffic)
4. **CDN for images** (if distributed globally)
5. **Health monitoring** (uptime checks)

### Example Production Setup
```bash
# Gunicorn with 4 workers
gunicorn -w 4 -b 0.0.0.0:8080 \
    overlay.flask_overlay_server:app
```

---

## Testing Strategy

### Unit Tests (Not Yet Implemented)
- Test forecast data parsing
- Test icon mapping
- Test unit conversions
- Test error handling

### Integration Tests (Manual)
- Run `test_endpoints.sh`
- Verify all endpoints respond
- Check image dimensions
- Verify themes work
- Test unit systems

### Visual Regression Tests (Manual)
- Compare styling across overlays
- Check font consistency
- Verify color accuracy
- Test different sizes

---

## Future Enhancements

### Potential Additions
1. **Hourly forecast overlay** (`/overlay/hourly`)
2. **Response caching** (reduce API calls)
3. **Custom layouts** (query param for layout style)
4. **Alert overlays** (severe weather warnings)
5. **Historical data** (charts/graphs)
6. **Multiple locations** (compare cities)

### Backward Compatibility
- All enhancements must preserve existing endpoints
- No breaking changes to query parameters
- Maintain consistent styling
- Keep modular architecture

---

**End of Architecture Overview**

