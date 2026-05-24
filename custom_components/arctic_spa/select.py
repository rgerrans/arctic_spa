"""Select platform for Arctic Spa (multi-speed pumps/blowers, RDT pattern)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CHLORINE_LEVEL_PRESETS,
    DOMAIN,
    FILTER_LIFESPAN_DEFAULT,
    FILTER_LIFESPAN_OPTIONS,
    PumpStatus,
    RDT_PATTERN_NAMES,
)
from .coordinator import ArcticSpaCoordinator
from homeassistant.helpers.restore_state import RestoreEntity


PUMP_OPTIONS = ["Off", "Low", "High"]
PUMP_FWD = {"Off": PumpStatus.OFF, "Low": PumpStatus.LOW, "High": PumpStatus.HIGH}
PUMP_REV = {v: k for k, v in PUMP_FWD.items()}

CHLORINE_LEVEL_OPTIONS = list(CHLORINE_LEVEL_PRESETS.keys())

# RDT pattern names per Customer Portal LightsDialog.tsx (only 4 exist):
#   0=Solid, 1=Fade In, 2=Blinking, 3=Spectrum
RDT_PATTERN_OPTIONS = list(RDT_PATTERN_NAMES.values())
RDT_PATTERN_FWD = {name: idx for idx, name in RDT_PATTERN_NAMES.items()}


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
    entities.append(_ChlorineLevelSelect(coordinator, entry))
    entities.append(_FilterLifespanSelect(coordinator, entry))
    async_add_entities(entities)


class _BaseSelect(CoordinatorEntity[ArcticSpaCoordinator], SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, key) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info


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
        return RDT_PATTERN_NAMES.get(self.coordinator.data.rdt_pattern)

    async def async_select_option(self, option: str) -> None:
        idx = RDT_PATTERN_FWD.get(option)
        if idx is None:
            return
        await self.coordinator.async_set_rdt(pattern=idx)


class _ChlorineLevelSelect(_BaseSelect):
    """Chlorine production level — Customer Portal Low/Medium/High preset bands."""

    _attr_options = CHLORINE_LEVEL_OPTIONS
    _attr_icon = "mdi:test-tube"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "Chlorine Level", "chlorine_level")

    @property
    def entity_registry_enabled_default(self) -> bool:
        if not self.coordinator.data:
            return True
        return bool(self.coordinator.data.cfg_spaboy)

    @property
    def current_option(self):
        """Match current SBORPlo/SBORPhi to a preset (or None if custom)."""
        if not self.coordinator.data:
            return None
        lo = self.coordinator.data.sb_orp_lo
        hi = self.coordinator.data.sb_orp_hi
        if not lo or not hi:
            return None
        for name, (preset_lo, preset_hi) in CHLORINE_LEVEL_PRESETS.items():
            if lo == preset_lo and hi == preset_hi:
                return name
        return None  # custom value set (via number.chlorine_target_orp)

    async def async_select_option(self, option: str) -> None:
        preset = CHLORINE_LEVEL_PRESETS.get(option)
        if preset is None:
            return
        lo, hi = preset
        await self.coordinator.async_set_chlorine_level(lo, hi)


class _FilterLifespanSelect(CoordinatorEntity[ArcticSpaCoordinator], SelectEntity, RestoreEntity):
    """User-selectable filter cartridge replacement frequency (global, both filters)."""

    _attr_has_entity_name = True
    _attr_options = list(FILTER_LIFESPAN_OPTIONS.keys())
    _attr_icon = "mdi:calendar-refresh"
    _attr_entity_category = "config"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_filter_lifespan"
        self._attr_name = "Filter Replacement Frequency"
        self._attr_device_info = coordinator.device_info
        self._selected: str = FILTER_LIFESPAN_DEFAULT

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in self._attr_options:
            self._selected = last.state
        # Push the active lifespan into the coordinator for the life-remaining sensor
        self.coordinator.filter_lifespan_days = FILTER_LIFESPAN_OPTIONS[self._selected]

    @property
    def current_option(self) -> str:
        return self._selected

    async def async_select_option(self, option: str) -> None:
        if option not in FILTER_LIFESPAN_OPTIONS:
            return
        self._selected = option
        self.coordinator.filter_lifespan_days = FILTER_LIFESPAN_OPTIONS[option]
        self.async_write_ha_state()
