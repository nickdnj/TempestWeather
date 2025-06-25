# Design & Validation Checklist

## 1. System Architecture
- [ ] Document overall system architecture (diagram and description in README)
- [ ] Confirm all components: Wyze camera, wyze-bridge, Tempest Weather Station, Flask overlay server, FFmpeg pipeline, YouTube Live
- [ ] Define all data flows (RTSP, HTTP overlay, RTMP out)

## 2. Environment & Configuration
- [ ] Consolidate all environment variables in a single `.env` or config file
- [ ] Document all required and optional variables (e.g., OVERLAY_URL, YOUTUBE_KEY, WB_API, etc.)
- [ ] Validate that secrets (API keys, tokens) are not committed to version control

## 3. Overlay Server
- [ ] Flask overlay server runs and serves PNG images at `/overlay`
- [ ] Overlay image updates with real Tempest data (via REST API or UDP)
- [ ] Overlay image renders correctly (text, icons, layout)
- [ ] Overlay server handles errors gracefully (e.g., Tempest API down)

## 4. Tempest Weather Integration
- [ ] Obtain and securely store Tempest API token
- [ ] Fetch and parse latest weather data from Tempest API
- [ ] (Optional) Validate UDP local data integration for offline use
- [ ] Map Tempest data fields to overlay display

## 5. Streaming Pipeline
- [ ] RTSP stream from Wyze camera is accessible via wyze-bridge
- [ ] FFmpeg pipeline composites overlay image onto video stream
- [ ] Streaming pipeline can be started manually and via systemd service
- [ ] Overlay updates at the configured interval (matches polling)

## 6. Service Management
- [ ] Systemd service (`vistter.service`) is installed and enabled
- [ ] Service restarts on failure and logs to journald
- [ ] Logs are accessible and provide useful diagnostics

## 7. Testing & Validation
- [ ] End-to-end test: Wyze camera → overlay → YouTube Live (or test RTMP endpoint)
- [ ] Overlay image is visible and updates in the live stream
- [ ] System recovers from network or API failures (auto-reconnect)
- [ ] Validate on target hardware (Raspberry Pi 5)

## 8. Documentation
- [ ] README.md is up to date with architecture, setup, and usage
- [ ] Example `.env`/config file is provided and documented
- [ ] Troubleshooting section covers common issues (RTSP, overlay, API, streaming)
- [ ] References to all external dependencies and APIs

## 9. Security & Maintenance
- [ ] API tokens and stream keys are protected (file permissions, not in repo)
- [ ] Minimal external dependencies (documented and justified)
- [ ] Update instructions for dependencies and system packages

## 10. Extensibility & Future-Proofing
- [ ] Overlay code is modular (easy to add new data fields or graphics)
- [ ] Pipeline can be extended for new cameras, overlays, or streaming targets
- [ ] Code is commented and maintainable 