#!/usr/bin/env python3
"""
stream_with_overlay.py: Python-based wrapper for streaming a Wyze Bridge RTSP feed to YouTube Live.

Features:
  - Load environment variables (WB_API, YOUTUBE_KEY, etc.) from .env or environment.
  - Periodically fetch overlay images (weather, tides) via HTTP and write to a FIFO pipe.
  - Launch ffmpeg to ingest RTSP video, apply overlay, and push to YouTube Live RTMP.
  - Automatic reconnection every segment interval with logging of events and exit codes.
"""
import os
import sys
import threading
import subprocess
import time
import logging
import signal
import urllib.request


def load_env_file(path='.env'):
    """Load key=value pairs from a .env file into os.environ."""
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for line in f:
            # Strip inline comments and whitespace
            stripped = line.split('#', 1)[0].strip()
            if not stripped or '=' not in stripped:
                continue
            key, val = stripped.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())


def fetch_overlay_loop(url, fifo_path, interval, stop_event):
    """Continuously fetch overlay images and write to FIFO."""
    logger = logging.getLogger('overlay')
    while not stop_event.is_set():
        try:
            logger.info('Fetching overlay image from %s', url)
            resp = urllib.request.urlopen(url, timeout=30)
            data = resp.read()
            with open(fifo_path, 'wb') as fifo:
                fifo.write(data)
            logger.debug('Wrote %d bytes to %s', len(data), fifo_path)
        except Exception as e:
            logger.error('Overlay fetch/write failed: %s', e)
        stop_event.wait(interval)


def main():
    # Load .env file if present
    load_env_file()

    # Configure logging level from environment (DEBUG, INFO, WARNING, ERROR)
    raw_ll = os.getenv('LOG_LEVEL', 'INFO').split('#', 1)[0].strip().upper()
    level = getattr(logging, raw_ll, logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger('stream_with_overlay')

    # Required environment variables
    WB_API = os.getenv('WB_API')
    YOUTUBE_KEY = os.getenv('YOUTUBE_KEY')
    if not WB_API or not YOUTUBE_KEY:
        logger.error('WB_API and YOUTUBE_KEY must be set')
        sys.exit(1)

    # Optional environment variables with defaults
    RTSP_HOST = os.getenv('RTSP_HOST', '127.0.0.1')
    RTSP_PORT = os.getenv('RTSP_PORT', '8554')
    RTSP_USER = os.getenv('RTSP_USER', 'wb')
    CAMERA_NAME = os.getenv('CAMERA_NAME', 'poolhouse')
    OVERLAY_URL = os.getenv(
        'OVERLAY_URL',
        'https://d3marco-service-2zlhs2gz7q-uk.a.run.app/seaer_ai/current_weather_tides/'
        '?location1=Shrewsberry+River&location2=Monmouth+Beach+NJ&'
        'stationName=8531942&api_key=7l0cOnQrBPq_DjYrShp_oyt9VkI7PoluiNj0Dcl9aQE'
    )
    OVERLAY_MARGIN = os.getenv('OVERLAY_MARGIN', '20')
    raw_poll = os.getenv('OVERLAY_POLL_INTERVAL', '60')
    raw_poll = raw_poll.split('#', 1)[0].strip()
    OVERLAY_POLL_INTERVAL = int(raw_poll)
    OVERLAY_FIFO = os.getenv('OVERLAY_FIFO', '/tmp/weather_overlay.fifo')
    SEGMENT_DURATION = os.getenv('SEGMENT_DURATION', '00:30:00')
    YOUTUBE_URL = os.getenv(
        'YOUTUBE_URL', f'rtmp://x.rtmp.youtube.com/live2/{YOUTUBE_KEY}'
    )
    # Microseconds to wait for network I/O before aborting FFmpeg (rw_timeout)
    FFMPEG_RW_TIMEOUT = os.getenv('FFMPEG_RW_TIMEOUT', '5000000')

    # Verify overlay URL before starting
    if not OVERLAY_URL:
        logger.error('OVERLAY_URL must be set')
        sys.exit(1)

    # Setup FIFO for overlay images
    try:
        if os.path.exists(OVERLAY_FIFO):
            os.remove(OVERLAY_FIFO)
        os.mkfifo(OVERLAY_FIFO)
    except Exception as e:
        logger.error('Failed to create FIFO %s: %s', OVERLAY_FIFO, e)
        sys.exit(1)

    stop_event = threading.Event()
    overlay_thread = threading.Thread(
        target=fetch_overlay_loop,
        args=(OVERLAY_URL, OVERLAY_FIFO, OVERLAY_POLL_INTERVAL, stop_event),
        daemon=True,
    )
    overlay_thread.start()

    # Graceful shutdown on SIGINT/SIGTERM
    def handle_exit(signum, frame):
        logger.info('Received signal %s, stopping...', signum)
        stop_event.set()
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # FFmpeg encoding settings to control output quality and bitrate (override via env)
    VIDEO_BITRATE = os.getenv('VIDEO_BITRATE', '2500k')
    VIDEO_MAXRATE = os.getenv('VIDEO_MAXRATE', VIDEO_BITRATE)
    # Default buffer size to twice the maxrate if in 'k' units, otherwise same as maxrate
    if VIDEO_MAXRATE.endswith('k') and VIDEO_MAXRATE[:-1].isdigit():
        default_buf = f"{int(VIDEO_MAXRATE[:-1]) * 2}k"
    else:
        default_buf = VIDEO_MAXRATE
    VIDEO_BUF_SIZE = os.getenv('VIDEO_BUF_SIZE', default_buf)
    GOP_SIZE = os.getenv('GOP_SIZE', '60')
    PRESET = os.getenv('PRESET', 'veryfast')
    PROFILE = os.getenv('PROFILE', 'high')
    OUTPUT_FRAMERATE = os.getenv('OUTPUT_FRAMERATE', '30')
    AUDIO_BITRATE = os.getenv('AUDIO_BITRATE', '128k')
    AUDIO_SAMPLE_RATE = os.getenv('AUDIO_SAMPLE_RATE', '44100')
    AUDIO_CHANNELS = os.getenv('AUDIO_CHANNELS', '2')

    count = 1
    # Main streaming loop
    while not stop_event.is_set():
        logger.info('Starting stream #%d', count)
        ffmpeg_cmd = [
            'ffmpeg',
            '-rw_timeout', FFMPEG_RW_TIMEOUT,
            '-rtsp_transport', 'tcp',
            '-thread_queue_size', '2048',
            '-t', SEGMENT_DURATION,
            '-i', f'rtsp://{RTSP_HOST}:{RTSP_PORT}/{CAMERA_NAME}',
            '-f', 'image2pipe', '-framerate', '1/60',
            '-i', OVERLAY_FIFO,
            '-f', 'lavfi', '-i', 'anullsrc',
            '-filter_complex',
            f'[1:v][0:v]scale2ref=w=iw:h=ow/mdar[ovr][base];'
            f'[base][ovr]overlay=x=0:y=main_h-overlay_h-{OVERLAY_MARGIN}:format=auto',
            '-r', OUTPUT_FRAMERATE,
            '-c:v', 'libx264',
            '-preset', PRESET,
            '-profile:v', PROFILE,
            '-pix_fmt', 'yuv420p',
            '-b:v', VIDEO_BITRATE,
            '-maxrate', VIDEO_MAXRATE,
            '-bufsize', VIDEO_BUF_SIZE,
            '-g', GOP_SIZE,
            '-c:a', 'aac',
            '-b:a', AUDIO_BITRATE,
            '-ar', AUDIO_SAMPLE_RATE,
            '-ac', AUDIO_CHANNELS,
            '-f', 'flv', YOUTUBE_URL,
        ]
        try:
            proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            restart_needed = False
            for line in proc.stdout:
                line = line.rstrip()
                logger.info(line)
                lower = line.lower()
                for pat in ('connection timed out', 'connection reset', 'broken pipe', 'error writing', '404', 'handshake failed'):
                    if pat in lower:
                        logger.warning('Detected ffmpeg error pattern %r, restarting stream', pat)
                        proc.kill()
                        restart_needed = True
                        break
                if restart_needed:
                    break
            proc.wait()
            exit_code = proc.returncode
        except Exception as e:
            logger.error('Error running ffmpeg: %s', e)
            exit_code = -1

        logger.info('Stream #%d ended with exit code %d', count, exit_code)
        try:
            with open('/tmp/streamcnt.txt', 'w') as cntf:
                cntf.write(str(count + 1))
        except Exception:
            pass
        count += 1
        # small delay before next segment
        time.sleep(1)

    logger.info('Exiting.')


if __name__ == '__main__':
    main() 