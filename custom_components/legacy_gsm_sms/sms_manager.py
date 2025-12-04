"""SMS Manager for tracking sent/received SMS counts and history."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SMSCounter:
    """Tracks sent and received SMS counts with persistent storage (thread-safe)."""

    def __init__(self, hass: HomeAssistant, counter_file: str = "sms_counter.json"):
        """Initialize SMS counter with persistent storage."""
        self._hass = hass
        self._counter_file = os.path.join(hass.config.config_dir, counter_file)
        self._sent_count = 0
        self._received_count = 0
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Load counter from JSON file."""
        try:
            if os.path.exists(self._counter_file):
                with open(self._counter_file, "r") as f:
                    data = json.load(f)
                    self._sent_count = data.get("sent_count", 0)
                    self._received_count = data.get("received_count", 0)
                    _LOGGER.info(
                        "Loaded SMS counters: sent=%d, received=%d",
                        self._sent_count,
                        self._received_count,
                    )
            else:
                _LOGGER.info("SMS counter file not found, starting from 0")
        except Exception as e:
            _LOGGER.error("Error loading SMS counter: %s", e)
            self._sent_count = 0
            self._received_count = 0

    def _save(self):
        """Save counter to JSON file."""
        try:
            data = {
                "sent_count": self._sent_count,
                "received_count": self._received_count,
            }
            with open(self._counter_file, "w") as f:
                json.dump(data, f)
            _LOGGER.debug(
                "Saved SMS counters: sent=%d, received=%d",
                self._sent_count,
                self._received_count,
            )
        except Exception as e:
            _LOGGER.error("Error saving SMS counter: %s", e)

    def increment_sent(self) -> int:
        """Increment sent counter and save (thread-safe)."""
        with self._lock:
            self._sent_count += 1
            self._save()
            return self._sent_count

    def increment_received(self) -> int:
        """Increment received counter and save (thread-safe)."""
        with self._lock:
            self._received_count += 1
            self._save()
            return self._received_count

    def reset_sent(self) -> int:
        """Reset sent counter to 0 (thread-safe)."""
        with self._lock:
            self._sent_count = 0
            self._save()
            _LOGGER.info("SMS sent counter reset to 0")
            return self._sent_count

    def reset_received(self) -> int:
        """Reset received counter to 0 (thread-safe)."""
        with self._lock:
            self._received_count = 0
            self._save()
            _LOGGER.info("SMS received counter reset to 0")
            return self._received_count

    @property
    def sent_count(self) -> int:
        """Get current sent count (thread-safe)."""
        with self._lock:
            return self._sent_count

    @property
    def received_count(self) -> int:
        """Get current received count (thread-safe)."""
        with self._lock:
            return self._received_count


class SMSHistory:
    """Tracks received SMS history with persistent storage (thread-safe)."""

    def __init__(
        self,
        hass: HomeAssistant,
        history_file: str = "sms_history.json",
        max_messages: int = 10,
    ):
        """Initialize SMS history with persistent storage."""
        self._hass = hass
        self._history_file = os.path.join(hass.config.config_dir, history_file)
        self._max_messages = max_messages
        self._messages: list[dict[str, Any]] = []
        self._last_sms: dict[str, Any] | None = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Load history from JSON file."""
        try:
            if os.path.exists(self._history_file):
                with open(self._history_file, "r") as f:
                    data = json.load(f)
                    self._messages = data.get("messages", [])
                    self._last_sms = data.get("last_sms")
                    # Keep only max_messages
                    self._messages = self._messages[-self._max_messages :]
                    _LOGGER.info("Loaded SMS history: %d messages", len(self._messages))
            else:
                _LOGGER.info("SMS history file not found, starting fresh")
        except Exception as e:
            _LOGGER.error("Error loading SMS history: %s", e)
            self._messages = []

    def _save(self):
        """Save history to JSON file."""
        try:
            data = {"messages": self._messages, "last_sms": self._last_sms}
            with open(self._history_file, "w") as f:
                json.dump(data, f, indent=2)
            _LOGGER.debug("Saved SMS history: %d messages", len(self._messages))
        except Exception as e:
            _LOGGER.error("Error saving SMS history: %s", e)

    def add_message(
        self, number: str, text: str, timestamp: str | None = None
    ) -> list[dict[str, Any]]:
        """Add a new message to history (thread-safe)."""
        with self._lock:
            if timestamp is None:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            message = {"number": number, "text": text, "timestamp": timestamp}

            self._messages.append(message)
            self._last_sms = message

            # Keep only last max_messages
            if len(self._messages) > self._max_messages:
                self._messages = self._messages[-self._max_messages :]

            self._save()
            _LOGGER.debug("Added message to history from %s", number)
            return self._messages.copy()

    @property
    def last_sms(self) -> dict[str, Any] | None:
        """Get the last received SMS (thread-safe)."""
        with self._lock:
            return self._last_sms.copy() if self._last_sms else None

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Get all messages in history (thread-safe)."""
        with self._lock:
            return self._messages.copy()

    def clear(self):
        """Clear all history (thread-safe)."""
        with self._lock:
            self._messages = []
            self._last_sms = None
            self._save()
            _LOGGER.info("SMS history cleared")


class SMSManager:
    """Central manager for SMS operations, counters, and history."""

    def __init__(self, hass: HomeAssistant, max_history: int = 10):
        """Initialize SMS manager."""
        self._hass = hass
        self.counter = SMSCounter(hass)
        self.history = SMSHistory(hass, max_messages=max_history)

        # Track modem connectivity status
        self._modem_status = "unknown"
        self._last_success_time: float | None = None
        self._consecutive_failures = 0

    def record_sms_sent(self) -> int:
        """Record a sent SMS message."""
        return self.counter.increment_sent()

    def record_sms_received(
        self, number: str, text: str, timestamp: str | None = None
    ) -> dict[str, Any]:
        """Record a received SMS message."""
        self.counter.increment_received()
        self.history.add_message(number, text, timestamp)
        return {
            "number": number,
            "text": text,
            "timestamp": timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
            "received_count": self.counter.received_count,
        }

    def record_modem_success(self):
        """Record successful modem operation."""
        self._last_success_time = time.time()
        self._consecutive_failures = 0
        self._modem_status = "online"

    def record_modem_failure(self, error: str | None = None):
        """Record failed modem operation."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= 2:
            self._modem_status = "offline"
        _LOGGER.warning(
            "Modem operation failed (%d consecutive): %s",
            self._consecutive_failures,
            error,
        )

    @property
    def modem_status(self) -> str:
        """Get current modem status."""
        return self._modem_status

    @property
    def last_sms(self) -> dict[str, Any] | None:
        """Get the last received SMS."""
        return self.history.last_sms

    @property
    def sent_count(self) -> int:
        """Get total sent SMS count."""
        return self.counter.sent_count

    @property
    def received_count(self) -> int:
        """Get total received SMS count."""
        return self.counter.received_count

    def reset_sent_counter(self):
        """Reset sent counter."""
        self.counter.reset_sent()

    def reset_received_counter(self):
        """Reset received counter."""
        self.counter.reset_received()
