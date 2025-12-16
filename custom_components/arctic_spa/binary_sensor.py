"""Binary sensor platform for Arctic Spa."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ArcticSpaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Arctic Spa binary sensors."""
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ArcticSpaHeaterBinarySensor(coordinator, entry),
        ArcticSpaConnectedSensor(coordinator, entry),
        ArcticSpaBoostSensor(coordinator, entry),
        ArcticSpaOnzenSensor(coordinator, entry),
        ArcticSpaEconomySensor(coordinator, entry),
        ArcticSpaErrorBinarySensor(coordinator, entry),
        ArcticSpaAlarmBinarySensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class ArcticSpaBaseBinarySensor(CoordinatorEntity[ArcticSpaCoordinator], BinarySensorEntity):
    """Base binary sensor for Arctic Spa."""

    _attr_has_entity_name = True

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        name: str,
        key: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }


class ArcticSpaHeaterBinarySensor(ArcticSpaBaseBinarySensor):
    """Heater active binary sensor for Arctic Spa."""

    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_icon = "mdi:water-boiler"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the heater sensor."""
        super().__init__(coordinator, entry, "Heater Active", "heater_active")

    @property
    def is_on(self) -> bool | None:
        """Return true if heater is active."""
        if self.coordinator.data:
            return self.coordinator.data.heater_active
        return None


class ArcticSpaConnectedSensor(ArcticSpaBaseBinarySensor):
    """Connected binary sensor for Arctic Spa."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:wifi"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the connected sensor."""
        super().__init__(coordinator, entry, "Connected", "connected")

    @property
    def is_on(self) -> bool | None:
        """Return true if connected to spa."""
        if self.coordinator.data:
            return self.coordinator.data.connected
        return False


class ArcticSpaBoostSensor(ArcticSpaBaseBinarySensor):
    """Boost active binary sensor for Arctic Spa."""

    _attr_icon = "mdi:rocket-launch"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the boost sensor."""
        super().__init__(coordinator, entry, "Boost Active", "boost_active")

    @property
    def is_on(self) -> bool | None:
        """Return true if boost is active."""
        if self.coordinator.data:
            return self.coordinator.data.filter_boost_active
        return None


class ArcticSpaOnzenSensor(ArcticSpaBaseBinarySensor):
    """Onzen active binary sensor for Arctic Spa."""

    _attr_icon = "mdi:water-plus"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Onzen sensor."""
        super().__init__(coordinator, entry, "Onzen Active", "onzen_active")

    @property
    def is_on(self) -> bool | None:
        """Return true if Onzen is active."""
        if self.coordinator.data:
            return self.coordinator.data.onzen
        return None


class ArcticSpaEconomySensor(ArcticSpaBaseBinarySensor):
    """Economy mode binary sensor for Arctic Spa."""

    _attr_icon = "mdi:leaf"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the economy sensor."""
        super().__init__(coordinator, entry, "Economy Mode", "economy_mode")

    @property
    def is_on(self) -> bool | None:
        """Return true if economy mode is active."""
        if self.coordinator.data:
            return self.coordinator.data.economy
        return None


class ArcticSpaErrorBinarySensor(ArcticSpaBaseBinarySensor):
    """Error binary sensor for Arctic Spa."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the error sensor."""
        super().__init__(coordinator, entry, "Error", "has_error")

    @property
    def is_on(self) -> bool | None:
        """Return true if there's an active error."""
        if self.coordinator.data:
            return self.coordinator.data.has_error
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        if self.coordinator.data:
            return {
                "error_code": self.coordinator.data.error,
                "error_message": self.coordinator.data.error_message,
            }
        return {}


class ArcticSpaAlarmBinarySensor(ArcticSpaBaseBinarySensor):
    """Alarm binary sensor for Arctic Spa."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alarm-light"

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
    ) -> None:
        """Initialize the alarm sensor."""
        super().__init__(coordinator, entry, "Alarm", "has_alarm")

    @property
    def is_on(self) -> bool | None:
        """Return true if there's an active alarm."""
        if self.coordinator.data:
            return self.coordinator.data.has_alarm
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        if self.coordinator.data:
            return {
                "alarm_code": self.coordinator.data.alarm,
                "alarm_message": self.coordinator.data.alarm_message,
            }
        return {}
