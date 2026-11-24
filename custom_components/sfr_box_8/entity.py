"""Shared device and power controls for both entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BoxConfigEntry
from .coordinator import BoxCoordinator


class BoxEntity(CoordinatorEntity[BoxCoordinator]):
    """Represent a platform entity on one SFR decoder."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: BoxConfigEntry, platform: str) -> None:
        """Associate the entity with the decoder device."""
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_{platform}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="SFR",
            model="Box 8 TV (STB8)",
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Request that the decoder turn on."""
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Request that the decoder enter standby."""
        await self.coordinator.async_set_power(False)
