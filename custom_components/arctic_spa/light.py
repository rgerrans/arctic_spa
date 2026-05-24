"""Light platform for Arctic Spa RDT RGB lights."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    async_add_entities([_RdtLight(coordinator, entry)])


class _RdtLight(CoordinatorEntity[ArcticSpaCoordinator], LightEntity):
    _attr_has_entity_name = True
    _attr_name = "Cabinet Lights"
    _attr_icon = "mdi:led-strip-variant"
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rdt_light"
        self._attr_device_info = coordinator.device_info
        # Remember last non-zero color so we can restore on turn-on.
        self._last_rgb: tuple[int, int, int] | None = None
        self._last_brightness: int = 255

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_lights)

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return bool(self.coordinator.data.lights)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        if not self.coordinator.data:
            return None
        d = self.coordinator.data
        if d.rdt_red == 0 and d.rdt_green == 0 and d.rdt_blue == 0:
            return None
        return (d.rdt_red, d.rdt_green, d.rdt_blue)

    @property
    def brightness(self) -> int | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.rdt_brightness or None

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Apply color/brightness updates if requested, then ensure lights are on.
        kwargs_to_send: dict[str, int] = {}
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            kwargs_to_send.update({"red": r, "green": g, "blue": b})
            self._last_rgb = (r, g, b)
        if ATTR_BRIGHTNESS in kwargs:
            kwargs_to_send["brightness"] = int(kwargs[ATTR_BRIGHTNESS])
            self._last_brightness = int(kwargs[ATTR_BRIGHTNESS])
        if kwargs_to_send:
            await self.coordinator.async_set_rdt(**kwargs_to_send)
        if not self.is_on:
            await self.coordinator.async_set_lights(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_lights(False)
