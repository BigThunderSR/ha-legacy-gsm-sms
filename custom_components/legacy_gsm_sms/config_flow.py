"""Config flow for Legacy GSM SMS integration."""

from __future__ import annotations

import logging
from typing import Any

import gammu
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_DELETE_READ_SMS,
    CONF_BAUD_SPEED,
    CONF_SMS_CHECK_INTERVAL,
    CONF_SMS_HISTORY_MAX,
    DEFAULT_AUTO_DELETE_READ_SMS,
    DEFAULT_BAUD_SPEED,
    DEFAULT_BAUD_SPEEDS,
    DEFAULT_SMS_CHECK_INTERVAL,
    DEFAULT_SMS_HISTORY_MAX,
    DOMAIN,
)
from .gateway import create_legacy_gsm_sms_gateway

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE): str,
        vol.Optional(CONF_BAUD_SPEED, default=DEFAULT_BAUD_SPEED): selector.selector(
            {"select": {"options": DEFAULT_BAUD_SPEEDS}}
        ),
    }
)


async def get_imei_from_config(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    device = data[CONF_DEVICE]
    connection_mode = "at"
    baud_speed = data.get(CONF_BAUD_SPEED, DEFAULT_BAUD_SPEED)
    if baud_speed != DEFAULT_BAUD_SPEED:
        connection_mode += baud_speed
    config = {"Device": device, "Connection": connection_mode}
    gateway = await create_legacy_gsm_sms_gateway(config, hass)
    if not gateway:
        raise CannotConnect
    try:
        imei = await gateway.get_imei_async()
    except gammu.GSMError as err:
        raise CannotConnect from err
    finally:
        await gateway.terminate_async()

    # Return info that you want to store in the config entry.
    return imei


class LegacyGSMSMSFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Legacy GSM SMS integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return LegacyGSMSMSOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors = {}
        if user_input is not None:
            try:
                imei = await get_imei_from_config(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(imei)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=imei, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class LegacyGSMSMSOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Legacy GSM SMS integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SMS_CHECK_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SMS_CHECK_INTERVAL, DEFAULT_SMS_CHECK_INTERVAL
                    ),
                ): selector.selector(
                    {"number": {"min": 5, "max": 300, "step": 5, "mode": "slider"}}
                ),
                vol.Optional(
                    CONF_AUTO_DELETE_READ_SMS,
                    default=self.config_entry.options.get(
                        CONF_AUTO_DELETE_READ_SMS, DEFAULT_AUTO_DELETE_READ_SMS
                    ),
                ): selector.selector({"boolean": {}}),
                vol.Optional(
                    CONF_SMS_HISTORY_MAX,
                    default=self.config_entry.options.get(
                        CONF_SMS_HISTORY_MAX, DEFAULT_SMS_HISTORY_MAX
                    ),
                ): selector.selector(
                    {"number": {"min": 1, "max": 100, "step": 1, "mode": "slider"}}
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
