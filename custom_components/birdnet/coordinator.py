"""Data update coordinators for BirdNET (birdnet-api2ha API)."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_TIMEOUT,
    DEFAULT_SYSTEM_UPDATE_INTERVAL,
    EVENT_NEW_DETECTION,
)
from .species_fr_cache import SpeciesFrCache

_LOGGER = logging.getLogger(__name__)


class BirdNetCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch detections/stats from birdnet-api2ha REST API. Keeps last good data on API errors."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        update_interval: int,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host.strip()
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{self.host}:{self.port}"
        self._last_detection_id: str | None = None
        self._last_successful_data: dict[str, Any] | None = None
        self._known_species: set[str] = set()
        self._is_online: bool = False
        self._fr_lookup_pending: set[str] = set()
        self._tick = 0  # incremented each coordinator run (base interval = 60s)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

        cache_path = hass.config.path(".storage", "birdnet_species_fr.json")
        self._fr_cache = SpeciesFrCache(cache_path)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data with staggered intervals to reduce Pi load.

        detections  → every tick      (60s  = ~1 min)
        stats_today → every 5 ticks   (300s = ~5 min)
        stats_week  → every 60 ticks  (3600s = ~1 h)
        """
        self._tick += 1
        is_first = self._tick == 1
        fetch_today = is_first or (self._tick % 5 == 0)
        fetch_week = is_first or (self._tick % 60 == 0)
        today = date.today().isoformat()

        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                stats_week_new, stats_today_new, detections = await self._fetch_selective(
                    session, today, fetch_today=fetch_today, fetch_week=fetch_week
                )
            self._is_online = True
        except Exception as err:
            _LOGGER.warning("API request failed: %s", err)
            self._is_online = False
            if self._last_successful_data is not None:
                return self._last_successful_data
            raise UpdateFailed(f"API error: {err}") from err

        # For endpoints not fetched this tick, reuse cached values
        prev = self._last_successful_data or {}
        stats_week = stats_week_new if fetch_week else (prev.get("stats_week") or [])
        stats_today = stats_today_new if fetch_today else (prev.get("stats_today") or [])

        # If everything is empty and we have prior data, keep it (avoid flicker to 0)
        if not detections and not stats_today and not stats_week:
            _LOGGER.debug("All API responses empty, keeping last successful data")
            if self._last_successful_data is not None:
                return self._last_successful_data
            return self._empty_data(today)

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

        # Track known species for per-species sensors
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
        }
        self._last_successful_data = result
        return result

    def _empty_data(self, today: str) -> dict[str, Any]:
        return {
            "detections_today": 0,
            "detections_week": 0,
            "species_today": 0,
            "species_week": 0,
            "last_detection": {"name": "—", "scientific_name": "", "timestamp": "", "confidence": 0, "id": "", "audio_url": "", "image_url": ""},
            "stats_today": [],
            "stats_week": [],
            "date_today": today,
        }

    def get_known_species(self) -> set[str]:
        return set(self._known_species)

    def get_count_today_for_species(self, species_name: str) -> int:
        if not self.data or not self.data.get("stats_today"):
            return 0
        for s in self.data["stats_today"]:
            if not isinstance(s, dict):
                continue
            name = (s.get("common_name") or s.get("scientific_name") or "").strip()
            if name == species_name:
                return int(s.get("count") or 0)
        return 0

    def get_species_info(self, species_name: str) -> dict:
        """Return image_url and scientific_name for a species from stats data."""
        if not self.data:
            return {}
        for dataset in (self.data.get("stats_today") or [], self.data.get("stats_week") or []):
            for s in dataset:
                if not isinstance(s, dict):
                    continue
                name = (s.get("common_name") or s.get("scientific_name") or "").strip()
                if name == species_name:
                    return {
                        "scientific_name": s.get("scientific_name") or "",
                        "image_url": s.get("image_url") or "",
                    }
        return {}

    def get_french_name(self, scientific_name: str) -> str | None:
        """Return French common name from cache; schedule a Wikidata lookup if missing."""
        if not scientific_name:
            return None
        cached = self._fr_cache.get(scientific_name)
        if cached is not None:
            return cached
        if scientific_name not in self._fr_lookup_pending:
            self._fr_lookup_pending.add(scientific_name)
            self.hass.async_create_task(self._lookup_fr_name(scientific_name))
        return None

    async def _lookup_fr_name(self, scientific_name: str) -> None:
        """Fetch French name from Wikidata in background, then refresh listeners."""
        result = await self._fr_cache.fetch(scientific_name)
        self._fr_lookup_pending.discard(scientific_name)
        if result:
            self.async_update_listeners()

    async def _fetch_selective(
        self,
        session: aiohttp.ClientSession,
        today: str,
        fetch_today: bool = True,
        fetch_week: bool = True,
    ) -> tuple[list | None, list | None, list]:
        """Fetch only the endpoints needed this tick."""

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

        tasks: list = []
        if fetch_week:
            tasks.append(get_json(f"{self.base_url}/api/stats?period=week"))
        if fetch_today:
            tasks.append(get_json(f"{self.base_url}/api/stats?date_start={today}&date_end={today}"))
        tasks.append(get_json(f"{self.base_url}/api/detections?period=week&limit=1"))

        results = await asyncio.gather(*tasks)

        idx = 0
        stats_week = None
        stats_today = None
        if fetch_week:
            stats_week = results[idx]; idx += 1
        if fetch_today:
            stats_today = results[idx]; idx += 1
        detections = results[idx]

        return stats_week, stats_today, detections


class BirdNetSystemCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch system metrics from /api/system at a fast independent interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        update_interval: int = DEFAULT_SYSTEM_UPDATE_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = f"http://{host.strip()}:{port}"
        self.timeout = timeout

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_system",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                t_start = time.monotonic()
                async with session.get(f"{self.base_url}/api/system") as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status}")
                    data = await resp.json()
                response_time_ms = round((time.monotonic() - t_start) * 1000)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"System API error: {err}") from err

        return {
            "ip_address": data.get("ip_address") or "",
            "cpu_percent": data.get("cpu_percent"),
            "memory_percent": data.get("memory_percent"),
            "disk_percent": data.get("disk_percent"),
            "response_time_ms": response_time_ms,
        }
