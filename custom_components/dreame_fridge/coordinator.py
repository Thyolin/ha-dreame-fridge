"""Data coordinator: periodic polling plus MQTT push."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DreameAuthError, DreameCloud, DreameDevice, DreameError
from .const import DOMAIN, POLL_INTERVAL, POLL_KEYS, REPORT_KEYS, WRITABLE
from .push import DreamePush, build_tls_context

_LOGGER = logging.getLogger(__name__)


class DreameFridgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the latest property values as {"siid.piid": value}."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cloud: DreameCloud, device: DreameDevice) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=POLL_INTERVAL)
        self.cloud = cloud
        self.device = device
        self.reported_at: dict[str, float] = {}
        self.push: DreamePush | None = None
        self.data = {}

    async def async_start_push(self) -> None:
        tls = await self.hass.async_add_executor_job(build_tls_context)
        self.push = DreamePush(self.cloud, self.device, tls, self._push_properties, self._push_state)
        self.cloud.on_token_refresh.append(self.push.update_credentials)
        await self.hass.async_add_executor_job(self.push.start)

    async def async_shutdown(self) -> None:
        if self.push:
            await self.hass.async_add_executor_job(self.push.stop)
            self.push = None
        await super().async_shutdown()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            for dev in await self.cloud.devices():
                if dev.did == self.device.did:
                    self.device = dev
                    break
            data = dict(self.data or {})
            if self.device.online:
                data.update(await self.cloud.get_properties(self.device, POLL_KEYS))
            for key, (value, stamp) in (await self.cloud.reported_properties(self.device, REPORT_KEYS)).items():
                data[key] = value
                self.reported_at[key] = stamp
        except DreameAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DreameError as err:
            raise UpdateFailed(str(err)) from err
        return data

    # Called from the MQTT thread.
    def _push_properties(self, params: list[dict[str, Any]]) -> None:
        self.hass.loop.call_soon_threadsafe(self._apply_push, params)

    def _push_state(self, _connected: bool) -> None:
        self.hass.loop.call_soon_threadsafe(self.async_update_listeners)

    @callback
    def _apply_push(self, params: list[dict[str, Any]]) -> None:
        data = dict(self.data or {})
        for item in params:
            data[f"{item['siid']}.{item['piid']}"] = item.get("value")
        self.async_set_updated_data(data)

    async def async_set_value(self, key: str, value: int) -> None:
        if value not in WRITABLE.get(key, set()):
            raise HomeAssistantError(f"Value {value} is not allowed for {key}")
        try:
            await self.cloud.set_property(self.device, key, value)
        except DreameError as err:
            raise HomeAssistantError(str(err)) from err
        data = dict(self.data or {})
        data[key] = value
        self.async_set_updated_data(data)
