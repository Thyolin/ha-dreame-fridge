"""Constants for the Dreame Fridge integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dreame_fridge"

CONF_COUNTRY: Final = "country"
CONF_DEVICE_ID: Final = "device_id"

# Server regions offered by the Dreamehome app.
COUNTRIES: Final = ["eu", "us", "cn", "sg", "ru", "kr"]

POLL_INTERVAL: Final = timedelta(seconds=60)

# --- Dreamehome app identifiers --------------------------------------------
# These values identify the public Dreamehome *app* towards the cloud. They are
# shipped inside every copy of the app and are the same for all users. They are
# NOT user credentials; your own e-mail/password are only stored in the Home
# Assistant config entry.
API_HOST_SUFFIX: Final = ".iot.dreame.tech"
API_PORT: Final = 13267
APP_BASIC_AUTH: Final = "ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
APP_PASSWORD_SALT: Final = "RAylYC%fmSKp7%Tq"
APP_SIGN_KEY: Final = b"EETjszu*XI5znHsI"
APP_VERSION_CODE: Final = "102060300"
APP_USER_AGENT: Final = "Dart/3.10 (dart:io)"
DEFAULT_TENANT: Final = "000000"

# Property keys ("siid.piid") of the Dreame Fizz Fresh (dreame.fridge.g2509),
# taken from the official device plugin.
KEY_FRIDGE_TEMP: Final = "1.1"
KEY_FREEZER_TEMP: Final = "2.1"
KEY_MODE: Final = "3.1"
KEY_ICE_CUBE: Final = "4.1"
KEY_ICE_CRUNCH: Final = "4.2"
KEY_FLEX_ZONE: Final = "5.1"
KEY_SPARKLING: Final = "6.1"
KEY_ALWAYS_FRESH: Final = "6.2"
KEY_AUTOFILL: Final = "6.4"
KEY_QUIET_TIME: Final = "7.1"
KEY_NIGHT_VIEW: Final = "8.1"
KEY_NIGHT_VIEW_LEVEL: Final = "8.3"
KEY_ERROR: Final = "9.1"
KEY_DOOR: Final = "10.1"
KEY_ICE_CUBE_FULL: Final = "11.1"
KEY_ICE_CRUNCH_FULL: Final = "11.2"
KEY_CO2_LOW: Final = "12.1"
KEY_WATER_LOW: Final = "12.2"
KEY_SABBATH: Final = "14.2"
KEY_STILL_WATER: Final = "16.1"
KEY_SPARKLING_WATER: Final = "16.2"
KEY_CARBONATION: Final = "16.3"

# Values that can be read with get_properties. Never add unknown keys here:
# the cloud does not answer a batch that contains a non-existing property.
POLL_KEYS: Final = [
    "1.1", "2.1", "3.1", "4.1", "4.2", "5.1", "6.1", "6.2", "6.4", "7.1",
    "8.1", "8.3", "9.1", "10.1", "11.1", "11.2", "12.1", "12.2", "14.2",
]
# Values that are only reported by the device (read from the cloud cache).
REPORT_KEYS: Final = ["16.1", "16.2", "16.3"]

# Allowed values for writing, exactly as the official app uses them.
WRITABLE: Final[dict[str, set[int]]] = {
    KEY_FRIDGE_TEMP: set(range(2, 9)),
    KEY_FREEZER_TEMP: set(range(-23, -14)),
    KEY_MODE: {0, 1, 2, 3, 4},
    KEY_ICE_CUBE: {0, 1},
    KEY_ICE_CRUNCH: {0, 1},
    KEY_FLEX_ZONE: {1, 2, 3},
    KEY_SPARKLING: {0, 1},
    KEY_ALWAYS_FRESH: {0, 1},
    KEY_AUTOFILL: {0, 1},
    KEY_NIGHT_VIEW: {0, 1},
    KEY_NIGHT_VIEW_LEVEL: {1, 2, 3},
}

MODE_OPTIONS: Final = {
    0: "manual",
    1: "super_cool",
    2: "super_freeze",
    3: "vacation",
    4: "super_cool_freeze",
}
FLEX_ZONE_OPTIONS: Final = {1: "fruit_vegetables", 2: "drinks", 3: "soft_freeze"}
NIGHT_VIEW_LEVEL_OPTIONS: Final = {1: "moonlight", 2: "comfort", 3: "bright"}
ERROR_OPTIONS: Final = {
    0: "none",
    1: "sensor_1",
    2: "sensor_2",
    3: "sensor_3",
    4: "sensor_4",
    5: "sensor_5",
    6: "sensor_6",
    7: "sensor_7",
    8: "communication",
    9: "door_open_too_long",
    10: "ice_sensor_1",
    11: "ice_sensor_2",
    12: "sparkling_sensor",
}
