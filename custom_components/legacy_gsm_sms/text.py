"""Text platform for Legacy GSM SMS integration."""

import logging

from homeassistant.components.text import TextEntity, TextEntityDescription, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, GATEWAY, SMS_GATEWAY

_LOGGER = logging.getLogger(__name__)


TEXT_DESCRIPTIONS = (
    TextEntityDescription(
        key="phone_number",
        translation_key="phone_number",
        icon="mdi:phone",
        mode=TextMode.TEXT,
        native_max=50,
    ),
    TextEntityDescription(
        key="message_text",
        translation_key="message_text",
        icon="mdi:message-text",
        mode=TextMode.TEXT,
        native_max=1000,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up text input entities."""
    sms_data = hass.data[DOMAIN][SMS_GATEWAY]
    gateway = sms_data[GATEWAY]
    unique_id = str(await gateway.get_imei_async())

    entities = []
    for description in TEXT_DESCRIPTIONS:
        entities.append(SMSTextInput(description, unique_id, gateway))

    async_add_entities(entities, True)


class SMSTextInput(TextEntity):
    """Text input entity for SMS phone number and message."""

    _attr_has_entity_name = True

    def __init__(self, description, unique_id, gateway):
        """Initialize the text input entity."""
        self._gateway = gateway
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="SMS Gateway",
            manufacturer=gateway.manufacturer,
            model=gateway.model,
            sw_version=gateway.firmware,
        )
        self._attr_unique_id = f"{unique_id}_{description.key}"
        self.entity_description = description
        self._value = ""

    @property
    def native_value(self) -> str:
        """Return the current value."""
        return self._value

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        self._value = value
        self.async_write_ha_state()
        _LOGGER.debug("Text input %s set to: %s", self.entity_description.key, value)
