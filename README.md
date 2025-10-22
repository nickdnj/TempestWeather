# 🌤️ Tempest Weather Overlay API

**Beautiful, real-time weather overlays for live streaming** — powered by your Tempest Weather Station and NOAA tide data.

Transform your Tempest weather station data into stunning, broadcast-ready PNG overlays perfect for YouTube Live, Twitch, OBS, or any streaming platform. No complicated setup, no monthly fees — just clean, professional weather graphics that update in real-time.

[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Tempest](https://img.shields.io/badge/Tempest-Weather%20Station-00A3E0.svg)](https://tempestwx.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

### 🎯 Four Powerful Overlay Endpoints

1. **`/overlay/current`** — Current conditions with live sensor data
2. **`/overlay/5hour`** — Next 5 hours of hourly forecast  
3. **`/overlay/5day`** — 5-day forecast at a glance
4. **`/overlay/tides`** — Multi-station tide predictions (up to 4 stations)

### 🎨 Designed for Streaming

- **Transparent PNG overlays** — Layer perfectly over any video
- **Customizable dimensions** — Adapt to any stream layout (320x120 to 1920x600)
- **Dark/Light themes** — Match your stream aesthetic
- **Professional typography** — Clean, readable fonts optimized for video
- **High-contrast credit lines** — Proper attribution that's always visible
- **Smart caching** — Fast response times, low resource usage

### 🏖️ Perfect for Coastal Streams

- **Real-time local weather** — Direct from your Tempest station via UDP
- **NOAA tide integration** — Show multiple tide stations simultaneously
- **Location-aware** — Automatically displays your city and state
- **Wind speed & direction** — Essential for marine and outdoor streams
- **Accurate weather icons** — From Tempest's API, not guesswork

---

## 🚀 Quick Start

### Prerequisites

- **Tempest Weather Station** on your local network
- **Raspberry Pi or Linux server** (or Mac/Windows with Docker)
- **Tempest API Key** (free at [tempestwx.com/settings/tokens](https://tempestwx.com/settings/tokens))

### One-Command Deploy (Raspberry Pi)

```bash
# Clone the repository
git clone https://github.com/nickdnj/TempestWeather.git
cd TempestWeather

# Configure your credentials
cp config.example.env .env
nano .env  # Add your TEMPEST_API_KEY and TEMPEST_STATION_ID

# Deploy!
./deploy.sh
```

That's it! Your overlay service is now running at `http://YOUR_IP:8036`

### Docker Deployment (Any Platform)

```bash
docker build -t tempest-overlay .
docker run -d --name tempest-overlay \
  --restart unless-stopped \
  --network host \
  --env-file .env \
  tempest-overlay
```

---

## 📸 Example Overlays

### Current Conditions
```
http://your-ip:8036/overlay/current?width=1200&height=300
```
Shows: Temperature, Wind, Humidity, Weather Icon
Credit: "Monmouth Beach, NJ (Station 12345) | Tempest Weather Network | 2:30 PM"

### 5-Hour Forecast
```
http://your-ip:8036/overlay/5hour?width=1200&height=300
```
Shows: Next 5 hours with time, icon, temperature, and wind for each hour
Perfect for: Beach cams, outdoor events, marine streams

### 5-Day Forecast
```
http://your-ip:8036/overlay/5day?width=1200&height=300
```
Shows: 5-day outlook with day names, high/low temps, and weather icons
Perfect for: Morning streams, weekly planning content

### Multi-Station Tides
```
http://your-ip:8036/overlay/tides?width=1200&height=300&station=8531680&station=8531662&station=8531991&station=8531942
```
Shows: Up to 4 NOAA tide stations with next high/low tide times
Perfect for: Surf reports, fishing streams, coastal monitoring

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Required for forecast endpoints
TEMPEST_API_KEY=your_api_key_here
TEMPEST_STATION_ID=12345

# Optional: Add state to location display
TEMPEST_LOCATION_STATE=NJ

# Server port (default: 8036)
FLASK_PORT=8036

# Timezone (default: America/New_York)
TZ=America/New_York
```

### Query Parameters

All endpoints support:
- `width` — Width in pixels (default: 800, range: 320-1920)
- `height` — Height in pixels (default: 200, range: 120-600)
- `theme` — `dark` or `light` (default: dark)
- `units` — `imperial` or `metric` (default: imperial)

Tide endpoint also accepts:
- `station` — NOAA tide station ID (repeatable, up to 4)

---

## 🎥 Integration with OBS / Streaming Software

1. Add a **Browser Source** to your scene
2. Set URL to your overlay endpoint:
   ```
   http://your-raspberry-pi-ip:8036/overlay/current?width=1200&height=300
   ```
3. Set width/height to match your query parameters
4. Enable **Shutdown source when not visible** for better performance
5. Set refresh rate (e.g., 60 seconds for forecasts, 10 seconds for current conditions)

### Pro Tips

- Use `width=1200&height=300` for bottom-of-screen overlays
- Use `width=400&height=600` for side panel overlays  
- Dark theme for night streams, light theme for daytime
- Tides overlay works great as a rotating information panel

---

## 🏗️ Architecture

```
┌─────────────────────┐
│ Tempest Station     │ ← Your weather station
│ (UDP broadcasts)    │
└──────────┬──────────┘
           │ Local Network
           ↓
┌─────────────────────┐
│ Overlay API         │ ← This service
│ (Docker/Python)     │ → Tempest Cloud API (for forecasts)
│ Listens: UDP + HTTP │ → NOAA API (for tides)
└──────────┬──────────┘
           │ HTTP/PNG
           ↓
┌─────────────────────┐
│ Your Stream         │
│ OBS / FFmpeg / etc. │ → YouTube / Twitch
└─────────────────────┘
```

**Key Design Principles:**
- **Local-first** — Current conditions use UDP broadcasts (no internet required)
- **Lightweight** — Minimal dependencies, efficient caching
- **No database** — Everything in memory, stateless
- **Docker-friendly** — One-command deployment
- **Stream-optimized** — Fast PNG generation, transparent backgrounds

---

## 🛠️ Development

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python overlay/flask_overlay_server.py
```

Server will be available at `http://localhost:8080`

### Project Structure

```
TempestWeather/
├── overlay/
│   ├── flask_overlay_server.py    # Main Flask API
│   ├── overlay_forecast.py         # Forecast rendering
│   ├── tempest_overlay_image.py    # Image generation
│   ├── tempest_listener.py         # UDP listener for local data
│   └── tide_client.py              # NOAA tide data fetching
├── weather_icons/                  # Weather icon PNGs
├── fonts/                          # Typography (Arial.ttf)
├── Dockerfile                      # Docker build config
├── deploy.sh                       # One-command deployment
└── README.md                       # This file
```

---

## 🌊 Finding NOAA Tide Stations

Visit [NOAA Tides & Currents](https://tidesandcurrents.noaa.gov/map/index.html) to find station IDs near you:

1. Click on a tide station on the map
2. Copy the station ID (e.g., `8531680`)
3. Add to your overlay URL: `&station=8531680`

**Example stations (New Jersey coast):**
- `8531680` — Sandy Hook
- `8531991` — Long Branch Fishing Pier
- `8531942` — Long Branch Reach (Inside)
- `8531662` — Atlantic Highlands

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Complete deployment guide
- **[deploy.sh](deploy.sh)** — Automated deployment script
- **[config.example.env](config.example.env)** — Configuration template

---

## 🎬 About

This project was created by **Nick D.** in Monmouth Beach, NJ, for his coastal live streams featuring local weather and tide conditions. 

### The Development Story

Built entirely using **Cursor IDE** and **Claude AI (Sonnet 4.5)** in an iterative, conversational development process. What started as a simple weather overlay evolved into a full-featured streaming toolkit through continuous refinement and feature additions.

**Development Approach:**
- **AI-Assisted Development** — Every line of code written through natural language conversation with Claude
- **Rapid Iteration** — From concept to production in days, not weeks
- **Real-World Testing** — Developed and deployed on actual live streams
- **Community Focused** — Built to share with the Tempest Weather Station community

**Tech Stack:**
- **Backend:** Python 3.11, Flask
- **Image Generation:** Pillow (PIL)
- **Containerization:** Docker
- **Deployment:** Raspberry Pi 4
- **Data Sources:** Tempest API, NOAA Tides & Currents
- **Development:** Cursor IDE + Claude AI

### Why This Project?

Running a coastal live stream means your viewers want to know:
- **Current weather** — What's it like right now?
- **Hourly forecast** — What's coming in the next few hours?
- **Multi-day outlook** — Should I plan a beach day this week?
- **Tide times** — When's the next high tide for fishing/surfing?

This project provides all of that in beautiful, stream-ready overlays that update automatically.

---

## 🙏 Acknowledgments

- **WeatherFlow/Tempest** — For creating an amazing weather station with a developer-friendly API
- **NOAA** — For providing free, public tide prediction data
- **Anthropic/Claude** — For making AI-assisted development accessible and powerful
- **Cursor IDE** — For seamless integration of AI into the development workflow
- **The Tempest Community** — For inspiration and support

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

Feel free to use, modify, and share this project. If you create something cool with it, let me know!

---

## 🤝 Contributing

Contributions are welcome! Whether it's:
- 🐛 Bug fixes
- ✨ New features
- 📖 Documentation improvements
- 🎨 Icon designs
- 💡 Ideas and suggestions

Feel free to open an issue or submit a pull request.

---

## 💬 Community & Support

- **Tempest Community:** [community.weatherflow.com](https://community.weatherflow.com/)
- **GitHub Issues:** [Report bugs or request features](https://github.com/nickdnj/TempestWeather/issues)
- **Share Your Stream:** Using these overlays? I'd love to see them in action!

---

## 🌟 Star This Repo!

If you find this project useful, please give it a star ⭐ on GitHub. It helps others discover it too!

---

**Built with ☕, 🌊, and 🤖 in Monmouth Beach, NJ**
