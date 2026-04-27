"""BirdNET integration (birdnet-api2ha)."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_SYSTEM_UPDATE_INTERVAL,
    DEFAULT_TIMEOUT,
)
from .coordinator import BirdNetCoordinator, BirdNetSystemCoordinator

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BirdNET from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    timeout = entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

    coordinator = BirdNetCoordinator(hass, host, port, update_interval, timeout)
    system_coordinator = BirdNetSystemCoordinator(hass, host, port, DEFAULT_SYSTEM_UPDATE_INTERVAL, timeout)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "main": coordinator,
        "system": system_coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start system coordinator 30s after main to stagger API calls on the Pi:
    # 0:00 main refresh, 0:30 system refresh, 1:00 main, 1:30 system, ...
    async def _delayed_system_start() -> None:
        await asyncio.sleep(30)
        await system_coordinator.async_config_entry_first_refresh()

    hass.async_create_task(_delayed_system_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
