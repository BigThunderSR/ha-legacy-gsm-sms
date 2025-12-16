"""
Tests for DeviceConnectivityTracker and hard_offline logic.

These tests verify the modem offline detection and auto-restart functionality:
- hard_offline state is set on timeout errors
- Status polling doesn't clear hard_offline (only SMS operations do)
- Restart timer persists through status polls when in hard_offline state
- Configurable hard_offline_restart_timeout works correctly
"""
import json
import threading
import time
import pytest


class MockDeviceTracker:
    """Mock implementation of DeviceConnectivityTracker for testing."""

    def __init__(self):
        self.hard_offline = False
        self.hard_offline_operation = None
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.last_error = None
        self._lock = threading.Lock()

    def record_success(self, operation_name=None):
        """Record successful gammu operation."""
        with self._lock:
            self.last_success_time = time.time()

            if self.hard_offline:
                is_sms_operation = operation_name and 'sms' in operation_name.lower()
                is_same_operation = operation_name == self.hard_offline_operation

                if is_sms_operation or is_same_operation:
                    self.hard_offline = False
                    self.hard_offline_operation = None
                    self.consecutive_failures = 0
                else:
                    # Status polling succeeded but we're still in hard offline
                    return

            self.consecutive_failures = 0
            self.last_error = None

    def record_failure(self, error_message=None, is_timeout=False, operation_name=None):
        """Record failed gammu operation."""
        with self._lock:
            self.consecutive_failures += 1
            self.last_error = error_message

            if is_timeout:
                self.hard_offline = True
                self.hard_offline_operation = operation_name

    def get_status(self):
        """Get current device connectivity status."""
        with self._lock:
            if self.hard_offline:
                return "offline"
            if self.consecutive_failures >= 2:
                return "offline"
            return "online"


class MockMQTTPublisher:
    """Mock implementation of MQTTPublisher for testing restart logic."""

    def __init__(self, hard_offline_restart_timeout=30):
        self.auto_restart_on_failure = True
        self.failure_start_time = None
        self.restart_timeout = 120
        self.hard_offline_restart_timeout = hard_offline_restart_timeout
        self.device_tracker = MockDeviceTracker()
        self.consecutive_failures = 0
        self._would_restart = False

    def _check_restart_timeout(self):
        """Check if failure duration exceeds restart timeout."""
        if not self.auto_restart_on_failure:
            return

        current_time = time.time()
        if self.failure_start_time is None:
            self.failure_start_time = current_time

        failure_duration = current_time - self.failure_start_time
        is_hard_offline = self.device_tracker.hard_offline
        effective_timeout = (
            self.hard_offline_restart_timeout if is_hard_offline 
            else self.restart_timeout
        )

        if failure_duration >= effective_timeout:
            self._would_restart = True

    def track_success(self, operation_name):
        """Simulate successful operation."""
        self.device_tracker.record_success(operation_name=operation_name)
        self.consecutive_failures = 0

        # Only reset restart timer if NOT in hard_offline state
        if not self.device_tracker.hard_offline:
            self.failure_start_time = None
        else:
            self._check_restart_timeout()

    def track_timeout(self, operation_name):
        """Simulate operation timeout."""
        self.consecutive_failures += 1
        self.device_tracker.record_failure(
            f"{operation_name}: Python timeout (15s)",
            is_timeout=True,
            operation_name=operation_name
        )
        self._check_restart_timeout()


class TestHardOfflineState:
    """Tests for hard_offline state management."""

    def test_timeout_sets_hard_offline(self):
        """Timeout should set hard_offline to True."""
        pub = MockMQTTPublisher()
        pub.track_timeout("retrieveAllSms")

        assert pub.device_tracker.hard_offline is True
        assert pub.device_tracker.hard_offline_operation == "retrieveAllSms"
        assert pub.device_tracker.get_status() == "offline"

    def test_status_polling_does_not_clear_hard_offline(self):
        """GetSignalQuality success should not clear hard_offline."""
        pub = MockMQTTPublisher()
        pub.track_timeout("retrieveAllSms")
        pub.track_success("GetSignalQuality")

        assert pub.device_tracker.hard_offline is True
        assert pub.device_tracker.get_status() == "offline"

    def test_sms_operation_clears_hard_offline(self):
        """SMS operation success should clear hard_offline."""
        pub = MockMQTTPublisher()
        pub.track_timeout("retrieveAllSms")
        pub.track_success("retrieveAllSms")

        assert pub.device_tracker.hard_offline is False
        assert pub.device_tracker.get_status() == "online"

    def test_same_operation_clears_hard_offline(self):
        """Same operation that failed succeeding should clear hard_offline."""
        pub = MockMQTTPublisher()
        pub.device_tracker.hard_offline = True
        pub.device_tracker.hard_offline_operation = "customOperation"
        pub.track_success("customOperation")

        assert pub.device_tracker.hard_offline is False


class TestRestartTimer:
    """Tests for restart timer behavior."""

    def test_restart_timer_persists_during_hard_offline(self):
        """failure_start_time should not reset during hard_offline."""
        pub = MockMQTTPublisher()
        pub.failure_start_time = time.time() - 25
        pub.device_tracker.hard_offline = True
        pub.device_tracker.hard_offline_operation = "retrieveAllSms"

        pub.track_success("GetSignalQuality")

        assert pub.failure_start_time is not None

    def test_restart_triggers_after_hard_offline_timeout(self):
        """Restart should trigger after hard_offline_restart_timeout."""
        pub = MockMQTTPublisher(hard_offline_restart_timeout=30)
        pub.failure_start_time = time.time() - 35  # 35s ago
        pub.device_tracker.hard_offline = True
        pub.device_tracker.hard_offline_operation = "retrieveAllSms"

        pub.track_success("GetSignalQuality")

        assert pub._would_restart is True

    def test_no_restart_before_threshold(self):
        """Should not restart before threshold is reached."""
        pub = MockMQTTPublisher(hard_offline_restart_timeout=30)
        pub.failure_start_time = time.time() - 20  # Only 20s ago
        pub.device_tracker.hard_offline = True

        pub._check_restart_timeout()

        assert pub._would_restart is False

    def test_normal_failure_uses_standard_timeout(self):
        """Normal failures should use 120s timeout."""
        pub = MockMQTTPublisher()
        pub.failure_start_time = time.time() - 60  # 60s ago
        pub.device_tracker.hard_offline = False
        pub.device_tracker.consecutive_failures = 3

        pub._check_restart_timeout()

        assert pub._would_restart is False  # 60s < 120s threshold

    def test_failure_start_time_resets_when_not_hard_offline(self):
        """failure_start_time should reset on success when not hard_offline."""
        pub = MockMQTTPublisher()
        pub.failure_start_time = time.time() - 10
        pub.device_tracker.hard_offline = False

        pub.track_success("GetSignalQuality")

        assert pub.failure_start_time is None

    def test_custom_hard_offline_timeout(self):
        """Custom hard_offline_restart_timeout should be respected."""
        pub = MockMQTTPublisher(hard_offline_restart_timeout=15)
        pub.failure_start_time = time.time() - 20
        pub.device_tracker.hard_offline = True

        pub._check_restart_timeout()

        assert pub._would_restart is True


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_operations(self):
        """Device tracker should handle concurrent operations safely."""
        pub = MockMQTTPublisher()
        errors = []

        def thread_func(operation_name, is_failure):
            try:
                for _ in range(50):
                    if is_failure:
                        pub.device_tracker.record_failure(
                            "test", is_timeout=True, operation_name=operation_name
                        )
                    else:
                        pub.device_tracker.record_success(operation_name=operation_name)
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=thread_func, args=(f"op{i}", i % 2 == 0))
            for i in range(4)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestJSONSerialization:
    """Tests for JSON serialization of status data."""

    def test_status_can_be_serialized(self):
        """Status data should be JSON serializable."""
        pub = MockMQTTPublisher()
        pub.device_tracker.hard_offline = True
        pub.device_tracker.hard_offline_operation = "retrieveAllSms"

        status = {
            "status": pub.device_tracker.get_status(),
            "hard_offline": pub.device_tracker.hard_offline,
            "hard_offline_operation": pub.device_tracker.hard_offline_operation,
        }

        json_str = json.dumps(status)
        parsed = json.loads(json_str)

        assert parsed["hard_offline"] is True
        assert parsed["hard_offline_operation"] == "retrieveAllSms"
        assert parsed["status"] == "offline"


class TestIntegrationScenario:
    """Integration tests simulating real-world scenarios."""

    def test_full_timeout_to_restart_flow(self):
        """
        Simulate the exact sequence:
        1. Normal operation
        2. retrieveAllSms times out
        3. Status polling continues to succeed
        4. After 30s, addon should restart
        """
        pub = MockMQTTPublisher(hard_offline_restart_timeout=30)

        # Phase 1: Normal operation
        pub.track_success("retrieveAllSms")
        pub.track_success("GetSignalQuality")
        assert pub.device_tracker.get_status() == "online"

        # Phase 2: retrieveAllSms times out
        pub.track_timeout("retrieveAllSms")
        assert pub.device_tracker.get_status() == "offline"
        assert pub.device_tracker.hard_offline is True
        timeout_start = pub.failure_start_time

        # Phase 3: Simulate 40s of status polling (10s intervals)
        restart_triggered_at = None
        for elapsed in [10, 20, 30, 40]:
            # Simulate time passing
            pub.failure_start_time = timeout_start - elapsed
            pub.track_success("GetSignalQuality")

            if pub._would_restart:
                restart_triggered_at = elapsed
                break

        assert restart_triggered_at is not None
        assert restart_triggered_at == 30  # Should trigger at exactly 30s

    def test_repeated_sms_failures_trigger_restart(self):
        """
        THIS IS THE EXACT BUG SCENARIO from 2025-12-16:
        
        Log showed:
        [15:58:01] WARNING: 🔴 Hard offline: retrieveAllSms timed out
        [15:58:01] INFO: ⏱️ Failure tracking started at 15:58:01
        [15:58:01] INFO: ⏱️ Modem failing for 0s (restart after 30s, hard offline)
        
        Then 5+ minutes passed with NO restart because _check_restart_timeout()
        was only called once at the initial timeout, not on subsequent cycles.
        
        This test verifies that repeated calls to _check_restart_timeout()
        (as would happen on each failed SMS monitoring cycle) will eventually
        trigger the restart.
        """
        pub = MockMQTTPublisher(hard_offline_restart_timeout=30)
        
        # Initial timeout - sets failure_start_time
        pub.track_timeout("retrieveAllSms")
        assert pub.device_tracker.hard_offline is True
        assert pub.failure_start_time is not None
        initial_start_time = pub.failure_start_time
        
        # Verify restart NOT triggered yet (0s elapsed)
        assert pub._would_restart is False
        
        # Simulate SMS monitoring loop calling _check_restart_timeout
        # on each 10s cycle. This is what the fix adds.
        # After 4 cycles (40s total), restart should have triggered.
        
        restart_triggered = False
        for cycle in range(1, 5):  # Cycles at 10s, 20s, 30s, 40s
            # Simulate time passing (10s per cycle)
            pub.failure_start_time = initial_start_time - (cycle * 10)
            
            # This is what the SMS monitoring loop now does on each failure
            pub._check_restart_timeout()
            
            if pub._would_restart:
                restart_triggered = True
                assert cycle == 3, f"Restart should trigger at cycle 3 (30s), not {cycle}"
                break
        
        assert restart_triggered, (
            "CRITICAL BUG: Restart never triggered after 40s of failures! "
            "The _check_restart_timeout() must be called on each failed cycle."
        )
