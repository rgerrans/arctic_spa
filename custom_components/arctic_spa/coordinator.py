"""DataUpdateCoordinator for Arctic Spa (push updates over WebSocket)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, FALLBACK_REFRESH_INTERVAL, PumpStatus
from .spa_client import ArcticSpaClient, SpaStatus

_LOGGER = logging.getLogger(__name__)


class ArcticSpaCoordinator(DataUpdateCoordinator[SpaStatus]):
    """Push-driven coordinator with a slow safety-net poll."""

    def __init__(self, hass: HomeAssistant, client: ArcticSpaClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=FALLBACK_REFRESH_INTERVAL),
        )
        self.client = client
        self.client.register_state_callback(self._on_state_change)
        # HA-side filter life tracking (per-filter installed date + selected lifespan).
        # Date entity owns installed_date persistence (via RestoreEntity); this
        # dict is the shared in-memory store accessed by the life-remaining sensor.
        from datetime import date as _date
        self.filter_install_dates: dict[int, _date | None] = {1: None, 2: None}
        self.filter_last_tags: dict[int, str] = {1: "", 2: ""}
        self.filter_lifespan_days: int = 180  # updated by the lifespan select entity

    @callback
    def _on_state_change(self) -> None:
        self.async_set_updated_data(self.client.status)

    async def _async_update_data(self) -> SpaStatus:
        if self.client.connected:
            await self.client.async_request_status()
        return self.client.status

    async def async_shutdown(self) -> None:
        self.client.unregister_state_callback(self._on_state_change)
        await self.client.async_stop()

    async def async_set_lights(self, on: bool) -> bool:
        return await self.client.async_set_lights(on)

    async def async_cycle_lights(self) -> bool:
        return await self.client.async_cycle_lights()

    async def async_set_pump(self, pump_num: int, status: int) -> bool:
        return await self.client.async_set_pump(pump_num, PumpStatus(status))

    async def async_cycle_pump(self, pump_num: int) -> bool:
        return await self.client.async_cycle_pump(pump_num)

    async def async_set_blower(self, blower_num: int, status: int) -> bool:
        return await self.client.async_set_blower(blower_num, PumpStatus(status))

    async def async_cycle_blower(self, blower_num: int) -> bool:
        return await self.client.async_cycle_blower(blower_num)

    async def async_set_temperature_f(self, temp_f: int) -> bool:
        return await self.client.async_set_temperature(temp_f)

    async def async_set_temperature_c(self, temp_c: float) -> bool:
        return await self.client.async_set_temperature_c(temp_c)

    async def async_set_filter_boost(self, on: bool) -> bool:
        return await self.client.async_set_filter_boost(on)

    async def async_set_spaboy_boost(self, on: bool) -> bool:
        return await self.client.async_set_spaboy_boost(on)

    async def async_set_onzen(self, on: bool) -> bool:
        return await self.client.async_set_onzen(on)

    async def async_set_sds(self, on: bool) -> bool:
        return await self.client.async_set_sds(on)

    async def async_set_yess(self, on: bool) -> bool:
        return await self.client.async_set_yess(on)

    async def async_set_fogger(self, on: bool) -> bool:
        return await self.client.async_set_fogger(on)

    async def async_set_filter_frequency(self, freq: int) -> bool:
        return await self.client.async_set_filter_frequency(freq)

    async def async_set_filter_duration(self, dur: int) -> bool:
        return await self.client.async_set_filter_duration(dur)

    async def async_set_rdt(self, **kwargs) -> bool:
        return await self.client.async_set_rdt(**kwargs)

    async def async_set_chlorine_band(self, target_orp: int, band: int = 5) -> bool:
        return await self.client.async_set_chlorine_band(target_orp, band)

    async def async_set_chlorine_level(self, lo: int, hi: int) -> bool:
        return await self.client.async_set_chlorine_level(lo, hi)

    async def async_set_ph_band(self, target_ph_x100: int, band: int = 5) -> bool:
        return await self.client.async_set_ph_band(target_ph_x100, band)

    async def async_set_stop_filter_above(self, on: bool) -> bool:
        return await self.client.async_set_stop_filter_above(on)

    async def async_set_spaboy_hours(self, hours: int) -> bool:
        return await self.client.async_set_spaboy_hours(hours)

    async def async_ph_boost(self) -> bool:
        return await self.client.async_ph_boost()

    async def async_oz_peak1(self) -> bool:
        return await self.client.async_oz_peak1()

    async def async_oz_peak2(self) -> bool:
        return await self.client.async_oz_peak2()

    async def async_reset(self) -> bool:
        return await self.client.async_reset("all")
