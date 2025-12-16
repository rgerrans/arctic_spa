"""Switch platform for Arctic Spa."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PumpStatus
from .coordinator import ArcticSpaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Arctic Spa switches."""
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ArcticSpaLightsSwitch(coordinator, entry),
        ArcticSpaBoostSwitch(coordinator, entry),
        ArcticSpaOnzenSwitch(coordinator, entry),
        ArcticSpaSdsSwitch(coordinator, entry),
        # Pump 2 and 3 - simple on/off (High only)
        ArcticSpaPumpOnOffSwitch(coordinator, entry, 2),
        ArcticSpaPumpOnOffSwitch(coordinator, entry, 3),
        # Blower
        ArcticSpaBlowerSwitch(coordinator, entry, 1),
    ]
    
    async_add_entities(entities)


class ArcticSpaBaseSwitch(CoordinatorEntity[ArcticSpaCoordinator], SwitchEntity):
    """Base switch for Arctic Spa."""

    _attr_has_entity_name = True

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        name: str,
        key: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }


class ArcticSpaLightsSwitch(ArcticSpaBaseSwitch):
    """Lights switch for Arctic Spa."""

    _attr_icon = "mdi:lightbulb"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the lights switch."""
        super().__init__(coordinator, entry, "Lights", "lights")

    @property
    def is_on(self) -> bool | None:
        """Return true if lights are on."""
        if self.coordinator.data:
            return self.coordinator.data.lights
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the lights."""
        await self.coordinator.async_set_lights(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the lights."""
        await self.coordinator.async_set_lights(False)


class ArcticSpaBoostSwitch(ArcticSpaBaseSwitch):
    """Boost switch for Arctic Spa."""

    _attr_icon = "mdi:rocket-launch"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the boost switch."""
        super().__init__(coordinator, entry, "Spa Boost", "boost")

    @property
    def is_on(self) -> bool | None:
        """Return true if boost is active."""
        if self.coordinator.data:
            return self.coordinator.data.filter_boost_active
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on boost."""
        await self.coordinator.async_set_filter_boost(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off boost."""
        await self.coordinator.async_set_filter_boost(False)


class ArcticSpaOnzenSwitch(ArcticSpaBaseSwitch):
    """Onzen switch for Arctic Spa."""

    _attr_icon = "mdi:water-plus"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Onzen switch."""
        super().__init__(coordinator, entry, "Onzen", "onzen_switch")

    @property
    def is_on(self) -> bool | None:
        """Return true if Onzen is active."""
        if self.coordinator.data:
            return self.coordinator.data.onzen
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on Onzen."""
        await self.coordinator.async_set_onzen(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off Onzen."""
        await self.coordinator.async_set_onzen(False)


class ArcticSpaSdsSwitch(ArcticSpaBaseSwitch):
    """SDS (bubbles) switch for Arctic Spa."""

    _attr_icon = "mdi:air-filter"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the SDS switch."""
        super().__init__(coordinator, entry, "Bubbles (SDS)", "sds")

    @property
    def is_on(self) -> bool | None:
        """Return true if SDS is active."""
        if self.coordinator.data:
            return self.coordinator.data.sds
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on SDS."""
        await self.coordinator.async_set_sds(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off SDS."""
        await self.coordinator.async_set_sds(False)


class ArcticSpaPumpOnOffSwitch(ArcticSpaBaseSwitch):
    """Simple on/off pump switch for Arctic Spa (for Pump 2 and 3)."""

    _attr_icon = "mdi:water-pump"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        pump_num: int,
    ) -> None:
        """Initialize the pump switch."""
        self._pump_num = pump_num
        super().__init__(coordinator, entry, f"Pump {pump_num}", f"pump_{pump_num}")

    def _get_pump_status(self) -> PumpStatus:
        """Get current pump status."""
        if not self.coordinator.data:
            return PumpStatus.OFF
        
        status_map = {
            2: self.coordinator.data.pump2,
            3: self.coordinator.data.pump3,
        }
        return status_map.get(self._pump_num, PumpStatus.OFF)

    @property
    def is_on(self) -> bool | None:
        """Return true if pump is on (High)."""
        if not self.coordinator.data:
            return None
        return self._get_pump_status() == PumpStatus.HIGH

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the pump (High speed)."""
        await self.coordinator.async_set_pump(self._pump_num, PumpStatus.HIGH.value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the pump."""
        await self.coordinator.async_set_pump(self._pump_num, PumpStatus.OFF.value)


class ArcticSpaBlowerSwitch(ArcticSpaBaseSwitch):
    """Blower switch for Arctic Spa."""

    _attr_icon = "mdi:fan"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        blower_num: int,
    ) -> None:
        """Initialize the blower switch."""
        self._blower_num = blower_num
        super().__init__(coordinator, entry, f"Blower {blower_num}", f"blower_{blower_num}")

    @property
    def is_on(self) -> bool | None:
        """Return true if blower is on."""
        if not self.coordinator.data:
            return None
        
        status_map = {
            1: self.coordinator.data.blower1,
            2: self.coordinator.data.blower2,
        }
        status = status_map.get(self._blower_num, PumpStatus.OFF)
        return status != PumpStatus.OFF

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the blower."""
        await self.coordinator.async_set_blower(self._blower_num, PumpStatus.HIGH.value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the blower."""
        await self.coordinator.async_set_blower(self._blower_num, PumpStatus.OFF.value)
