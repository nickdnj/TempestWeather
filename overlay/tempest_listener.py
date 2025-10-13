"""
Utilities for consuming Tempest UDP broadcast data and exposing the latest
observation in-memory for use by the overlay generator.
"""
from __future__ import annotations

import json
import os
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


UDP_PORT = _env_int("TEMPEST_UDP_PORT", 50222)
LISTEN_ADDRESS = os.getenv("TEMPEST_UDP_BIND", "")


@dataclass(frozen=True)
class TempestObservation:
    observed_at: datetime
    temperature_c: Optional[float]
    wind_speed_ms: Optional[float]
    wind_direction_deg: Optional[float]
    humidity: Optional[float]
    pressure_hpa: Optional[float]
    rain_recent_mm: Optional[float]
    rain_day_mm: Optional[float]
    precipitation_type: Optional[int]
    solar_radiation_wm2: Optional[float]
    uv_index: Optional[float]

    @property
    def cache_token(self) -> Tuple:
        """Used to determine overlay cache validity."""
        return (
            int(self.observed_at.timestamp()),
            self.temperature_c,
            self.wind_speed_ms,
            self.wind_direction_deg,
            self.humidity,
            self.pressure_hpa,
            self.rain_recent_mm,
            self.rain_day_mm,
            self.precipitation_type,
            self.solar_radiation_wm2,
            self.uv_index,
        )


class TempestDataStore:
    """Background listener that keeps the latest Tempest observation in memory."""

    def __init__(self, address: str = LISTEN_ADDRESS, port: int = UDP_PORT) -> None:
        self._bind_address = address
        self._port = port
        self._lock = threading.Lock()
        self._latest: Optional[TempestObservation] = None
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            name="TempestUDPListener",
            daemon=True,
        )
        self._listener_thread.start()

    def latest(self) -> Optional[TempestObservation]:
        with self._lock:
            return self._latest

    # === Internal helpers ===
    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self._bind_address, self._port))
        while True:
            try:
                payload, _ = sock.recvfrom(4096)
            except OSError:
                continue
            try:
                message = json.loads(payload.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            self._handle_message(message)

    def _handle_message(self, message: dict) -> None:
        if message.get("type") != "obs_st":
            return
        observations = message.get("obs")
        if not observations:
            return
        obs = observations[0]
        self._update_latest(self._parse_obs(obs))

    def _update_latest(self, observation: TempestObservation) -> None:
        with self._lock:
            self._latest = observation

    @staticmethod
    def _parse_obs(obs: list) -> TempestObservation:
        def safe_get(index: int) -> Optional[float]:
            try:
                value = obs[index]
            except IndexError:
                return None
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        timestamp = safe_get(0)
        observed_at = (
            datetime.fromtimestamp(timestamp, tz=timezone.utc)
            if timestamp
            else datetime.now(timezone.utc)
        )

        precipitation_type = safe_get(13)
        return TempestObservation(
            observed_at=observed_at,
            temperature_c=safe_get(7),
            wind_speed_ms=safe_get(2),
            wind_direction_deg=safe_get(4),
            humidity=safe_get(8),
            pressure_hpa=safe_get(6),
            rain_recent_mm=safe_get(12),
            rain_day_mm=safe_get(18),
            precipitation_type=int(precipitation_type) if precipitation_type is not None else None,
            solar_radiation_wm2=safe_get(11),
            uv_index=safe_get(10),
        )


# Module-level singleton used by the overlay service.
data_store = TempestDataStore()


def get_latest_observation() -> Optional[TempestObservation]:
    return data_store.latest()
