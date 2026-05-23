"""Climate platform for Arctic Spa — proper thermostat entity."""
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

from .const import (
    CONF_TEMP_UNIT,
    DEFAULT_MAX_TEMP_C,
    DEFAULT_MAX_TEMP_F,
    DEFAULT_MIN_TEMP_C,
    DEFAULT_MIN_TEMP_F,
    DEFAULT_TEMP_UNIT,
    DOMAIN,
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
    async_add_entities([ArcticSpaClimate(coordinator, entry, temp_unit)])


class ArcticSpaClimate(CoordinatorEntity[ArcticSpaCoordinator], ClimateEntity):
    _attr_has_entity_name = True
    _attr_name = None  # device-name-only → entity_id ends up as climate.<device_slug>
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_translation_key = "spa_climate"

    def __init__(
        self,
        coordinator: ArcticSpaCoordinator,
        entry: ConfigEntry,
        temp_unit: str,
    ) -> None:
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
            self._attr_target_temperature_step = 0.5
            self._fallback_min = DEFAULT_MIN_TEMP_C
            self._fallback_max = DEFAULT_MAX_TEMP_C
        else:
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
            self._attr_target_temperature_step = 1.0
            self._fallback_min = DEFAULT_MIN_TEMP_F
            self._fallback_max = DEFAULT_MAX_TEMP_F

    def _convert(self, f: float) -> float:
        if self._temp_unit == "C":
            return round(((f - 32) * 5 / 9) * 2) / 2
        return f

    @property
    def min_temp(self) -> float:
        if self.coordinator.data:
            return self._convert(self.coordinator.data.setpoint_min_f)
        return self._fallback_min

    @property
    def max_temp(self) -> float:
        if self.coordinator.data:
            return self._convert(self.coordinator.data.setpoint_max_f)
        return self._fallback_max

    @property
    def current_temperature(self) -> float | None:
        if self.coordinator.data and self.coordinator.data.temperature_f:
            return self._convert(self.coordinator.data.temperature_f)
        return None

    @property
    def target_temperature(self) -> float | None:
        if self.coordinator.data and self.coordinator.data.setpoint_f:
            return self._convert(self.coordinator.data.setpoint_f)
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.coordinator.data:
            return HVACAction.HEATING if self.coordinator.data.heater_active else HVACAction.IDLE
        return None

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.connected)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        if self._temp_unit == "C":
            temp_f = round(temp * 9 / 5 + 32)
        else:
            temp_f = int(temp)
        await self.coordinator.async_set_temperature_f(temp_f)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # Always-heat appliance; no-op.
        return
