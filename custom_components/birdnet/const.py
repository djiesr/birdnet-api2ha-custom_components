"""Constants for BirdNET integration (birdnet-api2ha)."""

DOMAIN = "birdnet"
MANUFACTURER = "BirdNET-Go API2HA"
MODEL = "BirdNET-Go Station"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_STATION_NAME = "station_name"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TIMEOUT = "timeout"

DEFAULT_PORT = 8081
DEFAULT_STATION_NAME = "station"
DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_TIMEOUT = 15

EVENT_NEW_DETECTION = f"{DOMAIN}_new_detection"

SENSOR_TYPES = {
    "detections_today": {
        "name": "Detections today",
        "icon": "mdi:calendar-today",
        "unit": "detections",
    },
    "detections_week": {
        "name": "Detections this week",
        "icon": "mdi:calendar-week",
        "unit": "detections",
    },
    "species_today": {
        "name": "Species today",
        "icon": "mdi:bird",
        "unit": "species",
    },
    "species_week": {
        "name": "Species this week",
        "icon": "mdi:bird",
        "unit": "species",
    },
    "last_detection": {
        "name": "Last detection",
        "icon": "mdi:bird",
        "unit": None,
    },
}
