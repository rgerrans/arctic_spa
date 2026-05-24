"""Config flow for Arctic Spa."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_NAME, CONF_TEMP_UNIT, DEFAULT_NAME, DEFAULT_TEMP_UNIT, DOMAIN
from .spa_client import ArcticSpaClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_TEMP_UNIT, default=DEFAULT_TEMP_UNIT): vol.In(["C", "F"]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    client = ArcticSpaClient(data[CONF_HOST])
    try:
        if not await client.async_start():
            raise CannotConnect
        # Allow time for the bootstrap query to draw a frame back
        await asyncio.sleep(3)
        if not client.status.last_update:
            raise CannotConnect
    except CannotConnect:
        raise
    except Exception as err:
        _LOGGER.error("validate_input error: %s", err)
        raise CannotConnect from err
    finally:
        try:
            await client.async_stop()
        except Exception:
            pass
    return {"title": f"Arctic Spa ({data[CONF_HOST]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
