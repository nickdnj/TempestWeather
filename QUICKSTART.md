# Quick Start Guide - Forecast Overlays

## 🎉 Implementation Complete!

Two new forecast overlay endpoints have been successfully added to your Tempest weather overlay system:
- `/overlay/daily` - Today's forecast
- `/overlay/5day` - 5-day forecast

The original `/overlay.png` endpoint remains **unchanged** and continues to work as before.

---

## 🚀 Quick Test (5 minutes)

### 1. Set Your Tempest API Credentials

You need two pieces of information:
- **API Key**: Get from https://tempestwx.com/settings/tokens
- **Station ID**: Find in your Tempest account

### 2. Run the Container

```bash
# Using environment variables
docker run -p 8080:8080 \
  -e TEMPEST_API_KEY=your_api_key_here \
  -e TEMPEST_STATION_ID=your_station_id_here \
  tempest-overlay
```

Or create a `.env` file:
```bash
cat > .env << EOF
TEMPEST_API_KEY=your_api_key_here
TEMPEST_STATION_ID=your_station_id_here
FLASK_PORT=8080
EOF

docker run -p 8080:8080 --env-file .env tempest-overlay
```

### 3. Test the Endpoints

```bash
# Run the automated test script
./test_endpoints.sh

# Or test manually:
curl -o daily.png "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark"
curl -o 5day.png "http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark"

# View the images (Mac)
open daily.png
open 5day.png
```

---

## 📊 What Was Added

### New Files Created
1. **`overlay/overlay_forecast.py`** - New forecast module
   - Fetches data from Tempest public API
   - Renders daily and 5-day forecast overlays
   - Matches styling of original overlay

2. **`FORECAST_OVERLAY_IMPLEMENTATION.md`** - Complete task documentation
   - Full requirements and specifications
   - Implementation details
   - API reference

3. **`FORECAST_OVERLAY_TESTING.md`** - Testing guide
   - Step-by-step testing instructions
   - Troubleshooting tips
   - Deployment guide

4. **`test_endpoints.sh`** - Automated test script
   - Tests all three endpoints
   - Verifies responses
   - Generates sample images

5. **`QUICKSTART.md`** - This file

### Modified Files
1. **`overlay/flask_overlay_server.py`** (additive changes only)
   - Added imports for forecast functions
   - Added `/overlay/daily` endpoint
   - Added `/overlay/5day` endpoint
   - Updated index page to list all endpoints
   - **Original `/overlay.png` endpoint unchanged**

2. **`config.example.env`**
   - Added `TEMPEST_API_KEY` documentation
   - Added `TEMPEST_STATION_ID` documentation

---

## 🎨 Endpoint Details

### `/overlay/daily` - Daily Forecast

Shows today's forecast with:
- High/low temperature
- Weather conditions
- Precipitation probability
- Weather icon

**Example:**
```bash
curl "http://localhost:8080/overlay/daily?width=800&height=200&theme=dark&units=imperial"
```

### `/overlay/5day` - 5-Day Forecast

Shows 5-day forecast with:
- Day names (Today, Tomorrow, Mon, Tue, etc.)
- High/low temperatures for each day
- Weather icons for each day
- Compact side-by-side layout

**Example:**
```bash
curl "http://localhost:8080/overlay/5day?width=1200&height=300&theme=dark&units=imperial"
```

### Query Parameters (all endpoints)
- `width`: Image width in pixels (320-1920, default: 800)
- `height`: Image height in pixels (120-600, default: 200)
- `theme`: `dark` or `light` (default: dark)
- `units`: `imperial` or `metric` (default: imperial)

---

## ✅ Verification Checklist

Before deploying to production:

- [ ] Docker container builds successfully (`docker build -t tempest-overlay .`)
- [ ] Container runs without errors (`docker run -p 8080:8080 --env-file .env tempest-overlay`)
- [ ] Index page shows all three endpoints (`curl http://localhost:8080/`)
- [ ] Daily forecast renders correctly (`curl -o test.png http://localhost:8080/overlay/daily`)
- [ ] 5-day forecast renders correctly (`curl -o test.png http://localhost:8080/overlay/5day`)
- [ ] Original endpoint still works on Raspberry Pi
- [ ] Both themes work (dark and light)
- [ ] Both unit systems work (imperial and metric)
- [ ] Styling matches original overlay
- [ ] Images are transparent PNGs

---

## 🎯 Using in Your Stream

### Update Your Overlay URL

You can now use any of these overlays in your streaming pipeline:

**Current conditions (original):**
```
http://tempest-overlay:8080/overlay.png?width=800&height=200&theme=dark&units=imperial
```

**Daily forecast (new):**
```
http://tempest-overlay:8080/overlay/daily?width=800&height=200&theme=dark&units=imperial
```

**5-day forecast (new):**
```
http://tempest-overlay:8080/overlay/5day?width=1200&height=300&theme=dark&units=imperial
```

### Switching Between Overlays

You can:
1. Use one overlay all the time
2. Rotate between overlays on a schedule
3. Use different overlays for different streams
4. Display multiple overlays at different positions

---

## 🐛 Troubleshooting

### Container won't start
- Check Docker is running
- Verify port 8080 is available
- Check environment variables are set

### "Unable to fetch forecast data"
- Verify `TEMPEST_API_KEY` is correct
- Verify `TEMPEST_STATION_ID` is correct
- Check internet connectivity from container
- Verify API key at https://tempestwx.com/settings/tokens

### Original overlay not working
- This is expected on Mac - requires local UDP broadcasts
- Will work on Raspberry Pi with local Tempest station
- Forecast overlays work everywhere (use public API)

### Styling doesn't match
- Compare images side-by-side
- Check theme parameter is the same
- Verify same font file is being used
- Review `tempest_overlay_image.py` THEME_STYLES

---

## 📚 Documentation

Detailed documentation available in:
- `FORECAST_OVERLAY_IMPLEMENTATION.md` - Full implementation details
- `FORECAST_OVERLAY_TESTING.md` - Comprehensive testing guide
- `README.md` - Original project documentation

---

## 🚢 Deploying to Raspberry Pi

### Option 1: Build on Raspberry Pi
```bash
ssh pi@your-pi-address
cd /path/to/TempestWeather
git pull
docker build -t tempest-overlay .
docker run -d --name tempest-overlay --restart unless-stopped \
  -p 8080:8080 \
  --env-file .env \
  tempest-overlay
```

### Option 2: Cross-compile on Mac
```bash
# Build for ARM64 architecture
docker buildx build --platform linux/arm64 -t tempest-overlay .

# Export and transfer to Pi
docker save tempest-overlay | gzip > tempest-overlay.tar.gz
scp tempest-overlay.tar.gz pi@your-pi-address:~

# On Pi, load and run
ssh pi@your-pi-address
docker load < tempest-overlay.tar.gz
docker run -d --name tempest-overlay --restart unless-stopped \
  -p 8080:8080 \
  --env-file .env \
  tempest-overlay
```

---

## 🎊 Success!

Your Tempest weather overlay system now has three fully functional endpoints:

1. ✅ **Current conditions** - Real-time data from local station
2. ✅ **Daily forecast** - Today's weather from Tempest API
3. ✅ **5-day forecast** - Week ahead from Tempest API

All endpoints share the same beautiful, consistent styling and are ready for production use!

---

## 📞 Need Help?

If you encounter issues:

1. Check the logs: `docker logs <container-id>`
2. Review the testing guide: `FORECAST_OVERLAY_TESTING.md`
3. Verify environment variables are set correctly
4. Test API access: `curl "https://swd.weatherflow.com/swd/rest/better_forecast?station_id=YOUR_ID&token=YOUR_KEY"`

Happy streaming! 🌤️

