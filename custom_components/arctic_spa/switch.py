"""Switch platform for Arctic Spa (on/off accessories)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PumpStatus
from .coordinator import ArcticSpaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [
        _LightsSwitch(coordinator, entry),
        _FilterBoostSwitch(coordinator, entry),
        _SpaBoyBoostSwitch(coordinator, entry),
        _OnzenSwitch(coordinator, entry),
        _SdsSwitch(coordinator, entry),
        _YessSwitch(coordinator, entry),
        _FoggerSwitch(coordinator, entry),
        _StopFilterAboveSwitch(coordinator, entry),
    ]
    # Pumps 2-5 are single-speed (off/high) per Arctic Spa hardware convention.
    # Pump 1 is the 3-speed circulation pump — controlled via select.pump_1_speed.
    for i in range(2, 6):
        entities.append(_PumpOnOff(coordinator, entry, i))
    # Blowers 1-2
    for i in range(1, 3):
        entities.append(_BlowerOnOff(coordinator, entry, i))
    async_add_entities(entities)


class _BaseSwitch(CoordinatorEntity[ArcticSpaCoordinator], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, key) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info


class _LightsSwitch(_BaseSwitch):
    _attr_icon = "mdi:lightbulb"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Cabinet Lights", "lights")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_lights)

    @property
    def is_on(self):
        return self.coordinator.data.lights if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_lights(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_lights(False)


class _FilterBoostSwitch(_BaseSwitch):
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Filter Boost", "boost")

    @property
    def is_on(self):
        return self.coordinator.data.filter_boost_active if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_filter_boost(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_filter_boost(False)


class _SpaBoyBoostSwitch(_BaseSwitch):
    _attr_icon = "mdi:rocket"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "SpaBoy Boost", "spaboy_boost")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def is_on(self):
        return self.coordinator.data.sb_boost if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_spaboy_boost(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_spaboy_boost(False)


class _OnzenSwitch(_BaseSwitch):
    _attr_icon = "mdi:water-plus"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Onzen", "onzen_switch")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_onzen)

    @property
    def is_on(self):
        return self.coordinator.data.onzen if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_onzen(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_onzen(False)


class _SdsSwitch(_BaseSwitch):
    _attr_icon = "mdi:chart-bubble"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Bubbles (SDS)", "sds")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_sds)

    @property
    def is_on(self):
        return self.coordinator.data.sds if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_sds(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_sds(False)


class _YessSwitch(_BaseSwitch):
    _attr_icon = "mdi:flower"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "YESS", "yess")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_yess)

    @property
    def is_on(self):
        return self.coordinator.data.yess if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_yess(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_yess(False)


class _FoggerSwitch(_BaseSwitch):
    _attr_icon = "mdi:weather-fog"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Fogger", "fogger")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_fogger)

    @property
    def is_on(self):
        return self.coordinator.data.fogger if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_fogger(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_fogger(False)


class _PumpOnOff(_BaseSwitch):
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator, entry, pump_num: int) -> None:
        self._num = pump_num
        super().__init__(coordinator, entry, f"Pump {pump_num}", f"pump_{pump_num}")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_pump[self._num - 1])

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        return getattr(self.coordinator.data, f"pump{self._num}") == PumpStatus.HIGH

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_pump(self._num, PumpStatus.HIGH.value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_pump(self._num, PumpStatus.OFF.value)


class _StopFilterAboveSwitch(_BaseSwitch):
    _attr_icon = "mdi:thermometer-off"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Stop Filter Above Setpoint+3°", "stop_filter_above")

    @property
    def is_on(self):
        return self.coordinator.data.filter_stop_above_3 if self.coordinator.data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_stop_filter_above(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_stop_filter_above(False)


class _BlowerOnOff(_BaseSwitch):
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, entry, blower_num: int) -> None:
        self._num = blower_num
        super().__init__(coordinator, entry, f"Blower {blower_num}", f"blower_{blower_num}")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_blower[self._num - 1])

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        return getattr(self.coordinator.data, f"blower{self._num}") != PumpStatus.OFF

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_blower(self._num, PumpStatus.HIGH.value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_blower(self._num, PumpStatus.OFF.value)
