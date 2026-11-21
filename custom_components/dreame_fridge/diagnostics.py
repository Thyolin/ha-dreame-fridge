"""Diagnostics (credentials and identifiers redacted)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import DreameFridgeConfigEntry
from .const import CONF_DEVICE_ID

REDACT = {CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID, "did", "mac", "owner_uid", "mqtt_host"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: DreameFridgeConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), REDACT),
        "device": async_redact_data(asdict(coordinator.device), REDACT),
        "push_connected": bool(coordinator.push and coordinator.push.connected),
        "values": coordinator.data,
        "reported_at": coordinator.reported_at,
    }
