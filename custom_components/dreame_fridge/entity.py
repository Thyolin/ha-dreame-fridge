"""Base entity."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DreameFridgeCoordinator


class DreameFridgeEntity(CoordinatorEntity[DreameFridgeCoordinator]):
    """Entity bound to one property key of the fridge."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DreameFridgeCoordinator, description: EntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        device = coordinator.device
        self._attr_unique_id = f"{device.did}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.did)},
            connections={(CONNECTION_NETWORK_MAC, device.mac.lower())} if device.mac else set(),
            manufacturer="Dreame",
            model=device.model,
            name=device.name or "Dreame Fridge",
            sw_version=device.firmware,
        )

    @property
    def value(self) -> Any:
        return (self.coordinator.data or {}).get(self.entity_description.key)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.device.online and self.value is not None
