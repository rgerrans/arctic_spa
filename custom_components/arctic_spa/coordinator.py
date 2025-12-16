"""DataUpdateCoordinator for Arctic Spa with push updates."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PumpStatus
from .spa_client import ArcticSpaClient, SpaStatus

_LOGGER = logging.getLogger(__name__)

# Fallback polling interval (in case push updates stop working)
FALLBACK_SCAN_INTERVAL = 60


class ArcticSpaCoordinator(DataUpdateCoordinator[SpaStatus]):
    """Coordinator for Arctic Spa with push-based updates.
    
    This coordinator primarily relies on push updates from the spa
    (via the persistent connection), but also has a fallback polling
    mechanism in case updates stop coming through.
    """

    def __init__(self, hass: HomeAssistant, client: ArcticSpaClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Fallback polling interval - the spa should push updates,
            # but we poll occasionally as a safety net
            update_interval=timedelta(seconds=FALLBACK_SCAN_INTERVAL),
        )
        self.client = client
        
        # Register callback for push updates from spa
        self.client.register_state_callback(self._on_state_change)

    @callback
    def _on_state_change(self) -> None:
        """Handle state change pushed from spa."""
        _LOGGER.debug("Received push update from spa")
        # Update the data and notify listeners
        self.async_set_updated_data(self.client.status)

    async def _async_update_data(self) -> SpaStatus:
        """Fetch data from the spa (fallback polling)."""
        # Request fresh status
        if self.client.connected:
            await self.client.async_request_status()
        return self.client.status

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        self.client.unregister_state_callback(self._on_state_change)
        await self.client.async_stop()

    # Command methods
    async def async_set_lights(self, on: bool) -> bool:
        """Set lights."""
        return await self.client.async_set_lights(on)

    async def async_set_pump(self, pump_num: int, status: int) -> bool:
        """Set pump status."""
        return await self.client.async_set_pump(pump_num, PumpStatus(status))

    async def async_set_blower(self, blower_num: int, status: int) -> bool:
        """Set blower status."""
        return await self.client.async_set_blower(blower_num, PumpStatus(status))

    async def async_set_temperature_c(self, temp_c: float) -> bool:
        """Set temperature in Celsius."""
        return await self.client.async_set_temperature_c(temp_c)

    async def async_set_temperature_f(self, temp_f: int) -> bool:
        """Set temperature in Fahrenheit."""
        return await self.client.async_set_temperature(temp_f)

    async def async_set_filter_boost(self, on: bool) -> bool:
        """Set filter boost."""
        return await self.client.async_set_filter_boost(on)

    async def async_set_onzen(self, on: bool) -> bool:
        """Set Onzen."""
        return await self.client.async_set_onzen(on)

    async def async_set_sds(self, on: bool) -> bool:
        """Set SDS (bubbles)."""
        return await self.client.async_set_sds(on)
