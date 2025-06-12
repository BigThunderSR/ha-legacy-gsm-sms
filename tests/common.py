"""Common test helpers."""
from unittest.mock import Mock


def mock_gateway():
    """Create a mock gateway."""
    gateway = Mock()
    gateway.init_async = Mock(return_value=None)
    gateway.get_signal_quality_async = Mock(return_value={"SignalStrength": 42, "SignalPercent": 50})
    gateway.get_network_info_async = Mock(
        return_value={"NetworkName": "TestOperator", "NetworkCode": "123456"}
    )
    gateway.manufacturer = "TestManufacturer"
    gateway.model = "TestModel"
    gateway.firmware = "1.0.0"
    return gateway
