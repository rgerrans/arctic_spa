"""Button platform for Arctic Spa (one-shot actions)."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
        _PhBoostButton(coordinator, entry),
        _OzPeak1Button(coordinator, entry),
        _OzPeak2Button(coordinator, entry),
        _ResetButton(coordinator, entry),
    ])


class _BaseButton(CoordinatorEntity[ArcticSpaCoordinator], ButtonEntity):
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


class _PhBoostButton(_BaseButton):
    _attr_icon = "mdi:ph"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pH Boost", "ph_boost")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_spaboy)

    async def async_press(self) -> None:
        await self.coordinator.async_ph_boost()


class _OzPeak1Button(_BaseButton):
    _attr_icon = "mdi:weather-cloudy"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Ozone Peak 1", "oz_peak_1")

    async def async_press(self) -> None:
        await self.coordinator.async_oz_peak1()


class _OzPeak2Button(_BaseButton):
    _attr_icon = "mdi:weather-cloudy"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Ozone Peak 2", "oz_peak_2")

    async def async_press(self) -> None:
        await self.coordinator.async_oz_peak2()


class _ResetButton(_BaseButton):
    _attr_icon = "mdi:restart-alert"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "System Reset", "system_reset")

    async def async_press(self) -> None:
        await self.coordinator.async_reset()
