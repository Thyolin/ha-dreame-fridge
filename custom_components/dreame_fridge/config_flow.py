"""Config flow: Dreamehome account login and fridge selection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .api import DreameAuthError, DreameCloud, DreameDevice, DreameError
from .const import CONF_COUNTRY, CONF_DEVICE_ID, COUNTRIES, DOMAIN


def _is_fridge(device: DreameDevice) -> bool:
    return ".fridge." in device.model


class DreameFridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._login: dict[str, Any] = {}
        self._fridges: list[DreameDevice] = []

    async def _fetch(self, data: Mapping[str, Any]) -> tuple[list[DreameDevice], str | None]:
        cloud = DreameCloud(async_get_clientsession(self.hass), data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_COUNTRY])
        try:
            return [d for d in await cloud.devices() if _is_fridge(d)], None
        except DreameAuthError:
            return [], "invalid_auth"
        except DreameError:
            return [], "cannot_connect"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._fridges, error = await self._fetch(user_input)
            if error:
                errors["base"] = error
            elif not self._fridges:
                errors["base"] = "no_fridge"
            else:
                self._login = user_input
                if len(self._fridges) == 1:
                    return await self._create(self._fridges[0])
                return await self.async_step_device()
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_COUNTRY, default=(user_input or {}).get(CONF_COUNTRY, "eu")): SelectSelector(
                    SelectSelectorConfig(options=COUNTRIES, mode=SelectSelectorMode.DROPDOWN, translation_key="country")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self._create(next(d for d in self._fridges if d.did == user_input[CONF_DEVICE_ID]))
        options = {d.did: f"{d.name or d.model} ({d.model})" for d in self._fridges}
        return self.async_show_form(step_id="device", data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)}))

    async def _create(self, device: DreameDevice) -> ConfigFlowResult:
        await self.async_set_unique_id(device.did)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=device.name or "Dreame Fridge", data={**self._login, CONF_DEVICE_ID: device.did}
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            _, error = await self._fetch(data)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )
