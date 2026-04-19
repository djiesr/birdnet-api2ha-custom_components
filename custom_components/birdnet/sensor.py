"""Sensors for BirdNET (birdnet-api2ha)."""

from __future__ import annotations

import re
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SENSOR_TYPES, SYSTEM_SENSOR_TYPES, MANUFACTURER, MODEL, CONF_STATION_NAME, DEFAULT_STATION_NAME
from .coordinator import BirdNetCoordinator


def _slug(s: str) -> str:
    """Slug for entity_id: lowercase, spaces and accents to underscore."""
    s = (s or "").strip().lower()
    s = re.subn(r"[^a-z0-9]+", "_", s)[0].strip("_")
    return s or "unknown"


def _station_slug(config_entry: ConfigEntry) -> str:
    """Slug du nom de station pour les entity_id."""
    name = (config_entry.data.get(CONF_STATION_NAME) or DEFAULT_STATION_NAME).strip()
    return _slug(name) or _slug(DEFAULT_STATION_NAME)


def _device_info(entry_id: str, station_name: str) -> DeviceInfo:
    display = (station_name or DEFAULT_STATION_NAME).strip() or DEFAULT_STATION_NAME
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=f"BirdNET {display}",
        manufacturer=MANUFACTURER,
        model=MODEL,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from config entry."""
    coordinator: BirdNetCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    base_entities = [
        BirdNetSensor(coordinator, sensor_type, config_entry)
        for sensor_type in SENSOR_TYPES
    ]
    system_entities = [
        BirdNetSystemSensor(coordinator, sensor_type, config_entry)
        for sensor_type in SYSTEM_SENSOR_TYPES
    ]
    async_add_entities(base_entities + system_entities)
    coordinator.config_entry = config_entry
    coordinator.async_add_entities = async_add_entities
    coordinator._species_sensors_added = set()
    _patch_coordinator(coordinator)
    _maybe_add_species_sensors(coordinator)


class BirdNetSensor(CoordinatorEntity[BirdNetCoordinator], SensorEntity):
    """Main BirdNET sensors (detections, species, last detection)."""

    def __init__(
        self,
        coordinator: BirdNetCoordinator,
        sensor_type: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._config_entry = config_entry
        station_slug = _station_slug(config_entry)
        station_display = (config_entry.data.get(CONF_STATION_NAME) or DEFAULT_STATION_NAME).strip() or DEFAULT_STATION_NAME
        info = SENSOR_TYPES[sensor_type]
        self._attr_name = info["name"]
        self._attr_icon = info["icon"]
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_device_info = _device_info(config_entry.entry_id, station_display)
        self._attr_suggested_object_id = f"{station_slug}_{sensor_type}"

    @property
    def native_value(self) -> str | int | None:
        """Return the state."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data
        if self._sensor_type == "last_detection":
            return data.get("last_detection", {}).get("name", "—")
        return data.get(self._sensor_type, 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        if not self.coordinator.data:
            return {}
        data = self.coordinator.data
        attrs: dict = {}
        if self._sensor_type == "last_detection":
            last = data.get("last_detection", {})
            attrs = {
                "scientific_name": last.get("scientific_name") or "",
                "confidence": last.get("confidence"),
                "timestamp": last.get("timestamp") or "",
                "detection_id": last.get("id") or "",
                "audio_url": last.get("audio_url") or "",
                "image_url": last.get("image_url") or "",
                "friendly_name": last.get("name") or "—",
            }
            # Garder toutes les clés pour HA (ex. audio_url pour lire l'audio)
            attrs = {k: v for k, v in attrs.items() if v is not None}
        elif self._sensor_type == "detections_today":
            attrs = {"species_today": data.get("species_today")}
            stats_today = data.get("stats_today") or []
            species_list = [
                {
                    "common_name": s.get("common_name") or s.get("scientific_name"),
                    "scientific_name": s.get("scientific_name"),
                    "count": s.get("count", 0),
                }
                for s in stats_today if isinstance(s, dict)
            ]
            if species_list:
                attrs["species_list"] = species_list
        elif self._sensor_type == "detections_week":
            attrs = {"species_week": data.get("species_week")}
        return attrs


class BirdNetSpeciesSensor(CoordinatorEntity[BirdNetCoordinator], SensorEntity):
    """Per-species sensor: detections today for one species. Returns 0 after midnight (never unavailable)."""

    def __init__(
        self,
        coordinator: BirdNetCoordinator,
        species_name: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._species_name = species_name
        self._config_entry = config_entry
        station_slug = _station_slug(config_entry)
        station_display = (config_entry.data.get(CONF_STATION_NAME) or DEFAULT_STATION_NAME).strip() or DEFAULT_STATION_NAME
        species_slug = _slug(species_name)
        self._attr_name = f"Bird {species_name}"
        self._attr_icon = "mdi:bird"
        self._attr_native_unit_of_measurement = "detections"
        self._attr_unique_id = f"{config_entry.entry_id}_bird_{species_slug}"
        self._attr_device_info = _device_info(config_entry.entry_id, station_display)
        self._attr_suggested_object_id = f"{station_slug}_bird_{species_slug}"

    @property
    def native_value(self) -> int:
        """Today's count for this species; 0 if none (so entity stays available)."""
        if not self.coordinator.data:
            return 0
        return self.coordinator.get_count_today_for_species(self._species_name)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        count = self.native_value
        return {
            "species_name": self._species_name,
            "detections_today": count,
        }


class BirdNetSystemSensor(CoordinatorEntity[BirdNetCoordinator], SensorEntity):
    """System metrics sensors: IP, response time, CPU, RAM, disk."""

    def __init__(
        self,
        coordinator: BirdNetCoordinator,
        sensor_type: str,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._config_entry = config_entry
        station_slug = _station_slug(config_entry)
        station_display = (config_entry.data.get(CONF_STATION_NAME) or DEFAULT_STATION_NAME).strip() or DEFAULT_STATION_NAME
        info = SYSTEM_SENSOR_TYPES[sensor_type]
        self._data_key = info["data_key"]
        self._attr_name = info["name"]
        self._attr_icon = info["icon"]
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_unique_id = f"{config_entry.entry_id}_system_{sensor_type}"
        self._attr_suggested_object_id = f"{station_slug}_system_{sensor_type}"
        self._attr_device_info = _device_info(config_entry.entry_id, station_display)
        state_class = info.get("state_class")
        if state_class == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("system", {}).get(self._data_key)


def _maybe_add_species_sensors(coordinator: BirdNetCoordinator) -> None:
    """If new species appeared, add new BirdNetSpeciesSensor entities."""
    if not getattr(coordinator, "config_entry", None) or not getattr(coordinator, "async_add_entities", None):
        return
    known = coordinator.get_known_species()
    added = getattr(coordinator, "_species_sensors_added", set())
    to_add = known - added
    if not to_add:
        return
    new_entities = [
        BirdNetSpeciesSensor(coordinator, name, coordinator.config_entry)
        for name in sorted(to_add)
    ]
    coordinator._species_sensors_added.update(to_add)
    coordinator.hass.async_create_task(coordinator.async_add_entities(new_entities))
    return


def _patch_coordinator(coordinator: BirdNetCoordinator) -> None:
    """Register listener to add new species sensors on each update."""
    if getattr(coordinator, "_species_listener_patched", False):
        return
    coordinator._species_listener_patched = True

    def _on_update() -> None:
        _maybe_add_species_sensors(coordinator)

    coordinator.async_add_listener(_on_update)
