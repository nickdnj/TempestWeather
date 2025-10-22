# 🚀 Deployment Guide

## Quick Deploy (Raspberry Pi)

To deploy updates to your Raspberry Pi, simply run:

```bash
./deploy.sh
```

That's it! The script will:
1. ✅ Pull latest changes from GitHub
2. ✅ Stop and remove old container
3. ✅ Build new Docker image
4. ✅ Start new container with proper settings
5. ✅ Show status and logs

---

## First-Time Setup

### 1. Clone the Repository

```bash
cd ~
git clone https://github.com/nickdnj/TempestWeather.git
cd TempestWeather
```

### 2. Create `.env` File

```bash
cp config.example.env .env
nano .env
```

Set these required values:
```bash
TEMPEST_API_KEY=your_actual_api_key_here
TEMPEST_STATION_ID=your_actual_station_id_here
FLASK_PORT=8036
```

### 3. Run First Deployment

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Manual Deployment Steps

If you prefer to run commands manually:

```bash
# 1. Pull updates
git pull origin main

# 2. Stop and remove old container
docker stop tempest-overlay
docker rm tempest-overlay

# 3. Build new image
docker build -t tempest-overlay .

# 4. Run new container
docker run -d \
  --name tempest-overlay \
  --restart unless-stopped \
  --network host \
  --env-file .env \
  tempest-overlay
```

---

## Important Notes

### Why `--network host`?

The container needs `--network host` to:
- Access Tempest UDP broadcasts on port 50222 (local station data)
- Serve on the configured port (default 8036)

Without `--network host`, the `/overlay.png` and `/overlay/current` endpoints won't receive real-time data from your local Tempest station.

### Port Configuration

The service runs on port `8036` by default (set in `.env` as `FLASK_PORT`).

Access endpoints at:
- `http://raspberry-pi-ip:8036/overlay/current`
- `http://raspberry-pi-ip:8036/overlay/daily`
- etc.

---

## Available Endpoints

Once deployed, you have 5 endpoints:

| Endpoint | Description | Data Source |
|----------|-------------|-------------|
| `/overlay.png` | Original overlay (headers + tide) | Local UDP |
| `/overlay/current` | Current conditions (simple) | Local UDP |
| `/overlay/daily` | Daily forecast | Tempest API |
| `/overlay/5day` | 5-day forecast | Tempest API |
| `/overlay/5hour` | 5-hour forecast | Tempest API |

### Query Parameters

All endpoints support:
- `width` - Image width (default: 800)
- `height` - Image height (default: 200)
- `theme` - `dark` or `light` (default: dark)
- `units` - `imperial` or `metric` (default: imperial)

Example:
```
http://your-pi:8036/overlay/current?width=1200&height=300&theme=dark&units=imperial&location=Monmouth+Beach
```

---

## Useful Commands

### View Logs
```bash
docker logs tempest-overlay
```

### Follow Logs (Real-time)
```bash
docker logs -f tempest-overlay
```

### Restart Container
```bash
docker restart tempest-overlay
```

### Stop Container
```bash
docker stop tempest-overlay
```

### Check Container Status
```bash
docker ps | grep tempest-overlay
```

### Remove Container
```bash
docker stop tempest-overlay
docker rm tempest-overlay
```

---

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker logs tempest-overlay
```

Common issues:
1. Missing `.env` file
2. Invalid API key or station ID
3. Port already in use

### No Data on `/overlay/current` or `/overlay.png`

Make sure you're using `--network host`:
```bash
docker inspect tempest-overlay | grep NetworkMode
# Should show: "NetworkMode": "host"
```

The container needs access to UDP port 50222 for local Tempest broadcasts.

### Forecast Endpoints Not Working

Check your API credentials:
```bash
grep TEMPEST_API_KEY .env
grep TEMPEST_STATION_ID .env
```

Test the API manually:
```bash
curl "https://swd.weatherflow.com/swd/rest/better_forecast?station_id=YOUR_STATION_ID&token=YOUR_API_KEY"
```

---

## Updating in the Future

Whenever there are updates:

```bash
cd ~/TempestWeather
./deploy.sh
```

The script handles everything automatically! 🎉

---

## Network Configuration

### For YouTube Live Streaming

If you're using these overlays in OBS for YouTube Live:

1. Add a Browser Source in OBS
2. Set URL to: `http://your-raspberry-pi-ip:8036/overlay/current?width=1200&height=300`
3. Set width/height to match your query parameters
4. Refresh Browser when stream starts

### Multiple Overlays

You can use different endpoints for different scenes:
- Scene 1: Current conditions (`/overlay/current`)
- Scene 2: 5-day forecast (`/overlay/5day`)
- Scene 3: Hourly forecast (`/overlay/5hour`)
- Scene 4: Original with tide (`/overlay.png?tideStation=8531942`)

---

## Performance

The container is lightweight and runs great on Raspberry Pi:
- Memory usage: ~100-150MB
- CPU usage: Minimal (only when generating overlays)
- Startup time: ~3-5 seconds
- Response time: <100ms per overlay

---

## Security Notes

- The service binds to `0.0.0.0` (all interfaces)
- Consider using a firewall if exposed to the internet
- Keep your `.env` file secure (contains API keys)
- The `.env` file is in `.gitignore` and won't be committed

---

## Support

If you have issues:

1. Check the logs: `docker logs tempest-overlay`
2. Verify `.env` configuration
3. Ensure Docker is running: `docker ps`
4. Test endpoints: `curl http://localhost:8036/`

---

Happy streaming! 🌤️📹

