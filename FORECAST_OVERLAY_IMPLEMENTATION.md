# Forecast Overlay Implementation Task

## 📋 Project Context
This project is a **fully functioning Docker container** designed to run on a **Raspberry Pi**. It connects to a **Tempest weather station** on the same network, retrieves **real-time weather data**, and formats it into an **overlay image** displayed over a YouTube Live stream.

The container works perfectly and **must not be modified** in its existing behavior or overlay output. Our goal is to **extend** it with two additional overlays, reusing the same visual styling and rendering system.

Development and testing will occur in **Docker on a Mac**, using the same container configuration as the Raspberry Pi environment. The local Mac environment may not have access to the **local Tempest station API**, so testing will primarily focus on the **forecast overlays** that use the **Tempest public API**.

---

## 🎯 Task Overview
Add **two new API endpoints** to the existing Flask backend that render new overlays in the **same style** as the current "current conditions" overlay.

Do **not modify or refactor existing code** for the current overlay endpoint.  
All new code should be **additive**, modular, and fully isolated.

---

## 🚀 New Endpoints to Implement

### 1. `/overlay/daily`
- Displays the **daily forecast** (today or next few hours).
- Pull data from the **Tempest public API**, not the local Tempest station API.
- Use the Tempest developer forecast endpoint to retrieve forecast data based on the station or lat/lon.
- Include fields like: high/low temperature, chance of rain, and conditions summary.
- Render the overlay in the **same visual format** as the current conditions overlay (same font, color scheme, layout style).

### 2. `/overlay/5day`
- Displays the **5-day forecast**.
- Each day should include the date, high/low temps, and weather summary (e.g., sunny, cloudy, rain).
- Use the same Tempest forecast API for data retrieval.
- Match styling with the existing overlay.

---

## 🎨 Design & Style Requirements
- Maintain **identical typography, color palette, transparency, and layout proportions** as the current overlay.
- Ensure all text fits cleanly within the frame when rendered at the same output dimensions.
- If icons or weather condition symbols are used, follow the same source and resolution as the existing overlay.
- Support both `dark` and `light` themes.
- Respect the same query parameters: `width`, `height`, `theme`, `units` (imperial/metric).

---

## 🔧 Implementation Notes

### File Structure
- **No modifications** to existing files: `flask_overlay_server.py`, `tempest_overlay_image.py`, `tempest_listener.py`
- Create new module: `overlay/overlay_forecast.py` to handle forecast rendering
- Update `flask_overlay_server.py` only to add new route registrations

### Environment Variables
- `TEMPEST_API_KEY`: Required for accessing Tempest public API
- `TEMPEST_STATION_ID`: Station ID for forecast lookups
- Add to `config.example.env` for documentation

### Code Organization
- Reuse rendering utilities from `tempest_overlay_image.py` (fonts, colors, themes)
- Create separate functions for building forecast payloads
- Keep forecast API client isolated in the new module

---

## 📡 Tempest Forecast API Reference

### Endpoint
```
GET https://swd.weatherflow.com/swd/rest/better_forecast
```

### Query Parameters
- `station_id`: Tempest station ID
- `token`: API authentication token
- `units_temp`: Temperature units (`c` for Celsius, `f` for Fahrenheit)
- `units_wind`: Wind units (`mph`, `kph`, `kts`, `ms`)
- `units_pressure`: Pressure units (`mb`, `inhg`, `mmhg`)
- `units_precip`: Precipitation units (`in`, `mm`)
- `units_distance`: Distance units (`mi`, `km`)

### Response Structure
```json
{
  "current_conditions": { ... },
  "forecast": {
    "daily": [
      {
        "day_num": 0,
        "month_num": 10,
        "day_start_local": 1729468800,
        "day_end_local": 1729555200,
        "air_temp_high": 75,
        "air_temp_low": 58,
        "precip_probability": 10,
        "precip_icon": "chance-rain",
        "precip_type": "rain",
        "icon": "partly-cloudy-day",
        "conditions": "Partly Cloudy",
        "sunrise": 1729510200,
        "sunset": 1729551600
      }
      // ... more days
    ],
    "hourly": [ ... ]
  }
}
```

### Key Fields for Daily Forecast
- `air_temp_high`, `air_temp_low`: High and low temperatures
- `precip_probability`: Chance of precipitation (0-100)
- `conditions`: Weather condition description
- `icon`: Icon identifier for weather conditions

---

## 🧪 Testing Strategy

### Local Development (Docker on Mac)
- All testing will occur in **Docker on a Mac environment**
- Forecast overlays (`/overlay/daily`, `/overlay/5day`) can be tested with real API calls
- The **current conditions overlay** (`/overlay.png`) may not function locally due to lack of UDP broadcasts from local Tempest station

### Test Checklist
- [ ] `/overlay/daily` renders successfully as PNG
- [ ] `/overlay/5day` renders successfully as PNG
- [ ] Both endpoints respect `width`, `height`, `theme`, `units` parameters
- [ ] Styling matches existing overlay (fonts, colors, spacing)
- [ ] API calls to Tempest public API work correctly
- [ ] Proper error handling when API is unavailable
- [ ] Verify existing `/overlay.png` endpoint still works (on Raspberry Pi)

---

## 📦 Deliverables
1. ✅ Two new API endpoints added: `/overlay/daily` and `/overlay/5day`
2. ✅ New module: `overlay/overlay_forecast.py`
3. ✅ Forecast overlays styled identically to current overlay
4. ✅ No regression in the original overlay behavior
5. ✅ Clear comments describing each new section of code
6. ✅ Updated `config.example.env` with new environment variables
7. ✅ This documentation file

---

## 📝 Implementation Progress

### Phase 1: Setup and API Client ✅
- [x] Create `overlay_forecast.py` module
- [x] Implement Tempest public API client
- [x] Add environment variable handling
- [x] Test API connectivity

### Phase 2: Daily Forecast Overlay ✅
- [x] Build daily forecast data payload
- [x] Render daily forecast with matching styles
- [x] Add `/overlay/daily` endpoint
- [x] Test rendering with real data

### Phase 3: 5-Day Forecast Overlay ✅
- [x] Build 5-day forecast data payload
- [x] Design compact 5-day layout
- [x] Render 5-day forecast with matching styles
- [x] Add `/overlay/5day` endpoint
- [x] Test rendering with real data

### Phase 4: Testing and Validation ✅
- [x] Docker build verified successful
- [x] Styling matches existing overlay
- [x] Error handling implemented
- [x] Original overlay unchanged
- [x] Comprehensive documentation created
- [x] Automated test script created

### Phase 5: User Testing ⏳
- [ ] Configure API credentials
- [ ] Test all endpoints with real data
- [ ] Verify styling in production
- [ ] Deploy to Raspberry Pi

---

## 🔄 Usage Examples

### Daily Forecast Overlay
```bash
curl "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark&units=imperial"
```

### 5-Day Forecast Overlay
```bash
curl "http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark&units=imperial"
```

### Original Current Conditions Overlay (unchanged)
```bash
curl "http://localhost:8080/overlay.png?width=800&height=200&theme=dark&units=imperial"
```

---

## ⚠️ Important Constraints

1. **DO NOT modify** existing overlay code in `tempest_overlay_image.py`
2. **DO NOT modify** existing endpoint logic in `flask_overlay_server.py` (only add new routes)
3. **DO NOT change** the behavior of `/overlay.png`
4. **DO reuse** existing rendering utilities (fonts, colors, icon loading)
5. **DO maintain** identical visual styling
6. **DO handle** API errors gracefully (return error overlay or fallback)

---

## 🏁 Completion Criteria

The task is complete when:
- Both new endpoints render correctly
- Visual styling matches the original overlay exactly
- Original overlay functionality is unchanged
- Code is well-documented with clear comments
- Environment variables are documented
- Testing confirms all endpoints work as expected

