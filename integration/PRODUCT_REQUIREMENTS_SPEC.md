# Product Requirements Specification: Vistter YouTube Live Streaming

## 1. Introduction

### 1.1 Purpose
This document translates the recommendations from `REVIEW.md` into a clear set of product requirements
for the Vistter YouTube Live Streaming solution. It serves as a single source of truth for design,
implementation, and operational requirements.

### 1.2 Scope
The scope covers the end‑to‑end streaming pipeline from Wyze Bridge RTSP feed to YouTube Live,
including configuration management, service orchestration, logging, documentation, and error handling.

### 1.3 References
- `REVIEW.md`: Prototype Code Review & Wyse Bridge Integration Report

## 2. Overall Description

### 2.1 Product Perspective
Vistter is a pipeline that ingests a Wyze camera RTSP feed (via Wyse Bridge), applies a periodic weather
overlay, and pushes the composite stream to YouTube Live.

### 2.2 Product Functions
- Capture RTSP video frames from Wyse Bridge.
- Fetch and overlay weather/tide graphics at configurable intervals.
- Encode and package audio/video for YouTube RTMP ingest.
- Provide automatic reconnection logic on stream interruptions.
- Expose a service unit for managed deployment and automatic restarts.
- Surface operational metrics and logs via systemd/journald.

### 2.3 User Classes and Characteristics
- **DevOps Engineers**: Install, configure, and monitor the streaming service.
- **Field Technicians**: Perform on‑site validation and troubleshooting.
- **Project Maintainers**: Extend the pipeline (e.g. add new overlays or outputs).

### 2.4 Operating Environment
- Host operating system with systemd (e.g. Linux).
- Installed dependencies: `bash`, `ffmpeg`, `curl`, Python 3 (for optional script), and Wyse Bridge RTSP server.

### 2.5 Design and Implementation Constraints
- Must maintain compatibility with existing `ytlive_wyze_rtsp.sh` workflow.
- Avoid introducing external dependencies beyond standard UNIX utilities and Python standard libraries.

## 3. System Features and Requirements

### 3.1 Configuration Management
- Provide a consolidated environment file named `config.example.env` at the repository root. It must document
  all required and optional environment variables:
  - `WB_API` (required): Wyse Bridge API token / RTSP authentication.
  - `YOUTUBE_KEY` (required): YouTube Live stream key.
  - `RTSP_HOST`, `RTSP_PORT`, `RTSP_USER`, `CAMERA_NAME`, `OVERLAY_URL`, `OVERLAY_MARGIN`, `OVERLAY_POLL_INTERVAL`, `OVERLAY_FIFO`, `SEGMENT_DURATION`, `FFMPEG_RW_TIMEOUT`, `LOG_LEVEL` (optional with defaults), and FFmpeg encoding variables (`VIDEO_BITRATE`, `VIDEO_MAXRATE`, `VIDEO_BUF_SIZE`, `GOP_SIZE`, `PRESET`, `PROFILE`, `OUTPUT_FRAMERATE`, `AUDIO_BITRATE`, `AUDIO_CHANNELS`, `AUDIO_SAMPLE_RATE`).
- Support a local `.env` file for override of environment variables in deployment.

### 3.2 Streaming Wrapper Script
- Maintain `ytlive_wyze_rtsp.sh` as the canonical shell‑based wrapper. Ensure the script includes:
  - Fail‑fast mode (`set -euo pipefail`).
  - Log output and exit status with timestamps.
  - Automatic reconnection every 30 minutes.
  - Clean-up and recreation of overlay FIFO at startup.

### 3.3 Python‑Based Streaming Option
- Introduce a Python version of the streaming pipeline named `stream_with_overlay.py` with functional parity:
  - Richer error handling and retries.
  - Structured logging (e.g. via Python `logging` module).
  - Modular overlay polling and FFmpeg process management.

### 3.4 Service Orchestration (systemd Unit)
- Provide `vistter.service` for systemd, conforming to best practices:
  - Uses `EnvironmentFile=/etc/vistter/config.env` or equivalent.
  - `ExecStart` points to the selected wrapper script.
  - Automatic restarts on failure (`Restart=on-failure`, `RestartSec`).
  - Proper dependency ordering (`After=network.target wyse-bridge.service`).
- Document installation steps: copying service file, reloading systemd, and enabling the service.

### 3.5 Logging and Monitoring
- Route all logs through systemd/journald instead of plain `/tmp/*.log`.
- Define log levels and filtering strategy (configurable via `LOG_LEVEL` environment variable).
- Expose minimal health metrics or counters via journald tags (e.g. stream attempt count).

### 3.6 Documentation
- Expand `README.md` with:
  - Project overview and purpose.
  - Prerequisites and dependency list.
  - Installation and setup guide (cloning repo, sourcing env, enabling service).
  - Usage examples (manual run, systemd).
  - Configuration reference (link to `config.example.env`).
  - ASCII pipeline diagram.
  - Troubleshooting tips (RTSP auth issues, overlay failures).

### 3.7 Wyse Bridge Integration
- Document Wyse Bridge dependency:
  - Repository URL and clone instructions.
  - Key modules and extension points (`rtspserver.py`, authentication flow).
  - Configuration knobs for RTSP feed performance.

### 3.8 Pipeline Diagram
Embed an ASCII diagram of the end‑to‑end data flow:

```
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

### 3.9 Demo Scripts
- Provide example demo scripts (e.g. motion‑controlled pan/tilt) to illustrate integration with the
  Wyse Bridge API.
- Organize demos in a `demos/` directory with a README explaining how to run and extend them.

## 4. External Interface Requirements

### 4.1 RTSP Feed
- Must support TCP transport and authentication as provided by Wyse Bridge.

### 4.2 Overlay HTTP API
- Poll at configurable intervals (default: 60 seconds).
- Return a single image/frame compatible with FFmpeg FIFO input.

### 4.3 YouTube RTMP Ingest
- Use RTMP URL `rtmp://x.rtmp.youtube.com/live2/${YOUTUBE_KEY}`.
- Ensure video codec h264, preset ultrafast, pixel format yuv420p.

## 5. Non-functional Requirements

### 5.1 Reliability
- Automatic reconnection on failures, with no manual intervention.
- Service restart on crash via systemd.

### 5.2 Maintainability
- Single source of environment configuration.
- Well‑structured Python code for optional streaming implementation.

### 5.3 Performance
- Overlay polling interval tunable without service interruption.
- Low‑latency processing path from RTSP ingest to RTMP output.

### 5.4 Security
- Protect API tokens and stream keys in environment files with appropriate file permissions.
- Minimize attack surface by limiting external dependencies.

### 5.5 Extensibility
- Modular overlay component to allow adding new overlays (e.g. motion detection).

## 6. Revision History

| Version | Date       | Description                      |
|---------|------------|----------------------------------|
| 0.1     | YYYY‑MM‑DD | Initial draft based on REVIEW.md |