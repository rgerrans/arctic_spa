"""Sensor platform for Arctic Spa."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_TEMP_UNIT,
    DEFAULT_TEMP_UNIT,
    DOMAIN,
    FilterStatus,
    HeaterStatus,
    SB_ORP_BAND_LABELS,
    SB_PH_BAND_LABELS,
    SMARTPH_LABELS,
)
from .coordinator import ArcticSpaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    temp_unit = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)

    entities: list[SensorEntity] = [
        _Temp(coordinator, entry, temp_unit, "Water Temperature", "temperature",
              lambda d: d.temperature_f),
        _Temp(coordinator, entry, temp_unit, "Target Temperature", "setpoint",
              lambda d: d.setpoint_f),
        _Temp(coordinator, entry, temp_unit, "Heater Temperature", "heater_temperature",
              lambda d: d.heater_temp),
        _Status(coordinator, entry, "Heater 1 Status", "heater_status", _HEATER_MAP,
                lambda d: d.heater1, icon="mdi:water-boiler"),
        _Status(coordinator, entry, "Heater 2 Status", "heater2_status", _HEATER_MAP,
                lambda d: d.heater2, icon="mdi:water-boiler"),
        _Status(coordinator, entry, "Filter Status", "filter_status", _FILTER_MAP,
                lambda d: d.filter_status, icon="mdi:air-filter"),
        _Numeric(coordinator, entry, "pH Level", "ph", "mdi:ph",
                 lambda d: (d.sb_ph / 100.0) if d.sb_ph > 0 else None,
                 state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "ORP (Chlorine)", "orp", "mdi:molecule",
                 lambda d: d.sb_orp if d.sb_orp > 0 else None,
                 unit="mV", state_class=SensorStateClass.MEASUREMENT),
        _PhStatus(coordinator, entry),
        _OrpStatus(coordinator, entry),
        _Error(coordinator, entry),
        _Alarm(coordinator, entry),
        _Power(coordinator, entry),
        _EnergyCumulative(coordinator, entry),
        _Numeric(coordinator, entry, "Current Draw", "current_draw", "mdi:current-ac",
                 lambda d: d.current_draw or None, unit="A",
                 state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "Filter Run Hours / Day", "filter_run_hours_per_day",
                 "mdi:timer-outline",
                 lambda d: d.filter_run_hours_per_day or None, unit="h"),
        _SmartPhState(coordinator, entry),
        _SpaBoyStateMachine(coordinator, entry),
    ]

    # SpaBoy chlorinator sensors (registered always; show unavailable if absent)
    entities += [
        _Temp(coordinator, entry, temp_unit, "SpaBoy Cell Temperature", "spaboy_temperature",
              lambda d: d.sb_temp_f if d.sb_present else None),
        _Numeric(coordinator, entry, "SpaBoy Voltage In", "spaboy_voltage_in", "mdi:flash",
                 lambda d: d.sb_voltage_in if d.sb_present else None,
                 unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE,
                 state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "SpaBoy Voltage Out", "spaboy_voltage_out", "mdi:flash",
                 lambda d: d.sb_voltage_out if d.sb_present else None,
                 unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE,
                 state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "SpaBoy Cell Current 1", "spaboy_current_1", "mdi:current-dc",
                 lambda d: d.sb_current_1 if d.sb_present else None,
                 unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT,
                 state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "SpaBoy Cell Current 2", "spaboy_current_2", "mdi:current-dc",
                 lambda d: d.sb_current_2 if d.sb_present else None,
                 unit=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT,
                 state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "SpaBoy Cell Wear", "spaboy_wear", "mdi:battery-50",
                 lambda d: d.sb_wear_pct if d.sb_present else None,
                 unit=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
        _Numeric(coordinator, entry, "SpaBoy Status Code", "spaboy_status_code", "mdi:numeric",
                 lambda d: d.sb_status if d.sb_present else None),
    ]

    # Info sensors
    entities += [
        _Info(coordinator, entry, "Spa Serial Number", "spa_serial",
              lambda d: d.spa_serial or None, "mdi:identifier"),
        _Info(coordinator, entry, "Spa Firmware (YOC)", "fw_yoc",
              lambda d: d.fw_yoc or None, "mdi:chip"),
        _Info(coordinator, entry, "Spa Firmware (LPC)", "fw_lpc",
              lambda d: d.fw_lpc or None, "mdi:chip"),
        _Info(coordinator, entry, "Spa Firmware (SpaBoy)", "fw_spaboy",
              lambda d: d.fw_sb or None, "mdi:chip"),
    ]

    async_add_entities(entities)


_HEATER_MAP = {
    HeaterStatus.IDLE: "Idle",
    HeaterStatus.WARMUP: "Warming Up",
    HeaterStatus.HEATING: "Heating",
    HeaterStatus.COOLDOWN: "Cooling Down",
}
_FILTER_MAP = {
    FilterStatus.IDLE: "Idle",
    FilterStatus.PURGE: "Purging",
    FilterStatus.FILTERING: "Filtering",
    FilterStatus.SUSPENDED: "Suspended",
    FilterStatus.OVERTEMPERATURE: "Over Temperature",
    FilterStatus.RESUMING: "Resuming",
    FilterStatus.BOOST: "Boost",
    FilterStatus.SANITIZE: "Sanitizing",
}


class _Base(CoordinatorEntity[ArcticSpaCoordinator], SensorEntity):
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


class _Temp(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, temp_unit, name, key, getter_f) -> None:
        super().__init__(coordinator, entry, name, key)
        self._getter_f = getter_f
        self._temp_unit = temp_unit
        self._attr_native_unit_of_measurement = (
            UnitOfTemperature.CELSIUS if temp_unit == "C" else UnitOfTemperature.FAHRENHEIT
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        val_f = self._getter_f(self.coordinator.data)
        if val_f is None or val_f == 0:
            return None
        if self._temp_unit == "C":
            return round(((val_f - 32) * 5 / 9) * 2) / 2
        return val_f


class _Status(_Base):
    def __init__(self, coordinator, entry, name, key, label_map, getter, icon=None) -> None:
        super().__init__(coordinator, entry, name, key)
        self._label_map = label_map
        self._getter = getter
        if icon:
            self._attr_icon = icon

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self._label_map.get(self._getter(self.coordinator.data), "Unknown")


class _Numeric(_Base):
    def __init__(self, coordinator, entry, name, key, icon, getter,
                 unit=None, device_class=None, state_class=None) -> None:
        super().__init__(coordinator, entry, name, key)
        self._getter = getter
        self._attr_icon = icon
        if unit:
            self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = device_class
        if state_class:
            self._attr_state_class = state_class

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self._getter(self.coordinator.data)


class _Info(_Base):
    def __init__(self, coordinator, entry, name, key, getter, icon) -> None:
        super().__init__(coordinator, entry, name, key)
        self._getter = getter
        self._attr_icon = icon
        self._attr_entity_category = "diagnostic"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self._getter(self.coordinator.data)


class _PhStatus(_Base):
    """pH status using firmware's sbpHind banding (0-4) per Customer Portal."""

    _attr_icon = "mdi:test-tube"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pH Status", "ph_status")

    @property
    def native_value(self):
        if not self.coordinator.data or self.coordinator.data.sb_ph <= 0:
            return None
        # Clamp index to 4 since firmware sometimes returns >4 (treat as upper extreme)
        idx = min(max(self.coordinator.data.sb_ph_indicator, 0), 4)
        return SB_PH_BAND_LABELS.get(idx, f"Band {idx}")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "indicator": self.coordinator.data.sb_ph_indicator,
            "ph": round(self.coordinator.data.sb_ph / 100.0, 2) if self.coordinator.data.sb_ph else None,
        }


class _OrpStatus(_Base):
    """Chlorine ORP status using firmware's sbORPind banding (0-4) per Customer Portal."""

    _attr_icon = "mdi:test-tube"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "ORP Status", "orp_status")

    @property
    def native_value(self):
        if not self.coordinator.data or self.coordinator.data.sb_orp <= 0:
            return None
        idx = min(max(self.coordinator.data.sb_orp_indicator, 0), 4)
        return SB_ORP_BAND_LABELS.get(idx, f"Band {idx}")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "indicator": self.coordinator.data.sb_orp_indicator,
            "orp_mV": self.coordinator.data.sb_orp,
        }


class _Error(_Base):
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Error", "error")

    @property
    def native_value(self):
        return self.coordinator.data.error_message if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "active_codes": list(self.coordinator.data.active_errors),
            "count": len(self.coordinator.data.active_errors),
        }


class _Alarm(_Base):
    _attr_icon = "mdi:alarm-light"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Alarm", "alarm")

    @property
    def native_value(self):
        return self.coordinator.data.alarm_message if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "active_codes": list(self.coordinator.data.active_statuses),
            "count": len(self.coordinator.data.active_statuses),
        }


class _SmartPhState(_Base):
    _attr_icon = "mdi:state-machine"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "SmartPH State", "smartph_state")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.smartph_state_label

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {"state_id": self.coordinator.data.smartph_state}


class _SpaBoyStateMachine(_Base):
    _attr_icon = "mdi:state-machine"
    _attr_entity_category = "diagnostic"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "SpaBoy State", "spaboy_state_machine")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.spaboy_state_machine


class _Power(_Base):
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Power", "power")

    @property
    def native_value(self):
        return self.coordinator.data.estimated_power_watts if self.coordinator.data else None


class _EnergyCumulative(CoordinatorEntity[ArcticSpaCoordinator], RestoreEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:lightning-bolt-circle"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_energy"
        self._attr_name = "Energy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }
        self._restored: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", None):
            try:
                self._restored = float(last.state)
                # Raise the live counter to at least the restored value so the
                # next push doesn't produce an apparent counter-reset (which
                # poisons HA's TOTAL_INCREASING + Energy dashboard math).
                if self.coordinator.client.status:
                    self.coordinator.client.status.energy_kwh = max(
                        self.coordinator.client.status.energy_kwh, self._restored
                    )
                # Flush restored value to HA state immediately so the first
                # coordinator push doesn't publish a stale 0.
                self.async_write_ha_state()
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self):
        # Floor at the restored value — TOTAL_INCREASING semantics require the
        # reported value to monotonically increase across restarts. If the
        # live counter is briefly less than restored (e.g. async_added_to_hass
        # hasn't applied the restore to client.status yet), return restored.
        live = self.coordinator.data.energy_kwh if self.coordinator.data else 0.0
        base = self._restored or 0.0
        return round(max(live, base), 3)
