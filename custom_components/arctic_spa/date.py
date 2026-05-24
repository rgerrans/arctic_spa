"""Date platform — filter cartridge installed-date entities.

Each entity tracks when its filter slot's RFID tag was last new-seen.
Auto-resets to today when the tag ID changes (cartridge swap). User can
manually override the date from the HA UI at any time.

State persists via HA's RestoreEntity across restarts. The companion
sensor.arctic_spa_filter_X_life_remaining reads this date + the selected
lifespan to compute the percentage.
"""
from __future__ import annotations

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
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
        _FilterInstalledDate(coordinator, entry, 1),
        _FilterInstalledDate(coordinator, entry, 2),
    ])


class _FilterInstalledDate(
    CoordinatorEntity[ArcticSpaCoordinator], DateEntity, RestoreEntity
):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: ArcticSpaCoordinator, entry: ConfigEntry, num: int) -> None:
        super().__init__(coordinator)
        self._num = num
        self._attr_unique_id = f"{entry.entry_id}_filter_{num}_installed_date"
        self._attr_name = f"Filter {num} Installed Date"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Restore the previously-persisted install date + last-seen tag.
        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                self.coordinator.filter_install_dates[self._num] = date.fromisoformat(last.state)
            except ValueError:
                pass
        if last and isinstance(last.attributes, dict):
            self.coordinator.filter_last_tags[self._num] = last.attributes.get("last_tag_id", "") or ""

        # First-install bootstrap: if we never had an install date but a tag
        # is currently present, assume the cartridge was installed today.
        # The user can override via the HA UI.
        if self.coordinator.filter_install_dates[self._num] is None and self.coordinator.data:
            current_tag = getattr(self.coordinator.data, f"filter_tag{self._num}", "")
            if current_tag:
                self.coordinator.filter_install_dates[self._num] = date.today()
                self.coordinator.filter_last_tags[self._num] = current_tag
                self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        # Detect tag-id change → cartridge swap → reset install date to today.
        if self.coordinator.data:
            current_tag = getattr(self.coordinator.data, f"filter_tag{self._num}", "")
            if current_tag and current_tag != self.coordinator.filter_last_tags[self._num]:
                self.coordinator.filter_install_dates[self._num] = date.today()
                self.coordinator.filter_last_tags[self._num] = current_tag
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> date | None:
        return self.coordinator.filter_install_dates[self._num]

    @property
    def extra_state_attributes(self) -> dict:
        return {"last_tag_id": self.coordinator.filter_last_tags[self._num] or None}

    async def async_set_value(self, value: date) -> None:
        self.coordinator.filter_install_dates[self._num] = value
        self.async_write_ha_state()
