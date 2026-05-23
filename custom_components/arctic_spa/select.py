"""Select platform for Arctic Spa (multi-speed pumps/blowers, RDT pattern)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PumpStatus
from .coordinator import ArcticSpaCoordinator


PUMP_OPTIONS = ["Off", "Low", "High"]
PUMP_FWD = {"Off": PumpStatus.OFF, "Low": PumpStatus.LOW, "High": PumpStatus.HIGH}
PUMP_REV = {v: k for k, v in PUMP_FWD.items()}

# RDT pattern catalogue — values per Customer Portal LightsDialog. Indexes 0..N.
# We expose a generic numeric range; the spa's interpretation is firmware-specific.
RDT_PATTERN_OPTIONS = [str(i) for i in range(16)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ArcticSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Pump 1 is the 3-speed circulation pump → select with Off/Low/High.
    # Pumps 2-5 are single-speed jet pumps → controlled via switch.* only.
    # Blowers may be variable-speed → expose select alongside the switch.
    entities: list[SelectEntity] = [_PumpSelect(coordinator, entry, 1)]
    for i in range(1, 3):
        entities.append(_BlowerSelect(coordinator, entry, i))
    entities.append(_RdtPatternSelect(coordinator, entry))
    async_add_entities(entities)


class _BaseSelect(CoordinatorEntity[ArcticSpaCoordinator], SelectEntity):
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


class _PumpSelect(_BaseSelect):
    _attr_options = PUMP_OPTIONS
    _attr_icon = "mdi:pump"

    def __init__(self, coordinator, entry, num: int) -> None:
        self._num = num
        super().__init__(coordinator, entry, f"Pump {num} Speed", f"pump{num}_select")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return self._num == 1
        return bool(self.coordinator.data.cfg_pump[self._num - 1])

    @property
    def current_option(self):
        if not self.coordinator.data:
            return None
        return PUMP_REV.get(getattr(self.coordinator.data, f"pump{self._num}"), "Off")

    async def async_select_option(self, option: str) -> None:
        target = PUMP_FWD.get(option, PumpStatus.OFF)
        await self.coordinator.async_set_pump(self._num, target.value)


class _BlowerSelect(_BaseSelect):
    _attr_options = PUMP_OPTIONS
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, entry, num: int) -> None:
        self._num = num
        super().__init__(coordinator, entry, f"Blower {num} Speed", f"blower{num}_select")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.cfg_blower[self._num - 1])

    @property
    def current_option(self):
        if not self.coordinator.data:
            return None
        return PUMP_REV.get(getattr(self.coordinator.data, f"blower{self._num}"), "Off")

    async def async_select_option(self, option: str) -> None:
        target = PUMP_FWD.get(option, PumpStatus.OFF)
        await self.coordinator.async_set_blower(self._num, target.value)


class _RdtPatternSelect(_BaseSelect):
    _attr_options = RDT_PATTERN_OPTIONS
    _attr_icon = "mdi:animation"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Lights Pattern", "rdt_pattern")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_lights)

    @property
    def current_option(self):
        if not self.coordinator.data:
            return None
        v = self.coordinator.data.rdt_pattern
        opt = str(v)
        return opt if opt in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        try:
            await self.coordinator.async_set_rdt(pattern=int(option))
        except ValueError:
            return
