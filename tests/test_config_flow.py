"""Tests for the legacy_gsm_sms integration config flow."""
from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.components.legacy_gsm_sms.const import DOMAIN

from tests.common import mock_gateway


async def test_config_flow_success(hass):
    """Test successful config flow."""
    # Ensure the integration is not already loaded
    assert await setup.async_setup_component(hass, DOMAIN, {}) is True

    with patch(
        "custom_components.legacy_gsm_sms.gateway.create_legacy_gsm_sms_gateway",
        return_value=mock_gateway(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

        assert result["type"] == "form"
        assert result["errors"] == {}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"device": "/dev/ttyUSB0", "baud_speed": "0"},
        )

        assert result["type"] == "create_entry"
        assert result["title"] == "GSM Modem"
        assert result["data"] == {"device": "/dev/ttyUSB0", "baud_speed": "0"}
