"""Dreame Fridge integration (Dreamehome cloud)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DreameAuthError, DreameCloud, DreameError
from .const import CONF_COUNTRY, CONF_DEVICE_ID
from .coordinator import DreameFridgeCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

type DreameFridgeConfigEntry = ConfigEntry[DreameFridgeCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry) -> bool:
    cloud = DreameCloud(
        async_get_clientsession(hass), entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], entry.data[CONF_COUNTRY]
    )
    try:
        devices = await cloud.devices()
    except DreameAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except DreameError as err:
        raise ConfigEntryNotReady(str(err)) from err
    device = next((d for d in devices if d.did == entry.data[CONF_DEVICE_ID]), None)
    if device is None:
        raise ConfigEntryNotReady("Fridge not found in the Dreamehome account")

    coordinator = DreameFridgeCoordinator(hass, entry, cloud, device)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_start_push()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded
