"""Tests for the legacy_gsm_sms sensors."""
from unittest.mock import patch

import pytest

from homeassistant.components.legacy_gsm_sms.const import DOMAIN
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS
from homeassistant.setup import async_setup_component

from tests.common import mock_gateway


@pytest.fixture
def mock_setup_entry():
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.legacy_gsm_sms.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_sensors(hass, mock_setup_entry):
    """Test setting up the sensors."""
    with patch(
        "custom_components.legacy_gsm_sms.gateway.create_legacy_gsm_sms_gateway",
        return_value=mock_gateway(),
    ):
        assert await async_setup_component(
            hass,
            DOMAIN,
            {DOMAIN: {"device": "/dev/ttyUSB0", "baud_speed": "0"}},
        )

        # Verify all sensors were created with correct attributes
        states = hass.states.async_all()
        signal_entity = hass.states.get("sensor.gsm_modem_signal_quality")
        assert signal_entity is not None
        assert signal_entity.state == "50"  # SignalPercent from mock
        assert signal_entity.attributes.get("unit_of_measurement") == PERCENTAGE
