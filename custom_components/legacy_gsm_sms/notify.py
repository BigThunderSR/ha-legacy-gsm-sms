"""Support for Legacy GSM SMS notification services."""

from __future__ import annotations

import logging

import gammu

from homeassistant.components.notify import ATTR_DATA, BaseNotificationService
from homeassistant.const import CONF_TARGET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_UNICODE, DOMAIN, GATEWAY, SMS_GATEWAY, SMS_MANAGER

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> LegacyGSMSMSNotificationService | None:
    """Get the Legacy GSM SMS notification service."""

    if discovery_info is None:
        return None

    return LegacyGSMSMSNotificationService(hass)


class LegacyGSMSMSNotificationService(BaseNotificationService):
    """Implement the notification service for Legacy GSM SMS."""

    def __init__(self, hass):
        """Initialize the service."""

        self.hass = hass

    async def async_send_message(self, message="", **kwargs):
        """Send SMS message."""

        if SMS_GATEWAY not in self.hass.data[DOMAIN]:
            _LOGGER.error("SMS gateway not found, cannot send message")
            return

        gateway = self.hass.data[DOMAIN][SMS_GATEWAY][GATEWAY]
        sms_manager = self.hass.data[DOMAIN][SMS_GATEWAY].get(SMS_MANAGER)

        targets = kwargs.get(CONF_TARGET)
        if targets is None:
            _LOGGER.error("No target number specified, cannot send message")
            return

        extended_data = kwargs.get(ATTR_DATA)
        _LOGGER.debug("Extended data:%s", extended_data)

        if extended_data is None:
            is_unicode = True
        else:
            is_unicode = extended_data.get(CONF_UNICODE, True)

        smsinfo = {
            "Class": -1,
            "Unicode": is_unicode,
            "Entries": [{"ID": "ConcatenatedTextLong", "Buffer": message}],
        }
        try:
            # Encode messages
            encoded = gammu.EncodeSMS(smsinfo)
        except gammu.GSMError as exc:
            _LOGGER.error("Encoding message %s failed: %s", message, exc)
            if sms_manager:
                sms_manager.record_modem_failure(str(exc))
            return

        # Send messages
        for encoded_message in encoded:
            # Fill in numbers
            encoded_message["SMSC"] = {"Location": 1}

            for target in targets:
                encoded_message["Number"] = target
                try:
                    # Actually send the message
                    await gateway.send_sms_async(encoded_message)
                    # Record successful send
                    if sms_manager:
                        sms_manager.record_sms_sent()
                        sms_manager.record_modem_success()
                    _LOGGER.info("SMS sent to %s", target)
                except gammu.GSMError as exc:
                    _LOGGER.error("Sending to %s failed: %s", target, exc)
                    if sms_manager:
                        sms_manager.record_modem_failure(str(exc))
