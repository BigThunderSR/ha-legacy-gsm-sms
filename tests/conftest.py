"""Conftest for legacy_gsm_sms tests."""
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytest.register_assert_rewrite("tests.common")

# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never setup during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


# This fixture is used for mocking the python-gammu module, which would otherwise
# be required for all tests.
@pytest.fixture(name="mock_gammu")
def mock_gammu_fixture():
    """Mock gammu module."""
    with patch("gammu.StateMachine", return_value=Mock()) as mock_state_machine:
        mock_state_machine.return_value.GetSMSStatus.return_value = {
            "SIMUsed": 0,
            "PhoneUsed": 0,
        }
        mock_state_machine.return_value.GetNextSMS.side_effect = [
            [{"Location": 1, "State": "UnRead", "Text": "Test message"}]
        ]
        yield mock_state_machine
