# Forecast Overlay Testing Guide

## 🧪 Testing the New Forecast Overlays

This guide helps you test the newly implemented forecast overlay endpoints.

---

## Prerequisites

1. **Tempest API Credentials**
   - Get your API key from: https://tempestwx.com/settings/tokens
   - Find your station ID in your Tempest account

2. **Environment Variables**
   Create a `.env` file with:
   ```bash
   TEMPEST_API_KEY=your_api_key_here
   TEMPEST_STATION_ID=your_station_id_here
   FLASK_PORT=8080
   ```

---

## 🐳 Building and Running the Docker Container

### Build the Container
```bash
docker build -t tempest-overlay .
```

### Run the Container
```bash
docker run -p 8080:8080 \
  -e TEMPEST_API_KEY=your_api_key_here \
  -e TEMPEST_STATION_ID=your_station_id_here \
  tempest-overlay
```

Or with a `.env` file:
```bash
docker run -p 8080:8080 --env-file .env tempest-overlay
```

---

## 🧪 Testing the Endpoints

### 1. Check Server Status
```bash
curl http://localhost:8080/
```

Expected output:
```
Tempest Weather Overlay service.
Available endpoints:
  /overlay.png - Current conditions overlay
  /overlay/daily - Daily forecast overlay
  /overlay/5day - 5-day forecast overlay
Query parameters: width, height, theme (dark/light), units (imperial/metric)
```

### 2. Test Daily Forecast Overlay
```bash
# Dark theme, imperial units
curl -o daily_dark.png "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark&units=imperial"

# Light theme, metric units
curl -o daily_light.png "http://localhost:8080/overlay/daily?width=800&height=200&theme=light&units=metric"

# Open the image (Mac)
open daily_dark.png
```

### 3. Test 5-Day Forecast Overlay
```bash
# Dark theme, imperial units (wider for 5 days)
curl -o 5day_dark.png "http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark&units=imperial"

# Light theme, metric units
curl -o 5day_light.png "http://localhost:8080/overlay/5day?width=1200&height=300&theme=light&units=metric"

# Open the image (Mac)
open 5day_dark.png
```

### 4. Test Original Current Conditions Overlay
```bash
# This endpoint requires UDP broadcasts from a local Tempest station
# It may not work on Mac unless you have a local station
curl -o current.png "http://localhost:8080/overlay.png?width=800&height=200&theme=dark&units=imperial"
```

---

## 🎨 Testing Different Configurations

### Different Sizes
```bash
# Small overlay
curl -o daily_small.png "http://localhost:8080/overlay/daily?width=400&height=150"

# Large overlay
curl -o daily_large.png "http://localhost:8080/overlay/daily?width=1600&height=400"
```

### Both Themes
```bash
# Dark theme
curl -o daily_dark.png "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark"

# Light theme
curl -o daily_light.png "http://localhost:8080/overlay/daily?width=800&height=200&theme=light"
```

### Different Units
```bash
# Imperial (Fahrenheit, mph)
curl -o daily_imperial.png "http://localhost:8080/overlay/daily?units=imperial"

# Metric (Celsius, km/h)
curl -o daily_metric.png "http://localhost:8080/overlay/daily?units=metric"
```

---

## 🔍 Visual Verification Checklist

### Daily Forecast Overlay
- [ ] Title reads "Today's Forecast"
- [ ] Weather icon displays correctly
- [ ] Temperature range shows high/low (e.g., "75°F / 58°F")
- [ ] Conditions text is readable (e.g., "Partly Cloudy")
- [ ] Precipitation probability shows (e.g., "Rain: 10%")
- [ ] Dark theme: dark background, light text
- [ ] Light theme: light background, dark text
- [ ] Font and spacing match current conditions overlay

### 5-Day Forecast Overlay
- [ ] Title reads "5-Day Forecast"
- [ ] Five day columns display
- [ ] First day says "Today", second says "Tomorrow"
- [ ] Days 3-5 show abbreviated day names (Mon, Tue, etc.)
- [ ] Each day has weather icon
- [ ] Each day shows high/low temps (e.g., "75/58°F")
- [ ] Icons and text are centered in each column
- [ ] Dark/light themes work correctly
- [ ] Layout is balanced and readable

---

## 🐛 Troubleshooting

### Error: "Unable to fetch forecast data"
**Problem:** Cannot connect to Tempest API

**Solutions:**
1. Verify `TEMPEST_API_KEY` is set correctly
2. Verify `TEMPEST_STATION_ID` is set correctly
3. Check internet connectivity from container
4. Verify API key is valid at https://tempestwx.com/settings/tokens

### Error: "No forecast data available"
**Problem:** API returned empty data

**Solutions:**
1. Verify station ID is correct
2. Check if station is active and reporting
3. Check Tempest API status

### Image Shows Error Message
**Expected:** Error overlays should display clearly with error message

**Check:**
- Read the error message in the overlay
- Check Docker logs: `docker logs <container_id>`
- Verify environment variables are passed to container

### Original `/overlay.png` Not Working on Mac
**Expected:** This is normal - requires local UDP broadcasts from Tempest station

**Note:** The current conditions overlay works on Raspberry Pi with local station, but forecast overlays work anywhere with internet access.

---

## 📊 Comparison Test

To verify styling consistency between original and new overlays:

1. Generate all three overlays:
```bash
# If on Raspberry Pi with local station:
curl -o current.png "http://localhost:8080/overlay.png?width=800&height=200&theme=dark"

curl -o daily.png "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark"
curl -o 5day.png "http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark"
```

2. Compare visually:
- Font family should match
- Font sizes should be proportional
- Colors should match (dark: light text on dark bg, light: dark text on light bg)
- Icon sizes should be similar
- Spacing and padding should feel consistent

---

## ✅ Final Verification

Before deploying to Raspberry Pi:

- [ ] All three endpoints respond successfully
- [ ] Daily forecast shows correct data
- [ ] 5-day forecast shows correct data
- [ ] Both themes work for new overlays
- [ ] Both imperial and metric units work
- [ ] Styling matches original overlay
- [ ] Images are transparent PNG format
- [ ] No errors in Docker logs
- [ ] API credentials are working

---

## 🚀 Deployment to Raspberry Pi

Once testing is complete on Mac:

1. **Build and push to Raspberry Pi:**
```bash
# On Mac, build for ARM architecture
docker buildx build --platform linux/arm64 -t tempest-overlay .

# Or build directly on Raspberry Pi
ssh pi@your-pi-address
cd /path/to/TempestWeather
docker build -t tempest-overlay .
```

2. **Update docker-compose.yml or run command:**
```bash
docker run -d \
  --name tempest-overlay \
  --restart unless-stopped \
  -p 8080:8080 \
  -e TEMPEST_API_KEY=your_api_key \
  -e TEMPEST_STATION_ID=your_station_id \
  tempest-overlay
```

3. **Test all three endpoints on Raspberry Pi:**
```bash
# Current conditions (should work with local station)
curl -o test_current.png "http://localhost:8080/overlay.png"

# Daily forecast
curl -o test_daily.png "http://localhost:8080/overlay/daily"

# 5-day forecast
curl -o test_5day.png "http://localhost:8080/overlay/5day"
```

---

## 📝 Success Criteria

✅ **Task is complete when:**
1. Both new endpoints render successfully
2. Forecast data is accurate and current
3. Visual styling matches original overlay
4. Original `/overlay.png` endpoint unchanged
5. Both themes (dark/light) work
6. Both unit systems (imperial/metric) work
7. Container runs successfully on both Mac and Raspberry Pi
8. All overlays display correctly in streaming pipeline

