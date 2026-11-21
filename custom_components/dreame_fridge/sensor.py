"""Error code and water dispensing reports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFridgeConfigEntry
from .const import ERROR_OPTIONS, KEY_CARBONATION, KEY_ERROR, KEY_SPARKLING_WATER, KEY_STILL_WATER
from .entity import DreameFridgeEntity

REPORTS = [
    SensorEntityDescription(
        key=KEY_STILL_WATER, translation_key="last_still_water", icon="mdi:cup-water",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    SensorEntityDescription(
        key=KEY_SPARKLING_WATER, translation_key="last_sparkling_water", icon="mdi:glass-cocktail",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    SensorEntityDescription(
        key=KEY_CARBONATION, translation_key="carbonation_cycles", icon="mdi:gas-cylinder",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFridgeConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    add([DreameErrorSensor(coordinator)] + [DreameReportSensor(coordinator, d) for d in REPORTS])


class DreameErrorSensor(DreameFridgeEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(ERROR_OPTIONS.values())

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, SensorEntityDescription(key=KEY_ERROR, translation_key="error", icon="mdi:alert-circle-outline"))

    @property
    def native_value(self) -> str | None:
        return ERROR_OPTIONS.get(self.value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"code": self.value}


class DreameReportSensor(DreameFridgeEntity, SensorEntity):
    """Value the fridge reported after the last event (e.g. seconds of water dispensed)."""

    @property
    def available(self) -> bool:
        # Reported values come from the cloud cache, also while the fridge is offline.
        return self.coordinator.last_update_success and self.value is not None

    @property
    def native_value(self) -> int | None:
        return self.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stamp = self.coordinator.reported_at.get(self.entity_description.key)
        return {"reported_at": datetime.fromtimestamp(stamp, UTC).isoformat() if stamp else None}
