"""The legacy_gsm_sms component."""

import logging

import gammu
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_FLASH,
    ATTR_MESSAGE,
    ATTR_NUMBER,
    ATTR_UNICODE,
    CONF_BAUD_SPEED,
    DEFAULT_BAUD_SPEED,
    DEFAULT_SMS_HISTORY_MAX,
    DOMAIN,
    GATEWAY,
    HASS_CONFIG,
    NETWORK_COORDINATOR,
    SERVICE_DELETE_ALL_SMS,
    SERVICE_RESET_RECEIVED_COUNTER,
    SERVICE_RESET_SENT_COUNTER,
    SERVICE_SEND_SMS,
    SIGNAL_COORDINATOR,
    SMS_GATEWAY,
    SMS_MANAGER,
)
from .coordinator import NetworkCoordinator, SignalCoordinator
from .gateway import create_legacy_gsm_sms_gateway
from .sms_manager import SMSManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.TEXT]

LEGACY_GSM_SMS_CONFIG_SCHEMA = {vol.Required(CONF_DEVICE): cv.isdevice}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            vol.All(
                cv.deprecated(CONF_DEVICE),
                LEGACY_GSM_SMS_CONFIG_SCHEMA,
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Service schemas
SEND_SMS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NUMBER): cv.string,
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_UNICODE, default=True): cv.boolean,
        vol.Optional(ATTR_FLASH, default=False): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Configure Gammu state machine for Legacy GSM SMS."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[HASS_CONFIG] = config
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure Gammu state machine for Legacy GSM SMS."""

    device = entry.data[CONF_DEVICE]
    connection_mode = "at"
    baud_speed = entry.data.get(CONF_BAUD_SPEED, DEFAULT_BAUD_SPEED)
    if baud_speed != DEFAULT_BAUD_SPEED:
        connection_mode += baud_speed
    config = {"Device": device, "Connection": connection_mode}
    _LOGGER.debug("Connecting mode:%s", connection_mode)
    gateway = await create_legacy_gsm_sms_gateway(config, hass)
    if not gateway:
        raise ConfigEntryNotReady(f"Cannot find device {device}")

    signal_coordinator = SignalCoordinator(hass, gateway)
    network_coordinator = NetworkCoordinator(hass, gateway)

    # Initialize SMS manager for tracking counters and history
    sms_manager = SMSManager(hass, max_history=DEFAULT_SMS_HISTORY_MAX)

    # Set SMS manager on gateway for incoming message tracking
    gateway.set_sms_manager(sms_manager)

    # Fetch initial data so we have data when entities subscribe
    await signal_coordinator.async_config_entry_first_refresh()
    await network_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][SMS_GATEWAY] = {
        SIGNAL_COORDINATOR: signal_coordinator,
        NETWORK_COORDINATOR: network_coordinator,
        GATEWAY: gateway,
        SMS_MANAGER: sms_manager,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, gateway, sms_manager)

    # set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {CONF_NAME: DOMAIN},
            hass.data[HASS_CONFIG],
        )
    )
    return True


async def _async_register_services(
    hass: HomeAssistant, gateway, sms_manager: SMSManager
) -> None:
    """Register integration services."""

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle send SMS service call."""
        number = call.data[ATTR_NUMBER]
        message = call.data[ATTR_MESSAGE]
        unicode_mode = call.data.get(ATTR_UNICODE, True)
        flash_mode = call.data.get(ATTR_FLASH, False)

        # Support multiple recipients (comma-separated)
        recipients = [n.strip() for n in number.split(",") if n.strip()]
        if not recipients:
            _LOGGER.error("No valid phone numbers provided")
            return

        # Flash SMS uses Class 0, normal SMS uses Class -1 (default)
        sms_class = 0 if flash_mode else -1

        if flash_mode:
            _LOGGER.info(
                "Sending Flash SMS (Class 0) to %d recipient(s)", len(recipients)
            )

        for recipient in recipients:
            _LOGGER.info("Service call: Sending SMS to %s", recipient)

            try:
                smsinfo = {
                    "Class": sms_class,
                    "Unicode": unicode_mode,
                    "Entries": [{"ID": "ConcatenatedTextLong", "Buffer": message}],
                }

                encoded = gammu.EncodeSMS(smsinfo)
                for encoded_message in encoded:
                    encoded_message["SMSC"] = {"Location": 1}
                    encoded_message["Number"] = recipient
                    await gateway.send_sms_async(encoded_message)

                sms_manager.record_sms_sent()
                sms_manager.record_modem_success()
                _LOGGER.info("SMS sent successfully to %s", recipient)

            except gammu.GSMError as e:
                _LOGGER.error("Failed to send SMS to %s: %s", recipient, e)
                sms_manager.record_modem_failure(str(e))
                raise

    async def handle_delete_all_sms(call: ServiceCall) -> None:
        """Handle delete all SMS service call."""
        _LOGGER.info("Service call: Deleting all SMS from SIM")
        try:
            deleted_count = await gateway.delete_all_sms_async()
            sms_manager.record_modem_success()
            _LOGGER.info("Deleted %d SMS messages", deleted_count)
        except gammu.GSMError as e:
            _LOGGER.error("Failed to delete SMS: %s", e)
            sms_manager.record_modem_failure(str(e))
            raise

    async def handle_reset_sent_counter(call: ServiceCall) -> None:
        """Handle reset sent counter service call."""
        sms_manager.reset_sent_counter()
        _LOGGER.info("SMS sent counter reset via service")

    async def handle_reset_received_counter(call: ServiceCall) -> None:
        """Handle reset received counter service call."""
        sms_manager.reset_received_counter()
        _LOGGER.info("SMS received counter reset via service")

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_SMS, handle_send_sms, schema=SEND_SMS_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_DELETE_ALL_SMS, handle_delete_all_sms)
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_SENT_COUNTER, handle_reset_sent_counter
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_RECEIVED_COUNTER, handle_reset_received_counter
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        gateway = hass.data[DOMAIN].pop(SMS_GATEWAY)[GATEWAY]
        await gateway.terminate_async()

        # Unregister services
        hass.services.async_remove(DOMAIN, SERVICE_SEND_SMS)
        hass.services.async_remove(DOMAIN, SERVICE_DELETE_ALL_SMS)
        hass.services.async_remove(DOMAIN, SERVICE_RESET_SENT_COUNTER)
        hass.services.async_remove(DOMAIN, SERVICE_RESET_RECEIVED_COUNTER)

    return unload_ok
