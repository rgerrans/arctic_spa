"""Select platform for Arctic Spa."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PumpStatus
from .coordinator import ArcticSpaCoordinator

_LOGGER = logging.getLogger(__name__)

PUMP_OPTIONS = ["Off", "Low", "High"]
PUMP_STATUS_MAP = {
    "Off": PumpStatus.OFF,
    "Low": PumpStatus.LOW,
    "High": PumpStatus.HIGH,
}
PUMP_REVERSE_MAP = {v: k for k, v in PUMP_STATUS_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Arctic Spa select entities."""
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Only Pump 1 gets a select (it has Off/Low/High)
    # Pumps 2 and 3 only have Off/High, so they use switches
    entities = [
        ArcticSpaPump1Select(coordinator, entry),
    ]
    
    async_add_entities(entities)


class ArcticSpaPump1Select(CoordinatorEntity[ArcticSpaCoordinator], SelectEntity):
    """Pump 1 speed select for Arctic Spa (Off/Low/High)."""

    _attr_has_entity_name = True
    _attr_options = PUMP_OPTIONS
    _attr_icon = "mdi:pump"
    _attr_name = "Pump 1"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the pump select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pump1_select"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }

    @property
    def current_option(self) -> str | None:
        """Return the current pump status."""
        if self.coordinator.data:
            status = self.coordinator.data.pump1
            return PUMP_REVERSE_MAP.get(status, "Off")
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the pump speed."""
        status = PUMP_STATUS_MAP.get(option, PumpStatus.OFF)
        await self.coordinator.async_set_pump(1, status.value)
