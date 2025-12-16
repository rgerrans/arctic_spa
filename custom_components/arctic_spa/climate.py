"""Climate platform for Arctic Spa."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT
from .coordinator import ArcticSpaCoordinator

_LOGGER = logging.getLogger(__name__)

# Temperature limits
MIN_TEMP_C = 26
MAX_TEMP_C = 40
MIN_TEMP_F = 80
MAX_TEMP_F = 104


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Arctic Spa climate entity."""
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    temp_unit = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)
    
    async_add_entities([ArcticSpaClimate(coordinator, entry, temp_unit)])


class ArcticSpaClimate(CoordinatorEntity[ArcticSpaCoordinator], ClimateEntity):
    """Climate entity for Arctic Spa."""

    _attr_has_entity_name = True
    _attr_name = "Spa"
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(
        self, 
        coordinator: ArcticSpaCoordinator, 
        entry: ConfigEntry,
        temp_unit: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Arctic Spa",
            "manufacturer": "Arctic Spas",
            "model": "Hot Tub",
        }
        self._temp_unit = temp_unit
        
        if temp_unit == "C":
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
            self._attr_min_temp = MIN_TEMP_C
            self._attr_max_temp = MAX_TEMP_C
            self._attr_target_temperature_step = 0.5  # Effective resolution in C
        else:
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
            self._attr_min_temp = MIN_TEMP_F
            self._attr_max_temp = MAX_TEMP_F
            self._attr_target_temperature_step = 1.0  # 1°F steps

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self.coordinator.data:
            if self._temp_unit == "C":
                return self.coordinator.data.temperature_c
            return self.coordinator.data.temperature_f
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self.coordinator.data:
            if self._temp_unit == "C":
                return self.coordinator.data.setpoint_c
            return self.coordinator.data.setpoint_f
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        # Arctic Spa is always in heat mode when connected
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        if self.coordinator.data:
            if self.coordinator.data.heater_active:
                return HVACAction.HEATING
            return HVACAction.IDLE
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        
        if self._temp_unit == "C":
            # Convert to F and round to nearest whole degree
            temp_f = round(temperature * 9 / 5 + 32)
            await self.coordinator.async_set_temperature_f(temp_f)
        else:
            await self.coordinator.async_set_temperature_f(int(temperature))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (not really supported, spa is always on)."""
        # Arctic Spa doesn't support turning off heating entirely
        pass
