"""Tests for PII redaction in guardrails.

Ensures that personal identifiable information is properly redacted
before being sent to models or included in outputs.
"""
import pytest

from llmhive.app.guardrails import (
    redact_sensitive_info,
    check_output_policy,
    filter_query,
    filter_output,
    SensitiveDataType,
    RedactionResult,
)


class TestPIIRedaction:
    """Test suite for PII redaction functionality."""

    def test_email_redaction(self):
        """Test that email addresses are redacted."""
        text = "Contact me at john.doe@example.com for more info"
        result = redact_sensitive_info(text)
        
        assert isinstance(result, RedactionResult)
        # Use redacted_text attribute
        assert "john.doe@example.com" not in result.redacted_text
        assert "[REDACTED_EMAIL]" in result.redacted_text or "***" in result.redacted_text

    def test_multiple_emails_redacted(self):
        """Test that multiple emails are all redacted."""
        text = "Emails: user1@test.com and user2@domain.org"
        result = redact_sensitive_info(text)
        
        assert "user1@test.com" not in result.redacted_text
        assert "user2@domain.org" not in result.redacted_text

    def test_phone_number_redaction(self):
        """Test that phone numbers are redacted."""
        phone_formats = [
            "Call me at 555-123-4567",
            "Phone: (555) 123-4567",
            "Reach me at 5551234567",
        ]
        
        for text in phone_formats:
            result = redact_sensitive_info(text)
            # Should not contain the actual phone number
            stripped = result.redacted_text.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
            assert "5551234567" not in stripped or "[REDACTED" in result.redacted_text

    def test_ssn_redaction(self):
        """Test that Social Security Numbers are redacted."""
        text = "My SSN is 123-45-6789"
        result = redact_sensitive_info(text)
        
        assert "123-45-6789" not in result.redacted_text

    def test_credit_card_redaction(self):
        """Test that credit card numbers are redacted."""
        cc_formats = [
            "CC: 4111-1111-1111-1111",
            "Card: 4111 1111 1111 1111",
        ]
        
        for text in cc_formats:
            result = redact_sensitive_info(text)
            # Credit card should be redacted
            assert "4111111111111111" not in result.redacted_text.replace("-", "").replace(" ", "")

    def test_preserves_non_pii_text(self):
        """Test that non-PII text is preserved."""
        text = "The meeting is scheduled for tomorrow at 3pm in conference room B"
        result = redact_sensitive_info(text)
        
        assert "meeting" in result.redacted_text
        assert "tomorrow" in result.redacted_text
        assert "3pm" in result.redacted_text

    def test_mixed_pii_content(self):
        """Test text with mixed PII and normal content."""
        text = """
        Hello John,
        
        Please contact me at john@example.com or call 555-123-4567.
        The total amount is $500 and the tracking number is ABC123.
        """
        result = redact_sensitive_info(text)
        
        # Email should be redacted
        assert "john@example.com" not in result.redacted_text
        
        # Non-PII should remain
        assert "Hello" in result.redacted_text
        assert "$500" in result.redacted_text

    def test_redaction_result_structure(self):
        """Test that RedactionResult has proper structure."""
        text = "test@example.com"
        result = redact_sensitive_info(text)
        
        assert hasattr(result, 'original_text')
        assert hasattr(result, 'redacted_text')
        assert hasattr(result, 'redactions')
        assert isinstance(result.redacted_text, str)
        assert isinstance(result.redactions, list)


class TestFilterQuery:
    """Test query filtering for PII."""

    def test_clean_query_unchanged(self):
        """Clean query without PII should be mostly unchanged."""
        safe_input = "What is the capital of France?"
        result = filter_query(safe_input)
        
        # filter_query returns a string
        assert isinstance(result, str)
        assert "France" in result

    def test_query_with_pii_filtered(self):
        """Query with PII should be filtered."""
        pii_input = "My email is test@example.com"
        result = filter_query(pii_input)
        
        assert "test@example.com" not in result


class TestFilterOutput:
    """Test output filtering."""

    def test_normal_output_preserved(self):
        """Normal output should be mostly preserved."""
        output = """
        The capital of France is Paris. It is known for the Eiffel Tower
        and the Louvre Museum.
        """
        result = filter_output(output)
        
        # filter_output returns tuple: (filtered_text, was_filtered, violations)
        assert isinstance(result, tuple)
        assert len(result) == 3
        filtered_text, was_filtered, violations = result
        assert "Paris" in filtered_text
        assert "Eiffel Tower" in filtered_text


class TestOutputPolicyCheck:
    """Test output policy checking."""

    def test_normal_output_passes(self):
        """Normal output should pass policy check."""
        output = """
        The capital of France is Paris. It is known for the Eiffel Tower
        and the Louvre Museum.
        """
        result = check_output_policy(output)
        # Returns PolicyCheckResult
        assert result.is_allowed is True

    def test_policy_check_returns_result(self):
        """Policy check should return PolicyCheckResult."""
        from llmhive.app.guardrails import PolicyCheckResult
        result = check_output_policy("test output")
        assert isinstance(result, PolicyCheckResult)


class TestSensitiveDataTypes:
    """Test sensitive data type enumeration."""

    def test_all_types_defined(self):
        """Verify all expected PII types are defined."""
        expected_types = ["EMAIL", "PHONE", "SSN", "CREDIT_CARD"]
        
        for type_name in expected_types:
            assert hasattr(SensitiveDataType, type_name), f"Missing type: {type_name}"

    def test_type_values(self):
        """Test that types have string values."""
        assert SensitiveDataType.EMAIL == "email"
        assert SensitiveDataType.PHONE == "phone"


class TestEdgeCases:
    """Edge cases for PII redaction."""

    def test_empty_input(self):
        """Empty input should be handled gracefully."""
        result = redact_sensitive_info("")
        assert result.redacted_text == ""

    def test_whitespace_only(self):
        """Whitespace-only input should be handled."""
        result = redact_sensitive_info("   \n\t   ")
        assert isinstance(result.redacted_text, str)

    def test_special_characters(self):
        """Special characters should not break redaction."""
        text = "Email: <user@test.com> [brackets]"
        result = redact_sensitive_info(text)
        assert "user@test.com" not in result.redacted_text

    def test_unicode_content(self):
        """Unicode content should be handled."""
        text = "Normal text with unicode: 日本語"
        result = redact_sensitive_info(text)
        assert isinstance(result.redacted_text, str)

    def test_very_long_text(self):
        """Very long text should be processed."""
        long_text = "Normal text. " * 100 + "email@test.com " + "More text. " * 100
        result = redact_sensitive_info(long_text)
        assert "email@test.com" not in result.redacted_text
        assert "Normal text" in result.redacted_text

    def test_partial_patterns_preserved(self):
        """Partial patterns that aren't real PII should be preserved."""
        # This might look like a phone but isn't
        text = "The year 2024 is significant"
        result = redact_sensitive_info(text)
        assert "2024" in result.redacted_text

    def test_ip_address_handling(self):
        """IP addresses should be handled appropriately."""
        text = "Server IP: 192.168.1.1"
        result = redact_sensitive_info(text)
        # IP handling depends on implementation
        assert isinstance(result.redacted_text, str)
