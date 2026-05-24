"""Number platform for Arctic Spa (filter freq/dur, chlorine/pH bands)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ArcticSpaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        _FilterFrequency(coordinator, entry),
        _FilterDuration(coordinator, entry),
        _ChlorineTarget(coordinator, entry),
        _PhTarget(coordinator, entry),
        _SpaBoyHours(coordinator, entry),
    ])


class _BaseNumber(CoordinatorEntity[ArcticSpaCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, name, key) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info


class _FilterFrequency(_BaseNumber):
    _attr_icon = "mdi:calendar-clock"
    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "cycles/day"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Filter Frequency", "filter_frequency")

    @property
    def native_value(self):
        if self.coordinator.data and self.coordinator.data.filter_frequency:
            return self.coordinator.data.filter_frequency
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_filter_frequency(int(value))


class _FilterDuration(_BaseNumber):
    _attr_icon = "mdi:timer-sand"
    _attr_native_min_value = 0.5
    _attr_native_max_value = 8.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Filter Duration", "filter_duration")

    @property
    def native_value(self):
        if self.coordinator.data and self.coordinator.data.filter_duration:
            return self.coordinator.data.filter_duration
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_filter_duration(int(value))


class _ChlorineTarget(_BaseNumber):
    _attr_icon = "mdi:molecule"
    _attr_native_min_value = 400
    _attr_native_max_value = 800
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "mV"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Chlorine Target (ORP)", "chlorine_target")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        hi = self.coordinator.data.sb_orp_hi
        lo = self.coordinator.data.sb_orp_lo
        if hi > 0 and lo > 0:
            return (hi + lo) // 2
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_chlorine_band(int(value), band=5)


class _PhTarget(_BaseNumber):
    _attr_icon = "mdi:ph"
    _attr_native_min_value = 7.0
    _attr_native_max_value = 7.8
    _attr_native_step = 0.1
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pH Target", "ph_target")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        hi = self.coordinator.data.sb_ph_hi
        lo = self.coordinator.data.sb_ph_lo
        if hi > 0 and lo > 0:
            return round(((hi + lo) // 2) / 100.0, 2)
        return None

    async def async_set_native_value(self, value: float) -> None:
        # Stored as int x100 on the spa.
        await self.coordinator.async_set_ph_band(int(round(value * 100)), band=5)


class _SpaBoyHours(_BaseNumber):
    _attr_icon = "mdi:timer-cog"
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h/day"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "SpaBoy Hours / Day", "spaboy_hours")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.spaboy_hours_per_day or None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_spaboy_hours(int(value))
