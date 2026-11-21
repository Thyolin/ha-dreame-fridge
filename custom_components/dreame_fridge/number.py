"""Target temperatures."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFridgeConfigEntry
from .const import KEY_FREEZER_TEMP, KEY_FRIDGE_TEMP, WRITABLE
from .entity import DreameFridgeEntity

DESCRIPTIONS = [
    NumberEntityDescription(key=KEY_FRIDGE_TEMP, translation_key="fridge_temperature", icon="mdi:fridge-top"),
    NumberEntityDescription(key=KEY_FREEZER_TEMP, translation_key="freezer_temperature", icon="mdi:snowflake"),
]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry, add: AddEntitiesCallback) -> None:
    add(DreameNumber(entry.runtime_data, d) for d in DESCRIPTIONS)


class DreameNumber(DreameFridgeEntity, NumberEntity):
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, description) -> None:
        super().__init__(coordinator, description)
        allowed = WRITABLE[description.key]
        self._attr_native_min_value = min(allowed)
        self._attr_native_max_value = max(allowed)

    @property
    def native_value(self) -> float | None:
        return self.value

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_value(self.entity_description.key, int(round(value)))
