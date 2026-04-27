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
DEFAULT_SYSTEM_UPDATE_INTERVAL = 60
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

SYSTEM_SENSOR_TYPES = {
    "ip_address": {
        "name": "IP Address",
        "icon": "mdi:ip-network",
        "unit": None,
        "data_key": "ip_address",
        "state_class": None,
    },
    "response_time": {
        "name": "Response time",
        "icon": "mdi:timer-outline",
        "unit": "ms",
        "data_key": "response_time_ms",
        "state_class": "measurement",
    },
    "cpu": {
        "name": "CPU usage",
        "icon": "mdi:cpu-64-bit",
        "unit": "%",
        "data_key": "cpu_percent",
        "state_class": "measurement",
    },
    "memory": {
        "name": "Memory usage",
        "icon": "mdi:memory",
        "unit": "%",
        "data_key": "memory_percent",
        "state_class": "measurement",
    },
    "disk": {
        "name": "Disk usage",
        "icon": "mdi:harddisk",
        "unit": "%",
        "data_key": "disk_percent",
        "state_class": "measurement",
    },
}
