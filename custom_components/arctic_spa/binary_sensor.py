"""Binary sensor platform for Arctic Spa."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    add: list[BinarySensorEntity] = [
        _Bool(coordinator, entry, "Heater Active", "heater_active",
              lambda d: d.heater_active, BinarySensorDeviceClass.HEAT, "mdi:water-boiler"),
        _Bool(coordinator, entry, "Connected", "connected",
              lambda d: d.connected, BinarySensorDeviceClass.CONNECTIVITY, "mdi:wifi"),
        _Bool(coordinator, entry, "Boost Active", "boost_active",
              lambda d: d.filter_boost_active, None, "mdi:rocket-launch"),
        _Bool(coordinator, entry, "Onzen Active", "onzen_active",
              lambda d: d.onzen, None, "mdi:water-plus"),
        _Bool(coordinator, entry, "Economy Mode", "economy_mode",
              lambda d: d.economy, None, "mdi:leaf"),
        _Bool(coordinator, entry, "Ozone Active", "ozone_active",
              lambda d: d.ozone, None, "mdi:weather-cloudy"),
        _Bool(coordinator, entry, "Fan Active", "fan_active",
              lambda d: d.fan, None, "mdi:fan"),
        _Bool(coordinator, entry, "Fogger Active", "fogger_active",
              lambda d: d.fogger, None, "mdi:weather-fog"),
        _Bool(coordinator, entry, "Bubbles (SDS) Active", "sds_active",
              lambda d: d.sds, None, "mdi:chart-bubble"),
        _Bool(coordinator, entry, "YESS Active", "yess_active",
              lambda d: d.yess, None, "mdi:flower"),
        _Bool(coordinator, entry, "All On", "all_on",
              lambda d: d.all_on, None, "mdi:power-on"),
        _Bool(coordinator, entry, "SpaBoy Producing", "spaboy_producing",
              lambda d: d.sb_producing, None, "mdi:test-tube"),
        _Bool(coordinator, entry, "SpaBoy Boost Active", "spaboy_boost_active",
              lambda d: d.sb_boost, None, "mdi:rocket"),
        _Bool(coordinator, entry, "Filter 1 Present", "filter_1_present",
              lambda d: d.filter_tag1, None, "mdi:air-filter"),
        _Bool(coordinator, entry, "Filter 2 Present", "filter_2_present",
              lambda d: d.filter_tag2, None, "mdi:air-filter"),
        _ErrorBool(coordinator, entry),
        _AlarmBool(coordinator, entry),
    ]
    # Per-pump and per-blower running indicators (5 pumps + 2 blowers; gated by cfg).
    for i in range(1, 6):
        add.append(_PumpRunning(coordinator, entry, i))
    for i in range(1, 3):
        add.append(_BlowerRunning(coordinator, entry, i))
    async_add_entities(add)


class _BaseBin(CoordinatorEntity[ArcticSpaCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, key) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }


class _Bool(_BaseBin):
    def __init__(self, coordinator, entry, name, key, getter, device_class, icon) -> None:
        super().__init__(coordinator, entry, name, key)
        self._getter = getter
        if device_class:
            self._attr_device_class = device_class
        if icon:
            self._attr_icon = icon

    @property
    def is_on(self):
        return self._getter(self.coordinator.data) if self.coordinator.data else None


class _ErrorBool(_BaseBin):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Error", "has_error")

    @property
    def is_on(self):
        return self.coordinator.data.has_error if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "active_codes": list(self.coordinator.data.active_errors),
            "error_message": self.coordinator.data.error_message,
        }


class _AlarmBool(_BaseBin):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alarm-light"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Alarm", "has_alarm")

    @property
    def is_on(self):
        return self.coordinator.data.has_alarm if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "active_codes": list(self.coordinator.data.active_statuses),
            "alarm_message": self.coordinator.data.alarm_message,
        }


class _PumpRunning(_BaseBin):
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator, entry, num: int) -> None:
        self._num = num
        super().__init__(coordinator, entry, f"Pump {num} Running", f"pump_{num}_running")

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        return getattr(self.coordinator.data, f"pump{self._num}") != PumpStatus.OFF

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_pump[self._num - 1])


class _BlowerRunning(_BaseBin):
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, entry, num: int) -> None:
        self._num = num
        super().__init__(coordinator, entry, f"Blower {num} Running", f"blower_{num}_running")

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        return getattr(self.coordinator.data, f"blower{self._num}") != PumpStatus.OFF

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_blower[self._num - 1])
