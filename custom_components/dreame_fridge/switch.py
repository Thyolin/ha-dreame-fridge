"""On/off settings."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFridgeConfigEntry
from .const import KEY_ALWAYS_FRESH, KEY_AUTOFILL, KEY_ICE_CRUNCH, KEY_ICE_CUBE, KEY_NIGHT_VIEW, KEY_SPARKLING
from .entity import DreameFridgeEntity

DESCRIPTIONS = [
    SwitchEntityDescription(key=KEY_ICE_CUBE, translation_key="ice_cube", icon="mdi:cube-outline"),
    SwitchEntityDescription(key=KEY_ICE_CRUNCH, translation_key="ice_crunch", icon="mdi:grain"),
    SwitchEntityDescription(key=KEY_SPARKLING, translation_key="sparkling", icon="mdi:cup-water"),
    SwitchEntityDescription(key=KEY_ALWAYS_FRESH, translation_key="always_fresh", icon="mdi:water-sync"),
    SwitchEntityDescription(key=KEY_AUTOFILL, translation_key="autofill", icon="mdi:water-plus"),
    SwitchEntityDescription(key=KEY_NIGHT_VIEW, translation_key="night_view", icon="mdi:lightbulb-night"),
]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry, add: AddEntitiesCallback) -> None:
    add(DreameSwitch(entry.runtime_data, d) for d in DESCRIPTIONS)


class DreameSwitch(DreameFridgeEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        return None if self.value is None else bool(self.value)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_value(self.entity_description.key, 1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_value(self.entity_description.key, 0)
