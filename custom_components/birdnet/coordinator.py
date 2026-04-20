"""Data update coordinator for BirdNET (birdnet-api2ha API)."""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_TIMEOUT,
    DEFAULT_TIMEOUT,
    EVENT_NEW_DETECTION,
)

_LOGGER = logging.getLogger(__name__)


class BirdNetCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch data from birdnet-api2ha REST API. Keeps last good data on API errors."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        update_interval: int,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize."""
        self.host = host.strip()
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{self.host}:{self.port}"
        self._last_detection_id: str | None = None
        self._last_successful_data: dict[str, Any] | None = None
        self._known_species: set[str] = set()
        self._is_online: bool = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch stats and last detection from API. Keep last good data on empty/error."""
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        today = date.today().isoformat()

        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                stats_week, stats_today, detections, system_data, response_time_ms = await self._fetch_all(session, today)
            self._is_online = True
        except Exception as err:
            _LOGGER.warning("API request failed: %s", err)
            self._is_online = False
            if self._last_successful_data is not None:
                return self._last_successful_data
            raise UpdateFailed(f"API error: {err}") from err

        # If all endpoints returned empty, keep last successful data (avoid flicker to 0)
        # Always inject fresh system data so CPU/RAM/disk sensors are never stuck at None
        fresh_system = {
            "ip_address": system_data.get("ip_address") or "",
            "cpu_percent": system_data.get("cpu_percent"),
            "memory_percent": system_data.get("memory_percent"),
            "disk_percent": system_data.get("disk_percent"),
            "response_time_ms": response_time_ms,
        }
        if not stats_week and not stats_today and not detections:
            _LOGGER.debug("All API responses empty, keeping last successful data")
            if self._last_successful_data is not None:
                return {**self._last_successful_data, "system": fresh_system}
            data = self._empty_data(today)
            data["system"] = fresh_system
            return data

        # Build result
        detections_week = sum(s.get("count", 0) for s in stats_week)
        species_week = len(stats_week)
        detections_today = sum(s.get("count", 0) for s in stats_today)
        species_today = len(stats_today)

        last_detection: dict[str, Any] = {
            "name": "—",
            "scientific_name": "",
            "timestamp": "",
            "confidence": 0,
            "id": "",
            "audio_url": "",
        }
        if detections and isinstance(detections, list) and len(detections) > 0:
            first = detections[0] if isinstance(detections[0], dict) else {}
            conf = first.get("confidence") or 0
            if isinstance(conf, float) and conf <= 1:
                conf = round(conf * 100, 1)
            last_detection = {
                "name": first.get("common_name") or first.get("scientific_name") or "—",
                "scientific_name": first.get("scientific_name") or "",
                "timestamp": first.get("timestamp") or "",
                "confidence": conf,
                "id": str(first.get("id", "")),
                "audio_url": first.get("audio_url") or "",
                "image_url": first.get("image_url") or "",
            }
            did = str(first.get("id", ""))
            if self._last_detection_id is not None and did and did != self._last_detection_id:
                self.hass.bus.async_fire(
                    EVENT_NEW_DETECTION,
                    {
                        "common_name": last_detection["name"],
                        "scientific_name": last_detection["scientific_name"],
                        "confidence": first.get("confidence"),
                        "timestamp": last_detection["timestamp"],
                        "id": did,
                    },
                )
            if did:
                self._last_detection_id = did

        # Track known species (from stats_today + stats_week) for per-species sensors
        for s in stats_today or []:
            if isinstance(s, dict):
                name = (s.get("common_name") or s.get("scientific_name") or "").strip()
                if name:
                    self._known_species.add(name)
        for s in stats_week or []:
            if isinstance(s, dict):
                name = (s.get("common_name") or s.get("scientific_name") or "").strip()
                if name:
                    self._known_species.add(name)

        result = {
            "detections_today": detections_today,
            "detections_week": detections_week,
            "species_today": species_today,
            "species_week": species_week,
            "last_detection": last_detection,
            "stats_today": stats_today or [],
            "stats_week": stats_week or [],
            "date_today": today,
            "system": {
                "ip_address": system_data.get("ip_address") or "",
                "cpu_percent": system_data.get("cpu_percent"),
                "memory_percent": system_data.get("memory_percent"),
                "disk_percent": system_data.get("disk_percent"),
                "response_time_ms": response_time_ms,
            },
        }
        self._last_successful_data = result
        return result

    def _empty_data(self, today: str) -> dict[str, Any]:
        """Return minimal data when no API data (first run or all empty)."""
        return {
            "detections_today": 0,
            "detections_week": 0,
            "species_today": 0,
            "species_week": 0,
            "last_detection": {"name": "—", "scientific_name": "", "timestamp": "", "confidence": 0, "id": "", "audio_url": "", "image_url": ""},
            "stats_today": [],
            "stats_week": [],
            "date_today": today,
            "system": {"ip_address": "", "cpu_percent": None, "memory_percent": None, "disk_percent": None, "response_time_ms": None},
        }

    def get_known_species(self) -> set[str]:
        """Return set of species that have been seen (for per-species sensors)."""
        return set(self._known_species)

    def get_count_today_for_species(self, species_name: str) -> int:
        """Return today's detection count for a species (0 if not in stats_today)."""
        if not self.data or not self.data.get("stats_today"):
            return 0
        for s in self.data["stats_today"]:
            if not isinstance(s, dict):
                continue
            name = (s.get("common_name") or s.get("scientific_name") or "").strip()
            if name == species_name:
                return int(s.get("count") or 0)
        return 0

    async def _fetch_all(
        self,
        session: aiohttp.ClientSession,
        today: str,
    ) -> tuple[list, list, list, dict, int]:
        """Fetch stats, detections and system info in parallel. Returns response time in ms."""
        import asyncio

        async def get_json(url: str) -> list:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data if isinstance(data, list) else []
            except Exception as e:
                _LOGGER.warning("Fetch %s failed: %s", url, e)
                return []

        async def get_dict(url: str) -> dict:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()
                    return data if isinstance(data, dict) else {}
            except Exception as e:
                _LOGGER.warning("Fetch %s failed: %s", url, e)
                return {}

        stats_week_url = f"{self.base_url}/api/stats?period=week"
        stats_today_url = f"{self.base_url}/api/stats?date_start={today}&date_end={today}"
        detections_url = f"{self.base_url}/api/detections?period=week&limit=1"
        system_url = f"{self.base_url}/api/system"

        t_start = time.monotonic()
        stats_week, stats_today, detections, system_data = await asyncio.gather(
            get_json(stats_week_url),
            get_json(stats_today_url),
            get_json(detections_url),
            get_dict(system_url),
        )
        response_time_ms = round((time.monotonic() - t_start) * 1000)
        return stats_week, stats_today, detections, system_data, response_time_ms
