"""Support for Legacy GSM SMS dongle sensor."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    GATEWAY,
    NETWORK_COORDINATOR,
    SIGNAL_COORDINATOR,
    SMS_GATEWAY,
    SMS_MANAGER,
)

SIGNAL_SENSORS = (
    SensorEntityDescription(
        key="SignalStrength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="SignalPercent",
        translation_key="signal_percent",
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=True,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="BitErrorRate",
        translation_key="bit_error_rate",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

NETWORK_SENSORS = (
    SensorEntityDescription(
        key="NetworkName",
        translation_key="network_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="State",
        translation_key="state",
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key="NetworkCode",
        translation_key="network_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="CID",
        translation_key="cid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="LAC",
        translation_key="lac",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)

# SMS-related sensors (not coordinator based)
SMS_SENSORS = (
    SensorEntityDescription(
        key="sms_sent_count",
        translation_key="sms_sent_count",
        icon="mdi:counter",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key="sms_received_count",
        translation_key="sms_received_count",
        icon="mdi:message-badge",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up all device sensors."""
    sms_data = hass.data[DOMAIN][SMS_GATEWAY]
    signal_coordinator = sms_data[SIGNAL_COORDINATOR]
    network_coordinator = sms_data[NETWORK_COORDINATOR]
    gateway = sms_data[GATEWAY]
    sms_manager = sms_data[SMS_MANAGER]
    unique_id = str(await gateway.get_imei_async())

    entities = [
        DeviceSensor(signal_coordinator, description, unique_id, gateway)
        for description in SIGNAL_SENSORS
    ]
    entities.extend(
        DeviceSensor(network_coordinator, description, unique_id, gateway)
        for description in NETWORK_SENSORS
    )

    # Add SMS counter sensors
    for description in SMS_SENSORS:
        entities.append(
            SMSCounterSensor(description, unique_id, gateway, sms_manager)
        )

    # Add Last SMS sensor
    entities.append(LastSMSSensor(unique_id, gateway, sms_manager))

    # Add Modem Status sensor
    entities.append(ModemStatusSensor(unique_id, gateway, sms_manager))

    async_add_entities(entities, True)


class DeviceSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a device sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, description, unique_id, gateway):
        """Initialize the device sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="SMS Gateway",
            manufacturer=gateway.manufacturer,
            model=gateway.model,
            sw_version=gateway.firmware,
        )
        self._attr_unique_id = f"{unique_id}_{description.key}"
        self.entity_description = description

    @property
    def native_value(self):
        """Return the state of the device."""
        return self.coordinator.data.get(self.entity_description.key)


class SMSCounterSensor(SensorEntity):
    """SMS Counter sensor for sent/received counts."""

    _attr_has_entity_name = True

    def __init__(self, description, unique_id, gateway, sms_manager):
        """Initialize the SMS counter sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="SMS Gateway",
            manufacturer=gateway.manufacturer,
            model=gateway.model,
            sw_version=gateway.firmware,
        )
        self._attr_unique_id = f"{unique_id}_{description.key}"
        self.entity_description = description
        self._sms_manager = sms_manager

    @property
    def native_value(self):
        """Return the current count value."""
        if self.entity_description.key == "sms_sent_count":
            return self._sms_manager.sent_count
        elif self.entity_description.key == "sms_received_count":
            return self._sms_manager.received_count
        return None


class LastSMSSensor(SensorEntity):
    """Sensor showing the last received SMS."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_sms"
    _attr_icon = "mdi:message-text"

    def __init__(self, unique_id, gateway, sms_manager):
        """Initialize the last SMS sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="SMS Gateway",
            manufacturer=gateway.manufacturer,
            model=gateway.model,
            sw_version=gateway.firmware,
        )
        self._attr_unique_id = f"{unique_id}_last_sms"
        self._sms_manager = sms_manager

    @property
    def native_value(self):
        """Return the last SMS text (truncated)."""
        last_sms = self._sms_manager.last_sms
        if last_sms:
            text = last_sms.get("text", "")
            # Truncate to 255 chars for state
            return text[:255] if len(text) > 255 else text
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes of the last SMS."""
        last_sms = self._sms_manager.last_sms
        if last_sms:
            return {
                "number": last_sms.get("number"),
                "timestamp": last_sms.get("timestamp"),
                "full_text": last_sms.get("text"),
            }
        return {}


class ModemStatusSensor(SensorEntity):
    """Sensor showing the modem connectivity status."""

    _attr_has_entity_name = True
    _attr_translation_key = "modem_status"
    _attr_icon = "mdi:connection"

    def __init__(self, unique_id, gateway, sms_manager):
        """Initialize the modem status sensor."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="SMS Gateway",
            manufacturer=gateway.manufacturer,
            model=gateway.model,
            sw_version=gateway.firmware,
        )
        self._attr_unique_id = f"{unique_id}_modem_status"
        self._sms_manager = sms_manager

    @property
    def native_value(self):
        """Return the modem status."""
        return self._sms_manager.modem_status
