# Weather Overlay Streaming System

## 1. Project Overview
This project enables live streaming of RTSP video from a Wyze camera with a real-time weather overlay gadget, using data from a Tempest Weather Station. The system is designed to run fully locally on a Raspberry Pi 5, combining video streaming, weather data integration, and overlay rendering.

## 2. System Architecture
- **Wyze Camera** streams RTSP video via [wyze-bridge](https://github.com/mrlt8/docker-wyze-bridge) running on the Raspberry Pi.
- **Tempest Weather Station** provides real-time weather data via the Tempest REST API (or optionally, local UDP broadcast).
- **Flask Overlay Server** generates a weather overlay PNG image in memory, served via HTTP.
- **FFmpeg** composites the overlay image onto the video stream for live streaming (e.g., to YouTube).

```
[Wyze Camera] --(RTSP)--> [Raspberry Pi: wyze-bridge] --(video)--> [FFmpeg + Overlay] --(stream)--> [YouTube or other]
                                             ^
                                             |
                        [Flask Overlay Server <--- Tempest Weather Station]
```

## 3. Setup Instructions
1. **Set up wyze-bridge** on your Raspberry Pi to expose the RTSP stream from your Wyze camera.
2. **Install dependencies** for the overlay server:
   ```bash
   conda create -n weather-overlay python=3.11
   conda activate weather-overlay
   pip install -r requirements.txt
   ```
3. **Configure Tempest API access**:
   - Generate a personal access token from your Tempest account ([instructions](https://apidocs.tempestwx.com/reference/quick-start)).
   - Set the token in your overlay code or as an environment variable.
4. **Run the Flask overlay server**:
   ```bash
   python overlay/flask_overlay_server.py
   ```
5. **Use FFmpeg to composite the overlay image onto the video stream** (see Streaming Pipeline below).

## 4. Tempest API Integration
- The overlay server fetches current weather data from the Tempest Weather Station using the REST API and your personal access token.
- Example API call to get latest station observation:
  ```
  https://swd.weatherflow.com/swd/rest/observations/station/[your_station_id]?token=[your_access_token]
  ```
- For fully offline use, you may use the Tempest local UDP broadcast interface (see [Tempest API docs](https://apidocs.tempestwx.com/reference/quick-start)).

## 5. Streaming Pipeline
- **FFmpeg** is used to overlay the weather PNG onto the RTSP video stream in real time.
- Example FFmpeg command:
  ```bash
  ffmpeg -i rtsp://<wyze-bridge-rtsp-url> -i http://localhost:5000/overlay -filter_complex "overlay=10:10" -f flv rtmp://a.rtmp.youtube.com/live2/<stream-key>
  ```
- Adjust overlay position and output as needed.

## 6. Example Usage
- Start the overlay server:
  ```bash
  python overlay/flask_overlay_server.py
  ```
- Start the FFmpeg pipeline (replace URLs and keys as needed):
  ```bash
  ffmpeg -i rtsp://raspi.local:8554/camera -i http://localhost:5000/overlay -filter_complex "overlay=10:10" -f flv rtmp://a.rtmp.youtube.com/live2/your-stream-key
  ```

## 7. Requirements
- Raspberry Pi 5 (or similar Linux SBC)
- Wyze camera(s) and wyze-bridge
- Tempest Weather Station (on same network)
- Python 3.11, Flask, Pillow, Requests
- FFmpeg

## 8. References
- [Tempest API Quick Start](https://apidocs.tempestwx.com/reference/quick-start)
- [wyze-bridge GitHub](https://github.com/mrlt8/docker-wyze-bridge)
- [FFmpeg Documentation](https://ffmpeg.org/)

## 9. Streaming Pipeline Integration

This project incorporates the robust streaming pipeline from the Vistter project:

- **integration/stream_with_overlay.py**: Python wrapper for streaming RTSP from Wyze Bridge, fetching overlay images, and streaming to YouTube Live via FFmpeg.
- **integration/vistter.service**: Systemd unit for running the pipeline as a managed service.
- **integration/config.example.env**: Example environment configuration for all pipeline variables.
- **integration/PRODUCT_REQUIREMENTS_SPEC.md**: Full product requirements for the streaming pipeline.
- **integration/README.md**: Additional usage and troubleshooting documentation.

**To use:**
1. Copy or symlink the files in `integration/` as needed.
2. Set `OVERLAY_URL` in your `.env` to your local Flask overlay server (e.g., `http://localhost:5000/overlay?...`).
3. Start the service with systemd or run the script manually:
   ```bash
   python integration/stream_with_overlay.py
   ```

All configuration is managed via environment variables. See `integration/config.example.env` for all options.

## 10. References

- [Vistter Product Requirements Spec](integration/PRODUCT_REQUIREMENTS_SPEC.md)
- [Vistter README](integration/README.md)

**Note:** In the setup instructions above, you can use the integrated streaming pipeline for end-to-end streaming with overlay. See Section 9 for details.
