# vistter

A streaming pipeline that ingests a Wyze camera RTSP feed (via Wyse Bridge), applies a periodic overlay (e.g., weather/tide data), and pushes the composite stream to YouTube Live.

## Prerequisites

- Linux host with systemd
- `bash`, `curl`, `ffmpeg`
- Python 3 (optional, for the Python-based wrapper)
- Wyse Bridge RTSP server running and accessible

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/vistter.git
   cd vistter
   ```
2. Copy and customize the environment file:
   ```bash
   cp config.example.env .env
   ```

3. (Optional) Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```


4. (Optional) Use the provided install script to deploy the service, config, and wrapper automatically:
   ```bash
   sudo ./install.sh
   ```

## Configuration

All configurable parameters are documented in `config.example.env`. Edit `.env` or set environment variables directly to override the defaults.

- `OVERLAY_URL`: defaults to `http://tempest-overlay:8080/overlay.png`. Update if the Tempest overlay service is exposed at a different host/port.

- `RTSP_URL`: full RTSP feed URL override (e.g. with credentials); takes precedence over `RTSP_HOST`/`RTSP_PORT`/`CAMERA_NAME`.

Additional FFmpeg encoding options (for output quality and bitrate) can be configured via environment variables:

- `VIDEO_BITRATE`: target video bitrate (e.g., 2500k)
- `VIDEO_MAXRATE`: maximum video bitrate (e.g., 2500k)
- `VIDEO_BUF_SIZE`: FFmpeg buffer size (e.g., 5000k)
- `GOP_SIZE`: keyframe interval in frames (e.g., 60)
- `PRESET`: codec preset (e.g., veryfast)
- `PROFILE`: H.264 profile (e.g., high)
- `OUTPUT_FRAMERATE`: output frame rate (e.g., 30)
- `AUDIO_BITRATE`: audio bitrate (e.g., 128k)
- `AUDIO_CHANNELS`: number of audio channels (e.g., 2)
- `AUDIO_SAMPLE_RATE`: audio sampling rate (e.g., 44100)
- `SEGMENT_DURATION`: duration of each streaming segment before restart (HH:MM:SS, e.g., 00:30:00)
- `FFMPEG_RW_TIMEOUT`: network I/O timeout for ffmpeg in microseconds (e.g., 5000000)
- `LOG_LEVEL`: logging verbosity for the wrapper (DEBUG, INFO, WARNING, ERROR)

## Usage

### Shell-based wrapper
```bash
source .env
./ytlive_wyze_rtsp.sh
```

### Python-based wrapper
```bash
source .env
python3 ./stream_with_overlay.py
```

### Systemd service
Copy the Python wrapper, service, and config to the system directories, then enable and start:
```bash
sudo mkdir -p /etc/vistter
sudo cp config.example.env /etc/vistter/config.env
sudo cp stream_with_overlay.py /usr/local/bin/stream_with_overlay.py
sudo chmod +x /usr/local/bin/stream_with_overlay.py
sudo cp vistter.service /etc/systemd/system/vistter.service
sudo systemctl daemon-reload
sudo systemctl enable --now vistter
```

## Pipeline Diagram
```text
                       ┌────────────────┐
                       │ Weather Overlay│
                       │    (HTTP API)  │
                       └────────────────┘
                                │
                                ▼
   Wyze Camera RTSP ─► Wyse Bridge RTSP Server ─► FFmpeg ─► YouTube RTMP
                                ▲
                                │
                       ┌────────────────┐
                       │   FIFO Pipe    │
                       └────────────────┘
```

## Demos

See the `demos/` directory for example scripts demonstrating Wyse Bridge API usage.

## Troubleshooting

- Ensure Wyse Bridge is running and reachable (`$RTSP_HOST:$RTSP_PORT`).
- Verify `WB_API` token and `CAMERA_NAME` match your Wyse Bridge setup.
- Inspect service logs with `journalctl -u vistter` or scripting logs printed to stdout.
