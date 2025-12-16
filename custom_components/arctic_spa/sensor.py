"""Sensor platform for Arctic Spa."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT, HeaterStatus, FilterStatus
from .coordinator import ArcticSpaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Arctic Spa sensors."""
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    temp_unit = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)
    
    entities = [
        ArcticSpaTemperatureSensor(coordinator, entry, temp_unit),
        ArcticSpaSetpointSensor(coordinator, entry, temp_unit),
        ArcticSpaHeaterSensor(coordinator, entry),
        ArcticSpaFilterSensor(coordinator, entry),
        ArcticSpaPhSensor(coordinator, entry),
        ArcticSpaOrpSensor(coordinator, entry),
        ArcticSpaPhStatusSensor(coordinator, entry),
        ArcticSpaOrpStatusSensor(coordinator, entry),
        ArcticSpaErrorSensor(coordinator, entry),
        ArcticSpaAlarmSensor(coordinator, entry),
        ArcticSpaPowerSensor(coordinator, entry),
        ArcticSpaEnergySensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class ArcticSpaBaseSensor(CoordinatorEntity[ArcticSpaCoordinator], SensorEntity):
    """Base sensor for Arctic Spa."""

    _attr_has_entity_name = True

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        name: str,
        key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }


class ArcticSpaTemperatureSensor(ArcticSpaBaseSensor):
    """Temperature sensor for Arctic Spa."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        temp_unit: str,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, entry, "Water Temperature", "temperature")
        self._temp_unit = temp_unit
        if temp_unit == "C":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        else:
            self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        if self.coordinator.data:
            if self._temp_unit == "C":
                return self.coordinator.data.temperature_c
            return self.coordinator.data.temperature_f
        return None


class ArcticSpaSetpointSensor(ArcticSpaBaseSensor):
    """Setpoint sensor for Arctic Spa."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        temp_unit: str,
    ) -> None:
        """Initialize the setpoint sensor."""
        super().__init__(coordinator, entry, "Target Temperature", "setpoint")
        self._temp_unit = temp_unit
        if temp_unit == "C":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        else:
            self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    @property
    def native_value(self) -> float | None:
        """Return the setpoint temperature."""
        if self.coordinator.data:
            if self._temp_unit == "C":
                return self.coordinator.data.setpoint_c
            return self.coordinator.data.setpoint_f
        return None


class ArcticSpaHeaterSensor(ArcticSpaBaseSensor):
    """Heater status sensor for Arctic Spa."""

    _attr_icon = "mdi:water-boiler"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the heater sensor."""
        super().__init__(coordinator, entry, "Heater Status", "heater_status")

    @property
    def native_value(self) -> str | None:
        """Return the heater status."""
        if self.coordinator.data:
            status_map = {
                HeaterStatus.IDLE: "Idle",
                HeaterStatus.WARMUP: "Warming Up",
                HeaterStatus.HEATING: "Heating",
                HeaterStatus.COOLDOWN: "Cooling Down",
            }
            return status_map.get(self.coordinator.data.heater1, "Unknown")
        return None


class ArcticSpaFilterSensor(ArcticSpaBaseSensor):
    """Filter status sensor for Arctic Spa."""

    _attr_icon = "mdi:air-filter"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the filter sensor."""
        super().__init__(coordinator, entry, "Filter Status", "filter_status")

    @property
    def native_value(self) -> str | None:
        """Return the filter status."""
        if self.coordinator.data:
            status_map = {
                FilterStatus.IDLE: "Idle",
                FilterStatus.PURGE: "Purging",
                FilterStatus.FILTERING: "Filtering",
                FilterStatus.SUSPENDED: "Suspended",
                FilterStatus.OVERTEMPERATURE: "Over Temperature",
                FilterStatus.RESUMING: "Resuming",
                FilterStatus.BOOST: "Boost",
                FilterStatus.SANITIZE: "Sanitizing",
            }
            return status_map.get(self.coordinator.data.filter_status, "Unknown")
        return None


class ArcticSpaPhSensor(ArcticSpaBaseSensor):
    """pH sensor for Arctic Spa."""

    _attr_icon = "mdi:ph"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the pH sensor."""
        super().__init__(coordinator, entry, "pH Level", "ph")

    @property
    def native_value(self) -> float | None:
        """Return the pH level."""
        if self.coordinator.data and self.coordinator.data.ph > 0:
            # SpaBoy reports pH as integer * 100 (e.g., 720 = 7.20)
            return self.coordinator.data.ph / 100.0
        return None


class ArcticSpaOrpSensor(ArcticSpaBaseSensor):
    """ORP (Chlorine) sensor for Arctic Spa."""

    _attr_icon = "mdi:molecule"
    _attr_native_unit_of_measurement = "mV"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the ORP sensor."""
        super().__init__(coordinator, entry, "ORP (Chlorine)", "orp")

    @property
    def native_value(self) -> int | None:
        """Return the ORP level."""
        if self.coordinator.data and self.coordinator.data.orp > 0:
            return self.coordinator.data.orp
        return None


class ArcticSpaPhStatusSensor(ArcticSpaBaseSensor):
    """pH status sensor for Arctic Spa."""

    _attr_icon = "mdi:test-tube"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the pH status sensor."""
        super().__init__(coordinator, entry, "pH Status", "ph_status")

    @property
    def native_value(self) -> str | None:
        """Return the pH status."""
        if self.coordinator.data and self.coordinator.data.ph > 0:
            ph = self.coordinator.data.ph / 100.0
            if ph < 7.2:
                return "Low"
            elif ph > 7.8:
                return "High"
            else:
                return "OK"
        return None


class ArcticSpaOrpStatusSensor(ArcticSpaBaseSensor):
    """ORP status sensor for Arctic Spa."""

    _attr_icon = "mdi:test-tube"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the ORP status sensor."""
        super().__init__(coordinator, entry, "ORP Status", "orp_status")

    @property
    def native_value(self) -> str | None:
        """Return the ORP status."""
        if self.coordinator.data and self.coordinator.data.orp > 0:
            orp = self.coordinator.data.orp
            if orp < 500:
                return "Low"
            elif orp > 750:
                return "High"
            else:
                return "OK"
        return None


class ArcticSpaErrorSensor(ArcticSpaBaseSensor):
    """Error sensor for Arctic Spa."""

    _attr_icon = "mdi:alert-circle"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the error sensor."""
        super().__init__(coordinator, entry, "Error", "error")

    @property
    def native_value(self) -> str | None:
        """Return the error message."""
        if self.coordinator.data:
            return self.coordinator.data.error_message
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        if self.coordinator.data:
            return {"error_code": self.coordinator.data.error}
        return {}


class ArcticSpaAlarmSensor(ArcticSpaBaseSensor):
    """Alarm sensor for Arctic Spa."""

    _attr_icon = "mdi:alarm-light"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the alarm sensor."""
        super().__init__(coordinator, entry, "Alarm", "alarm")

    @property
    def native_value(self) -> str | None:
        """Return the alarm message."""
        if self.coordinator.data:
            return self.coordinator.data.alarm_message
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        if self.coordinator.data:
            return {"alarm_code": self.coordinator.data.alarm}
        return {}


class ArcticSpaPowerSensor(ArcticSpaBaseSensor):
    """Estimated power consumption sensor for Arctic Spa."""

    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = "W"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator, entry, "Power", "power")

    @property
    def native_value(self) -> int | None:
        """Return the estimated power consumption."""
        if self.coordinator.data:
            return self.coordinator.data.estimated_power_watts
        return None


class ArcticSpaEnergySensor(CoordinatorEntity[ArcticSpaCoordinator], RestoreEntity, SensorEntity):
    """Cumulative energy consumption sensor for Arctic Spa with persistence."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:lightning-bolt-circle"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_energy"
        self._attr_name = "Energy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }
        self._restored_energy: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last state when added to hass."""
        await super().async_added_to_hass()
        
        # Try to restore the last known energy value
        last_state = await self.async_get_last_state()
        
        if last_state and last_state.state not in ("unknown", "unavailable", None):
            try:
                restored_value = float(last_state.state)
                self._restored_energy = restored_value
                # Set the restored value in the client's status
                if self.coordinator.client.status:
                    self.coordinator.client.status.energy_kwh = restored_value
                _LOGGER.info("Restored energy value: %.3f kWh", restored_value)
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Could not restore energy state: %s", err)

    @property
    def native_value(self) -> float | None:
        """Return the cumulative energy consumption in kWh."""
        if self.coordinator.data:
            return round(self.coordinator.data.energy_kwh, 3)
        return self._restored_energy
