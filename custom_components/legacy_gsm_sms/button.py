"""Button platform for Legacy GSM SMS integration."""

import logging
from typing import Optional

import gammu

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, GATEWAY, SMS_GATEWAY, SMS_MANAGER

_LOGGER = logging.getLogger(__name__)


BUTTON_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="send_sms",
        translation_key="send_sms",
        icon="mdi:message-plus",
    ),
    ButtonEntityDescription(
        key="delete_all_sms",
        translation_key="delete_all_sms",
        icon="mdi:delete-sweep",
    ),
    ButtonEntityDescription(
        key="reset_sent_counter",
        translation_key="reset_sent_counter",
        icon="mdi:restart",
    ),
    ButtonEntityDescription(
        key="reset_received_counter",
        translation_key="reset_received_counter",
        icon="mdi:restart",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up button entities."""
    sms_data = hass.data[DOMAIN][SMS_GATEWAY]
    gateway = sms_data[GATEWAY]
    sms_manager = sms_data[SMS_MANAGER]
    unique_id = str(await gateway.get_imei_async())

    entities = []
    for description in BUTTON_DESCRIPTIONS:
        entities.append(
            SMSButton(hass, description, unique_id, gateway, sms_manager)
        )

    async_add_entities(entities, True)


class SMSButton(ButtonEntity):
    """Button entity for SMS actions."""

    _attr_has_entity_name = True

    def __init__(self, hass, description, unique_id, gateway, sms_manager):
        """Initialize the button entity."""
        self._hass = hass
        self._gateway = gateway
        self._sms_manager = sms_manager
        self._unique_id_base = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="SMS Gateway",
            manufacturer=gateway.manufacturer,
            model=gateway.model,
            sw_version=gateway.firmware,
        )
        self._attr_unique_id = f"{unique_id}_{description.key}"
        self.entity_description = description

    def _get_entity_id_by_unique_id(self, suffix: str) -> Optional[str]:
        """Get entity_id from unique_id using the entity registry."""
        unique_id = f"{self._unique_id_base}_{suffix}"
        ent_reg = er.async_get(self._hass)
        entry = ent_reg.async_get_entity_id("text", DOMAIN, unique_id)
        return entry

    async def async_press(self) -> None:
        """Handle the button press."""
        key = self.entity_description.key

        if key == "send_sms":
            await self._handle_send_sms()
        elif key == "delete_all_sms":
            await self._handle_delete_all_sms()
        elif key == "reset_sent_counter":
            self._sms_manager.reset_sent_counter()
            _LOGGER.info("SMS sent counter reset")
        elif key == "reset_received_counter":
            self._sms_manager.reset_received_counter()
            _LOGGER.info("SMS received counter reset")

    async def _handle_send_sms(self) -> None:
        """Handle send SMS button press.

        This reads from the text input entities and sends the SMS.
        """
        # Get entity IDs from registry using unique_ids
        phone_entity_id = self._get_entity_id_by_unique_id("phone_number")
        message_entity_id = self._get_entity_id_by_unique_id("message_text")

        if not phone_entity_id:
            _LOGGER.error("Phone number text entity not found in registry")
            return

        if not message_entity_id:
            _LOGGER.error("Message text entity not found in registry")
            return

        phone_state = self._hass.states.get(phone_entity_id)
        message_state = self._hass.states.get(message_entity_id)

        # Check phone number is set and valid
        if not phone_state or not phone_state.state or phone_state.state in (
            "unknown", "unavailable", ""
        ):
            _LOGGER.warning("Phone number not set, cannot send SMS")
            return

        # Check message is set and valid
        if not message_state or not message_state.state or message_state.state in (
            "unknown", "unavailable", ""
        ):
            _LOGGER.warning("Message text not set, cannot send SMS")
            return

        phone = phone_state.state
        message = message_state.state

        _LOGGER.info("Sending SMS to %s via button", phone)

        try:
            # Prepare SMS info
            smsinfo = {
                "Class": -1,
                "Unicode": True,
                "Entries": [{"ID": "ConcatenatedTextLong", "Buffer": message}],
            }

            # Encode the message
            encoded = gammu.EncodeSMS(smsinfo)

            # Send each part of the message
            for encoded_message in encoded:
                encoded_message["SMSC"] = {"Location": 1}
                encoded_message["Number"] = phone
                await self._gateway.send_sms_async(encoded_message)

            self._sms_manager.record_sms_sent()
            _LOGGER.info("SMS sent successfully to %s", phone)

            # Clear the text inputs after successful send
            await self._hass.services.async_call(
                "text",
                "set_value",
                {"entity_id": phone_entity_id, "value": ""},
            )
            await self._hass.services.async_call(
                "text",
                "set_value",
                {"entity_id": message_entity_id, "value": ""},
            )

        except gammu.GSMError as e:
            _LOGGER.error("Failed to send SMS: %s", e)
            self._sms_manager.record_modem_failure(str(e))

    async def _handle_delete_all_sms(self) -> None:
        """Handle delete all SMS button press."""
        _LOGGER.info("Deleting all SMS from SIM")
        try:
            deleted_count = await self._gateway.delete_all_sms_async()
            _LOGGER.info("Deleted %d SMS messages", deleted_count)
            self._sms_manager.record_modem_success()
        except gammu.GSMError as e:
            _LOGGER.error("Failed to delete SMS: %s", e)
            self._sms_manager.record_modem_failure(str(e))
