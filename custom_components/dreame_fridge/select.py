"""Mode selections."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFridgeConfigEntry
from .const import (
    FLEX_ZONE_OPTIONS,
    KEY_FLEX_ZONE,
    KEY_MODE,
    KEY_NIGHT_VIEW_LEVEL,
    MODE_OPTIONS,
    NIGHT_VIEW_LEVEL_OPTIONS,
)
from .entity import DreameFridgeEntity


@dataclass(frozen=True, kw_only=True)
class DreameSelectDescription(SelectEntityDescription):
    values: dict[int, str]


DESCRIPTIONS = [
    DreameSelectDescription(key=KEY_MODE, translation_key="mode", icon="mdi:fridge-variant", values=MODE_OPTIONS),
    DreameSelectDescription(key=KEY_FLEX_ZONE, translation_key="flex_zone", icon="mdi:tray", values=FLEX_ZONE_OPTIONS),
    DreameSelectDescription(
        key=KEY_NIGHT_VIEW_LEVEL, translation_key="night_view_level", icon="mdi:brightness-6", values=NIGHT_VIEW_LEVEL_OPTIONS
    ),
]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry, add: AddEntitiesCallback) -> None:
    add(DreameSelect(entry.runtime_data, d) for d in DESCRIPTIONS)


class DreameSelect(DreameFridgeEntity, SelectEntity):
    entity_description: DreameSelectDescription

    def __init__(self, coordinator, description: DreameSelectDescription) -> None:
        super().__init__(coordinator, description)
        self._attr_options = list(description.values.values())

    @property
    def current_option(self) -> str | None:
        return self.entity_description.values.get(self.value)

    async def async_select_option(self, option: str) -> None:
        value = next(k for k, v in self.entity_description.values.items() if v == option)
        await self.coordinator.async_set_value(self.entity_description.key, value)
