"""Doors, warnings and status flags."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFridgeConfigEntry
from .const import (
    KEY_CO2_LOW,
    KEY_DOOR,
    KEY_ERROR,
    KEY_ICE_CRUNCH_FULL,
    KEY_ICE_CUBE_FULL,
    KEY_QUIET_TIME,
    KEY_SABBATH,
    KEY_WATER_LOW,
)
from .entity import DreameFridgeEntity


@dataclass(frozen=True, kw_only=True)
class DreameBinaryDescription(BinarySensorEntityDescription):
    source: str
    is_on_fn: Callable[[Any], bool] = bool


DESCRIPTIONS = [
    # 10.1: 0 closed, 1 fridge open, 2 freezer open, 3 both open
    DreameBinaryDescription(
        key="door_fridge", source=KEY_DOOR, translation_key="door_fridge",
        device_class=BinarySensorDeviceClass.DOOR, is_on_fn=lambda v: v in (1, 3),
    ),
    DreameBinaryDescription(
        key="door_freezer", source=KEY_DOOR, translation_key="door_freezer",
        device_class=BinarySensorDeviceClass.DOOR, is_on_fn=lambda v: v in (2, 3),
    ),
    DreameBinaryDescription(key=KEY_ICE_CUBE_FULL, source=KEY_ICE_CUBE_FULL, translation_key="ice_cube_full", icon="mdi:cube"),
    DreameBinaryDescription(key=KEY_ICE_CRUNCH_FULL, source=KEY_ICE_CRUNCH_FULL, translation_key="ice_crunch_full", icon="mdi:grain"),
    DreameBinaryDescription(
        key=KEY_CO2_LOW, source=KEY_CO2_LOW, translation_key="co2_low",
        device_class=BinarySensorDeviceClass.PROBLEM, icon="mdi:gas-cylinder",
    ),
    DreameBinaryDescription(
        key=KEY_WATER_LOW, source=KEY_WATER_LOW, translation_key="water_low",
        device_class=BinarySensorDeviceClass.PROBLEM, icon="mdi:water-alert",
    ),
    DreameBinaryDescription(
        key="problem", source=KEY_ERROR, translation_key="problem", device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    DreameBinaryDescription(
        key=KEY_QUIET_TIME, source=KEY_QUIET_TIME, translation_key="quiet_time",
        icon="mdi:volume-off", entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DreameBinaryDescription(
        key=KEY_SABBATH, source=KEY_SABBATH, translation_key="sabbath_mode",
        icon="mdi:candle", entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    add([DreameBinarySensor(coordinator, d) for d in DESCRIPTIONS] + [DreameCloudPush(coordinator)])


class DreameBinarySensor(DreameFridgeEntity, BinarySensorEntity):
    entity_description: DreameBinaryDescription

    @property
    def value(self) -> Any:
        return (self.coordinator.data or {}).get(self.entity_description.source)

    @property
    def is_on(self) -> bool | None:
        return None if self.value is None else self.entity_description.is_on_fn(self.value)


class DreameCloudPush(DreameFridgeEntity, BinarySensorEntity):
    """Whether the fridge is online and push updates are connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, BinarySensorEntityDescription(key="cloud", translation_key="cloud"))

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self.coordinator.device.online

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        push = self.coordinator.push
        return {"push_connected": bool(push and push.connected)}
