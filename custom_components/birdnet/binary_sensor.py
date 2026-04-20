"""Binary sensors for BirdNET (birdnet-api2ha) — capteur En ligne."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL, CONF_STATION_NAME, DEFAULT_STATION_NAME
from .coordinator import BirdNetCoordinator
from .sensor import _slug, _station_slug


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from config entry."""
    coordinator: BirdNetCoordinator = hass.data[DOMAIN][config_entry.entry_id]["main"]
    async_add_entities([BirdNetOnlineSensor(coordinator, config_entry)])


class BirdNetOnlineSensor(CoordinatorEntity[BirdNetCoordinator], BinarySensorEntity):
    """Binary sensor: True when the birdnet-api2ha API is reachable."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:api"

    def __init__(self, coordinator: BirdNetCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        station_slug = _station_slug(config_entry)
        station_display = (config_entry.data.get(CONF_STATION_NAME) or DEFAULT_STATION_NAME).strip() or DEFAULT_STATION_NAME
        self._attr_name = "Online"
        self._attr_unique_id = f"{config_entry.entry_id}_online"
        self._attr_suggested_object_id = f"{station_slug}_online"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"BirdNET {station_display}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator._is_online
