"""
Tests for BalanceSMSParser functionality.

These tests verify the balance SMS parsing and data migration:
- Parsing data/minutes/messages from carrier SMS responses
- Parsing account balance and plan expiry dates
- GB to MB conversion for consistent storage
- Migration of old string-based format to new numeric format
- Currency symbol detection
"""
import json
import os
import tempfile
import pytest


class MockBalanceSMSParser:
    """
    Mock implementation of BalanceSMSParser for testing.
    
    This mirrors the actual implementation in mqtt_publisher.py but without
    external dependencies (logging, file I/O during init).
    """
    
    def __init__(self, balance_file=None, currency='USD'):
        self.balance_file = balance_file
        self.currency = currency
        self.balance_data = {
            "account_balance": None,
            "account_balance_currency": currency,
            "data_remaining": None,
            "data_remaining_unit": "MB",
            "minutes_remaining": None,
            "messages_remaining": None,
            "plan_expiry": None,
            "last_updated": None,
            "raw_message": None
        }
    
    def _migrate_old_format(self, data):
        """Migrate old string-based format to new numeric format"""
        import re
        migrated = False
        
        # Migrate data_remaining from "200.00 MB" to 200.0
        if isinstance(data.get('data_remaining'), str):
            match = re.match(r'([\d.]+)\s*(MB|GB)?', data['data_remaining'])
            if match:
                value = float(match.group(1))
                unit = match.group(2) or 'MB'
                if unit.upper() == 'GB':
                    value *= 1024
                data['data_remaining'] = value
                data['data_remaining_unit'] = 'MB'
                migrated = True
        
        # Migrate account_balance from "$3.00" to 3.0
        if isinstance(data.get('account_balance'), str):
            match = re.match(r'[\$€£]?([\d.]+)', data['account_balance'])
            if match:
                value = float(match.group(1))
                data['account_balance'] = value
                data['account_balance_currency'] = self.currency
                migrated = True
        
        return data
    
    def parse_balance_sms(self, message_text):
        """Parse balance information from SMS text"""
        import re
        import time
        
        updated = False
        self.balance_data["last_updated"] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.balance_data["raw_message"] = message_text
        
        # Parse data remaining (MB or GB) - store as numeric MB
        data_match = re.search(
            r'([\d.]+)\s*(MB|GB)\s*(?:of\s*)?(?:High\s*Speed\s*)?Data',
            message_text, re.IGNORECASE
        )
        if data_match:
            amount = float(data_match.group(1))
            unit = data_match.group(2).upper()
            # Convert to MB for consistency
            if unit == "GB":
                amount *= 1024
            self.balance_data["data_remaining"] = amount
            self.balance_data["data_remaining_unit"] = "MB"
            updated = True
        
        # Parse minutes remaining
        minutes_match = re.search(r'([\d,]+)\s*Minutes', message_text, re.IGNORECASE)
        if minutes_match:
            minutes = int(minutes_match.group(1).replace(',', ''))
            self.balance_data["minutes_remaining"] = minutes
            updated = True
        
        # Parse messages remaining
        messages_match = re.search(r'([\d,]+)\s*Messages', message_text, re.IGNORECASE)
        if messages_match:
            messages = int(messages_match.group(1).replace(',', ''))
            self.balance_data["messages_remaining"] = messages
            updated = True
        
        # Parse account balance (dollar amount) - store as numeric
        balance_match = re.search(
            r'balance\s*of\s*\$?([\d.]+)', message_text, re.IGNORECASE
        )
        if balance_match:
            balance = float(balance_match.group(1))
            self.balance_data["account_balance"] = balance
            self.balance_data["account_balance_currency"] = self.currency
            updated = True
        
        # Parse plan expiry date
        expiry_match = re.search(
            r'expires?\s*on\s*([\d-]+)', message_text, re.IGNORECASE
        )
        if expiry_match:
            expiry_date = expiry_match.group(1)
            self.balance_data["plan_expiry"] = expiry_date
            updated = True
        
        return self.balance_data
    
    def get_balance_data(self):
        """Get current balance data"""
        return self.balance_data


class TestBalanceSMSParsing:
    """Tests for parsing balance information from SMS messages."""
    
    def test_parse_data_minutes_messages(self):
        """Test parsing data, minutes, and messages from typical carrier SMS."""
        parser = MockBalanceSMSParser()
        message = "You have 200.00 MB of High Speed Data Remaining 200 Minutes & 991 Messages"
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] == 200.0
        assert result["data_remaining_unit"] == "MB"
        assert result["minutes_remaining"] == 200
        assert result["messages_remaining"] == 991
    
    def test_parse_account_balance_and_expiry(self):
        """Test parsing account balance and plan expiry date."""
        parser = MockBalanceSMSParser()
        message = "Your plan expires on 2026-01-19. You have balance of $2.00"
        
        result = parser.parse_balance_sms(message)
        
        assert result["account_balance"] == 2.0
        assert result["account_balance_currency"] == "USD"
        assert result["plan_expiry"] == "2026-01-19"
    
    def test_parse_gb_to_mb_conversion(self):
        """Test that GB values are converted to MB."""
        parser = MockBalanceSMSParser()
        message = "You have 1.5 GB of High Speed Data Remaining"
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] == 1536.0  # 1.5 * 1024
        assert result["data_remaining_unit"] == "MB"
    
    def test_parse_with_commas_in_numbers(self):
        """Test parsing numbers with comma separators."""
        parser = MockBalanceSMSParser()
        message = "You have 1,500 Minutes & 2,000 Messages remaining"
        
        result = parser.parse_balance_sms(message)
        
        assert result["minutes_remaining"] == 1500
        assert result["messages_remaining"] == 2000
    
    def test_parse_balance_without_dollar_sign(self):
        """Test parsing balance amount without currency symbol."""
        parser = MockBalanceSMSParser()
        message = "You have balance of 5.50"
        
        result = parser.parse_balance_sms(message)
        
        assert result["account_balance"] == 5.50
    
    def test_custom_currency_setting(self):
        """Test that custom currency is applied to parsed balance."""
        parser = MockBalanceSMSParser(currency='EUR')
        message = "You have balance of 10.00"
        
        result = parser.parse_balance_sms(message)
        
        assert result["account_balance"] == 10.0
        assert result["account_balance_currency"] == "EUR"
    
    def test_partial_message_data_only(self):
        """Test parsing message with only data information."""
        parser = MockBalanceSMSParser()
        message = "You have 500 MB of Data remaining"
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] == 500.0
        assert result["minutes_remaining"] is None
        assert result["messages_remaining"] is None
    
    def test_raw_message_stored(self):
        """Test that raw message is stored in balance data."""
        parser = MockBalanceSMSParser()
        message = "Test message content"
        
        result = parser.parse_balance_sms(message)
        
        assert result["raw_message"] == message
    
    def test_last_updated_set(self):
        """Test that last_updated timestamp is set."""
        parser = MockBalanceSMSParser()
        message = "You have 100 MB of Data"
        
        result = parser.parse_balance_sms(message)
        
        assert result["last_updated"] is not None
        # Should be in format YYYY-MM-DD HH:MM:SS
        assert len(result["last_updated"]) == 19


class TestBalanceDataMigration:
    """Tests for migrating old string-based format to new numeric format."""
    
    def test_migrate_data_remaining_mb(self):
        """Test migration of MB string format to numeric."""
        parser = MockBalanceSMSParser()
        old_data = {"data_remaining": "200.00 MB"}
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["data_remaining"] == 200.0
        assert migrated["data_remaining_unit"] == "MB"
    
    def test_migrate_data_remaining_gb(self):
        """Test migration of GB string format to numeric MB."""
        parser = MockBalanceSMSParser()
        old_data = {"data_remaining": "2.5 GB"}
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["data_remaining"] == 2560.0  # 2.5 * 1024
        assert migrated["data_remaining_unit"] == "MB"
    
    def test_migrate_account_balance_with_dollar(self):
        """Test migration of dollar balance string to numeric."""
        parser = MockBalanceSMSParser()
        old_data = {"account_balance": "$3.00"}
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["account_balance"] == 3.0
        assert migrated["account_balance_currency"] == "USD"
    
    def test_migrate_account_balance_with_euro(self):
        """Test migration of euro balance string to numeric."""
        parser = MockBalanceSMSParser(currency='EUR')
        old_data = {"account_balance": "€15.50"}
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["account_balance"] == 15.50
        assert migrated["account_balance_currency"] == "EUR"
    
    def test_migrate_account_balance_with_pound(self):
        """Test migration of pound balance string to numeric."""
        parser = MockBalanceSMSParser(currency='GBP')
        old_data = {"account_balance": "£7.25"}
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["account_balance"] == 7.25
        assert migrated["account_balance_currency"] == "GBP"
    
    def test_migrate_already_numeric_data(self):
        """Test that already numeric data is not changed."""
        parser = MockBalanceSMSParser()
        old_data = {"data_remaining": 150.0, "account_balance": 5.0}
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["data_remaining"] == 150.0
        assert migrated["account_balance"] == 5.0
    
    def test_migrate_mixed_format(self):
        """Test migration with mix of old string and new numeric formats."""
        parser = MockBalanceSMSParser()
        old_data = {
            "data_remaining": "100.50 MB",  # Old format
            "account_balance": 10.0,  # Already numeric
            "minutes_remaining": 500  # Already numeric
        }
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["data_remaining"] == 100.5
        assert migrated["account_balance"] == 10.0
        assert migrated["minutes_remaining"] == 500
    
    def test_migrate_preserves_other_fields(self):
        """Test that migration preserves unrelated fields."""
        parser = MockBalanceSMSParser()
        old_data = {
            "data_remaining": "50 MB",
            "plan_expiry": "2026-01-19",
            "minutes_remaining": 200
        }
        
        migrated = parser._migrate_old_format(old_data)
        
        assert migrated["plan_expiry"] == "2026-01-19"
        assert migrated["minutes_remaining"] == 200


class TestSensorValueTypes:
    """Tests verifying sensor values are correct types for Home Assistant."""
    
    def test_data_remaining_is_float(self):
        """Verify data_remaining is float for device_class: data_size."""
        parser = MockBalanceSMSParser()
        message = "You have 200.00 MB of High Speed Data Remaining"
        
        result = parser.parse_balance_sms(message)
        
        assert isinstance(result["data_remaining"], float)
    
    def test_account_balance_is_float(self):
        """Verify account_balance is float for device_class: monetary."""
        parser = MockBalanceSMSParser()
        message = "You have balance of $3.00"
        
        result = parser.parse_balance_sms(message)
        
        assert isinstance(result["account_balance"], float)
    
    def test_minutes_remaining_is_int(self):
        """Verify minutes_remaining is int for device_class: duration."""
        parser = MockBalanceSMSParser()
        message = "You have 200 Minutes remaining"
        
        result = parser.parse_balance_sms(message)
        
        assert isinstance(result["minutes_remaining"], int)
    
    def test_messages_remaining_is_int(self):
        """Verify messages_remaining is int."""
        parser = MockBalanceSMSParser()
        message = "You have 991 Messages remaining"
        
        result = parser.parse_balance_sms(message)
        
        assert isinstance(result["messages_remaining"], int)
    
    def test_plan_expiry_is_string(self):
        """Verify plan_expiry is string for device_class: date."""
        parser = MockBalanceSMSParser()
        message = "Your plan expires on 2026-01-19"
        
        result = parser.parse_balance_sms(message)
        
        assert isinstance(result["plan_expiry"], str)
        assert result["plan_expiry"] == "2026-01-19"


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""
    
    def test_empty_message(self):
        """Test parsing empty message."""
        parser = MockBalanceSMSParser()
        message = ""
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] is None
        assert result["minutes_remaining"] is None
        assert result["messages_remaining"] is None
        assert result["account_balance"] is None
        assert result["plan_expiry"] is None
    
    def test_unrelated_message(self):
        """Test parsing message without balance info."""
        parser = MockBalanceSMSParser()
        message = "Thank you for your payment. Have a nice day!"
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] is None
        assert result["account_balance"] is None
    
    def test_decimal_precision(self):
        """Test parsing preserves decimal precision."""
        parser = MockBalanceSMSParser()
        message = "You have 123.45 MB of Data and balance of $67.89"
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] == 123.45
        assert result["account_balance"] == 67.89
    
    def test_case_insensitive_parsing(self):
        """Test that parsing is case-insensitive."""
        parser = MockBalanceSMSParser()
        message = "you have 100 mb of high speed data REMAINING 50 MINUTES"
        
        result = parser.parse_balance_sms(message)
        
        assert result["data_remaining"] == 100.0
        assert result["minutes_remaining"] == 50
    
    def test_multiple_parse_calls_accumulate(self):
        """Test that multiple parse calls update the same data object."""
        parser = MockBalanceSMSParser()
        
        # First message with data
        parser.parse_balance_sms("You have 200 MB of Data Remaining")
        
        # Second message with balance
        result = parser.parse_balance_sms("Your balance is balance of $5.00")
        
        # Both should be present
        assert result["data_remaining"] == 200.0
        assert result["account_balance"] == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
