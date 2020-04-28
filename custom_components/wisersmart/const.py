import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "wisersmart"
DATA_WISER_SMART_CONFIG = "wiserSmart_config"
VERSION = "0.9.1"
WISER_SMART_PLATFORMS = ["climate", "sensor", "switch"]

# Battery Constants

THERMOSTAT_MIN_BATTERY_LEVEL = 1
THERMOSTAT_FULL_BATTERY_LEVEL = 3


# Controller
CONTROLLERNAME = "Wiser Smart Controller"
MANUFACTURER = "Schneider Electric"
ROOM = "Room"

# Notifications
NOTIFICATION_ID = "wiser_smart_notification"
NOTIFICATION_TITLE = "Wiser Smart Component Setup"

# Default Values
DEFAULT_SCAN_INTERVAL = 300

DEVICE_STATUS_ICONS = {
    "ONLINE": "mdi:remote",
    "OFFLINE": "mdi:remote-off",
}

WISER_SMART_HOME_MODE_ICONS = {
    "manual": "mdi:gesture-tap",
    "schedule": "mdi:calendar-clock",
    "energysaver": "mdi:battery-plus",
    "holiday": "mdi:palm-tree",
}

WISER_SMART_SERVICES = {
    "SERVICE_SET_APPLIANCE_STATE": "set_appliance_state",
}
