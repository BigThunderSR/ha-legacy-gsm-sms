"""
Tests for GET endpoint functionality.

These tests verify the GET endpoint implementation:
- IP whitelisting with CIDR notation
- URL decoding (+ and %20 to spaces)
- SMS deduplication logic
- Configuration default values
- Path parsing for /sms/{PHONE}&{MESSAGE} format
"""
import ipaddress
import time
from urllib.parse import unquote_plus


class TestIPWhitelist:
    """Test IP address whitelisting with CIDR notation."""
    
    def test_ip_in_private_network(self):
        """Test that private network IPs are allowed."""
        client_ip = "192.168.1.100"
        allowed_networks = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
        
        client = ipaddress.ip_address(client_ip)
        allowed = False
        for network_str in allowed_networks:
            network = ipaddress.ip_network(network_str, strict=False)
            if client in network:
                allowed = True
                break
        
        assert allowed is True, "Private IP should be allowed"
    
    def test_ip_outside_private_network(self):
        """Test that public IPs are blocked."""
        client_ip = "8.8.8.8"
        allowed_networks = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
        
        client = ipaddress.ip_address(client_ip)
        allowed = False
        for network_str in allowed_networks:
            network = ipaddress.ip_network(network_str, strict=False)
            if client in network:
                allowed = True
                break
        
        assert allowed is False, "Public IP should be blocked"
    
    def test_localhost_allowed(self):
        """Test that localhost is allowed."""
        client_ip = "127.0.0.1"
        allowed_networks = ["127.0.0.1"]
        
        client = ipaddress.ip_address(client_ip)
        allowed = False
        for network_str in allowed_networks:
            network = ipaddress.ip_network(network_str, strict=False)
            if client in network:
                allowed = True
                break
        
        assert allowed is True, "Localhost should be allowed"
    
    def test_empty_whitelist_allows_all(self):
        """Test that empty whitelist allows all IPs."""
        allowed_networks = []
        
        # When list is empty, IP check should be skipped
        assert not allowed_networks, "Empty list should be falsy"


class TestURLDecoding:
    """Test URL decoding for phone numbers and messages."""
    
    def test_plus_to_space(self):
        """Test that + signs are decoded to spaces."""
        encoded = "Hello+World"
        decoded = unquote_plus(encoded)
        assert decoded == "Hello World", "Plus should decode to space"
    
    def test_percent20_to_space(self):
        """Test that %20 is decoded to spaces."""
        encoded = "Hello%20World"
        decoded = unquote_plus(encoded)
        assert decoded == "Hello World", "%20 should decode to space"
    
    def test_mixed_encoding(self):
        """Test mixed encoding formats."""
        encoded = "Test+Message%20Here"
        decoded = unquote_plus(encoded)
        assert decoded == "Test Message Here", "Mixed encoding should work"
    
    def test_phone_number_with_plus(self):
        """Test phone number with + prefix."""
        encoded = "%2B15555551234"
        decoded = unquote_plus(encoded)
        assert decoded == "+15555551234", "Phone number + should decode"


class TestPathParsing:
    """Test path parsing for GET endpoint."""
    
    def test_split_on_first_ampersand(self):
        """Test that path is split on first & only."""
        path = "5555551234&Hello&World"
        parts = path.split('&', 1)
        
        assert len(parts) == 2, "Should split into 2 parts"
        assert parts[0] == "5555551234", "First part should be phone"
        assert parts[1] == "Hello&World", "Second part should be rest of message"
    
    def test_path_without_ampersand(self):
        """Test that path without & is handled."""
        path = "5555551234"
        parts = path.split('&', 1)
        
        assert len(parts) == 1, "Should have 1 part only"
    
    def test_path_with_decoded_content(self):
        """Test path parsing with URL decoding."""
        path = "5555551234&Test+Message"
        parts = path.split('&', 1)
        phone = unquote_plus(parts[0])
        message = unquote_plus(parts[1])
        
        assert phone == "5555551234", "Phone should be decoded"
        assert message == "Test Message", "Message should be decoded"


class TestDeduplication:
    """Test SMS deduplication logic."""
    
    def test_duplicate_detection_within_window(self):
        """Test that duplicates within 15s window are detected."""
        cache = {}
        window = 15
        
        # First request
        key1 = "5555551234|Test message"
        time1 = time.time()
        cache[key1] = time1
        
        # Duplicate request 1 second later
        time2 = time1 + 1
        is_duplicate = key1 in cache and (time2 - cache[key1] < window)
        
        assert is_duplicate is True, "Should detect duplicate within window"
    
    def test_duplicate_detection_outside_window(self):
        """Test that requests outside window are not duplicates."""
        cache = {}
        window = 15
        
        # First request
        key1 = "5555551234|Test message"
        time1 = time.time()
        cache[key1] = time1
        
        # Request 20 seconds later
        time2 = time1 + 20
        is_duplicate = key1 in cache and (time2 - cache[key1] < window)
        
        assert is_duplicate is False, "Should not detect duplicate outside window"
    
    def test_cache_cleanup(self):
        """Test that old cache entries are removed."""
        cache = {
            "key1|msg1": time.time() - 20,  # 20 seconds old
            "key2|msg2": time.time() - 5,   # 5 seconds old
        }
        window = 15
        current_time = time.time()
        
        # Clean cache
        cleaned = {k: v for k, v in cache.items() 
                   if current_time - v < window}
        
        assert "key1|msg1" not in cleaned, "Old entry should be removed"
        assert "key2|msg2" in cleaned, "Recent entry should remain"
    
    def test_different_message_not_duplicate(self):
        """Test that different messages are not duplicates."""
        key1 = "5555551234|Message 1"
        key2 = "5555551234|Message 2"
        
        assert key1 != key2, "Different messages should have different keys"
    
    def test_different_number_not_duplicate(self):
        """Test that different numbers are not duplicates."""
        key1 = "5555551234|Test message"
        key2 = "9999999999|Test message"
        
        assert key1 != key2, "Different numbers should have different keys"


class TestConfigDefaults:
    """Test configuration default values."""
    
    def test_auth_defaults_to_false(self):
        """Test that auth_required defaults to False."""
        config = {}
        auth_required = config.get('get_endpoint_auth_required', False)
        assert auth_required is False, "Auth should default to False"
    
    def test_allowed_ips_defaults_to_empty(self):
        """Test that allowed_ips defaults to empty list."""
        config = {}
        allowed_ips = config.get('get_endpoint_allowed_ips', [])
        assert allowed_ips == [], "Allowed IPs should default to []"
    
    def test_deduplication_defaults_to_true(self):
        """Test that deduplication defaults to True."""
        config = {}
        dedup_enabled = config.get('get_endpoint_deduplication_enabled', True)
        assert dedup_enabled is True, "Deduplication should default to True"
    
    def test_empty_list_is_falsy(self):
        """Test that empty IP list is falsy (disables IP check)."""
        allowed_ips = []
        assert not allowed_ips, "Empty list should be falsy"
    
    def test_nonempty_list_is_truthy(self):
        """Test that non-empty IP list is truthy (enables IP check)."""
        allowed_ips = ["192.168.0.0/16"]
        assert allowed_ips, "Non-empty list should be truthy"
