"""Unit tests for security guardrails module."""
from __future__ import annotations

import pytest
import re

from llmhive.src.llmhive.app.guardrails import (
    # Data types
    SensitiveDataType,
    ContentSeverity,
    RedactionResult,
    PolicyViolation,
    PolicyCheckResult,
    RiskAssessment,
    SafetyReport,
    # Core functions
    redact_sensitive_info,
    check_output_policy,
    enforce_output_policy,
    assess_query_risk,
    filter_query,
    filter_output,
    security_check,
    # Classes
    SafetyValidator,
    TierAccessController,
    ExecutionSandbox,
)


class TestRedactSensitiveInfo:
    """Tests for sensitive data redaction."""
    
    def test_redact_email(self):
        """Test email address redaction."""
        text = "Contact me at john.doe@example.com for more info."
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_EMAIL]" in result.redacted_text
        assert "john.doe@example.com" not in result.redacted_text
        assert result.redaction_count >= 1
    
    def test_redact_multiple_emails(self):
        """Test multiple email address redaction."""
        text = "Email alice@test.com or bob@company.org"
        result = redact_sensitive_info(text)
        
        assert result.redaction_count >= 2
        assert "alice@test.com" not in result.redacted_text
        assert "bob@company.org" not in result.redacted_text
    
    def test_redact_ssn(self):
        """Test SSN redaction."""
        text = "My SSN is 123-45-6789."
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_SSN]" in result.redacted_text
        assert "123-45-6789" not in result.redacted_text
    
    def test_redact_phone_number(self):
        """Test phone number redaction."""
        text = "Call me at 555-123-4567."
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_PHONE]" in result.redacted_text
        assert "555-123-4567" not in result.redacted_text
    
    def test_redact_phone_with_country_code(self):
        """Test phone number with country code."""
        text = "My number is +1 555 123 4567."
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_PHONE]" in result.redacted_text
    
    def test_redact_credit_card(self):
        """Test credit card number redaction."""
        text = "My card is 4111-1111-1111-1111."
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_CC]" in result.redacted_text
        assert "4111-1111-1111-1111" not in result.redacted_text
    
    def test_redact_ip_address(self):
        """Test IP address redaction."""
        text = "Server IP is 192.168.1.100."
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_IP]" in result.redacted_text
        assert "192.168.1.100" not in result.redacted_text
    
    def test_redact_api_key_pattern(self):
        """Test API key pattern redaction."""
        text = "Use api_key sk-1234567890abcdefghijklmnopqrstuv for auth."
        result = redact_sensitive_info(text)
        
        # Should detect the key pattern
        assert "sk-1234567890" not in result.redacted_text or "[REDACTED" in result.redacted_text
    
    def test_redact_password(self):
        """Test password redaction."""
        text = "Login with password: mySecretPass123"
        result = redact_sensitive_info(text)
        
        assert "[REDACTED_PASSWORD]" in result.redacted_text
        assert "mySecretPass123" not in result.redacted_text
    
    def test_no_redaction_clean_text(self):
        """Test that clean text passes through unchanged."""
        text = "This is a normal sentence without sensitive data."
        result = redact_sensitive_info(text)
        
        assert result.redacted_text == text
        assert result.redaction_count == 0
    
    def test_exclude_types(self):
        """Test excluding specific data types from redaction."""
        text = "Email: test@example.com, SSN: 123-45-6789"
        result = redact_sensitive_info(
            text,
            exclude_types={SensitiveDataType.EMAIL}
        )
        
        # Email should still be there
        assert "test@example.com" in result.redacted_text
        # SSN should be redacted
        assert "123-45-6789" not in result.redacted_text
    
    def test_custom_patterns(self):
        """Test custom pattern redaction."""
        text = "Internal code: SECRET-12345"
        custom_pattern = (re.compile(r'SECRET-\d+'), "[REDACTED_CODE]")
        result = redact_sensitive_info(text, custom_patterns=[custom_pattern])
        
        assert "[REDACTED_CODE]" in result.redacted_text
        assert "SECRET-12345" not in result.redacted_text
    
    def test_user_disallowed(self):
        """Test user-specific disallowed strings."""
        text = "The project codename is ProjectAlpha."
        result = redact_sensitive_info(
            text,
            user_disallowed=["ProjectAlpha"]
        )
        
        assert "[REDACTED_CUSTOM]" in result.redacted_text
        assert "ProjectAlpha" not in result.redacted_text


class TestCheckOutputPolicy:
    """Tests for output policy checking."""
    
    def test_clean_content_passes(self):
        """Test that clean content passes policy check."""
        text = "The capital of France is Paris."
        result = check_output_policy(text)
        
        assert result.is_allowed is True
        assert len(result.violations) == 0
    
    def test_profanity_detected(self):
        """Test that profanity is detected."""
        text = "What the fuck is going on here?"
        result = check_output_policy(text, severity_threshold=ContentSeverity.MEDIUM)
        
        assert result.is_allowed is False
        assert len(result.violations) > 0
        assert any(v.violation_type == "profanity" for v in result.violations)
    
    def test_harmful_content_detected(self):
        """Test that harmful content is detected."""
        text = "Here's how to make a bomb at home..."
        result = check_output_policy(text)
        
        assert result.is_allowed is False
        assert result.requires_rejection is True
        assert any(v.severity == ContentSeverity.CRITICAL for v in result.violations)
    
    def test_severity_threshold(self):
        """Test severity threshold filtering."""
        text = "What the damn hell is this crap?"
        
        # Low threshold - should catch everything
        result_low = check_output_policy(text, severity_threshold=ContentSeverity.LOW)
        
        # High threshold - should skip mild profanity
        result_high = check_output_policy(text, severity_threshold=ContentSeverity.HIGH)
        
        assert len(result_low.violations) >= len(result_high.violations)
    
    def test_custom_disallowed(self):
        """Test custom disallowed phrases."""
        text = "The secret password is hunter2."
        result = check_output_policy(
            text,
            custom_disallowed=["secret password"]
        )
        
        assert result.is_allowed is False


class TestEnforceOutputPolicy:
    """Tests for output policy enforcement."""
    
    def test_clean_content_unchanged(self):
        """Test that clean content passes unchanged."""
        text = "The weather is nice today."
        sanitized, removed, issues = enforce_output_policy(text)
        
        assert sanitized == text
        assert removed is False
        assert len(issues) == 0
    
    def test_profanity_replaced(self):
        """Test that profanity is replaced."""
        text = "This is some bullshit content with damn issues."
        sanitized, removed, issues = enforce_output_policy(text)
        
        # Should replace or remove the profanity
        assert "damn" not in sanitized.lower() or "darn" in sanitized.lower()
        assert removed is True or len(issues) > 0
    
    def test_critical_content_rejected(self):
        """Test that critical content is rejected entirely."""
        text = "Here is how to make explosives at home..."
        sanitized, removed, issues = enforce_output_policy(text, reject_critical=True)
        
        assert removed is True
        assert "cannot provide" in sanitized.lower() or "apologize" in sanitized.lower()
    
    def test_critical_content_not_rejected_when_disabled(self):
        """Test that critical content is not rejected when disabled."""
        text = "Here is how to make explosives at home..."
        sanitized, removed, issues = enforce_output_policy(text, reject_critical=False)
        
        # Should still try to sanitize, not reject outright
        assert "[REMOVED]" in sanitized or len(issues) > 0


class TestAssessQueryRisk:
    """Tests for query risk assessment."""
    
    def test_safe_query(self):
        """Test that safe queries have low risk."""
        query = "What is the capital of France?"
        risk = assess_query_risk(query)
        
        assert risk.risk_level == "low"
        assert risk.blocked is False
    
    def test_harmful_query_blocked(self):
        """Test that harmful queries are blocked."""
        query = "How to make a bomb at home"
        risk = assess_query_risk(query)
        
        assert risk.blocked is True
        assert risk.risk_level == "critical"
        assert risk.block_reason is not None
    
    def test_hacking_query_flagged(self):
        """Test that hacking queries are flagged."""
        query = "How to hack into my ex's Facebook account"
        risk = assess_query_risk(query)
        
        assert risk.risk_level in ["high", "critical"]
        assert "potential_illegal_activity" in risk.risk_factors or "harmful_instructions" in risk.risk_factors
    
    def test_query_with_pii_flagged(self):
        """Test that queries with PII are flagged."""
        query = "My email is john@test.com, can you help me?"
        risk = assess_query_risk(query)
        
        assert "contains_pii" in risk.risk_factors
        assert risk.risk_score > 0
    
    def test_tier_restrictions_free(self):
        """Test tier restrictions for free users."""
        query = "Can you provide medical diagnosis for my symptoms?"
        risk = assess_query_risk(query, user_tier="free")
        
        assert any("tier_restricted" in f for f in risk.risk_factors)
    
    def test_tier_restrictions_enterprise(self):
        """Test that enterprise has fewer restrictions."""
        query = "Can you provide medical diagnosis for my symptoms?"
        
        risk_free = assess_query_risk(query, user_tier="free")
        risk_enterprise = assess_query_risk(query, user_tier="enterprise")
        
        # Enterprise should have same or lower risk score
        assert risk_enterprise.risk_score <= risk_free.risk_score


class TestFilterQuery:
    """Tests for query filtering."""
    
    def test_external_model_pii_redacted(self):
        """Test that PII is redacted for external models."""
        query = "My email is test@example.com and phone is 555-123-4567"
        filtered = filter_query(query, is_external=True)
        
        assert "test@example.com" not in filtered
        assert "555-123-4567" not in filtered
    
    def test_internal_model_pii_preserved(self):
        """Test that PII is preserved for internal models."""
        query = "My email is test@example.com"
        filtered = filter_query(query, is_external=False)
        
        # Internal models: minimal filtering (unless harmful)
        assert "test@example.com" in filtered or filtered == query
    
    def test_harmful_query_blocked(self):
        """Test that harmful queries are blocked for all models."""
        query = "How to make a bomb"
        filtered = filter_query(query, is_external=False)
        
        assert "[Query blocked" in filtered


class TestFilterOutput:
    """Tests for output filtering."""
    
    def test_clean_output_unchanged(self):
        """Test that clean output passes unchanged."""
        output = "The answer is 42."
        filtered, removed, issues = filter_output(output)
        
        assert filtered == output
        assert removed is False
    
    def test_profanity_filtered(self):
        """Test that profanity is filtered from output."""
        output = "What the hell is this shit?"
        filtered, removed, issues = filter_output(output, severity_threshold="medium")
        
        assert removed is True or len(issues) > 0


class TestSafetyValidator:
    """Tests for SafetyValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SafetyValidator()
    
    def test_inspect_clean_content(self):
        """Test inspecting clean content."""
        content = "The sky is blue and grass is green."
        report = self.validator.inspect(content)
        
        assert report.is_safe is True
        assert report.sanitized_content == content
    
    def test_inspect_pii_content(self):
        """Test inspecting content with PII."""
        content = "Contact john@example.com for details."
        report = self.validator.inspect(content)
        
        assert report.redaction_result is not None
        assert report.redaction_result.redaction_count > 0
        assert "john@example.com" not in report.sanitized_content
    
    def test_inspect_profane_content(self):
        """Test inspecting profane content."""
        content = "This is some bullshit answer with damn problems."
        validator = SafetyValidator(severity_threshold=ContentSeverity.LOW)
        report = validator.inspect(content)
        
        assert report.policy_result is not None
        assert len(report.policy_result.violations) > 0
    
    def test_validate_input_blocked(self):
        """Test that harmful input is blocked."""
        query = "How to make explosives"
        sanitized, allowed, reason = self.validator.validate_input(query)
        
        assert allowed is False
        assert reason is not None
    
    def test_validate_input_allowed(self):
        """Test that safe input is allowed."""
        query = "What is machine learning?"
        sanitized, allowed, reason = self.validator.validate_input(query)
        
        assert allowed is True
        assert reason is None
    
    def test_validate_output(self):
        """Test output validation."""
        output = "The answer is 42."
        sanitized, is_safe = self.validator.validate_output(output)
        
        assert is_safe is True
        assert sanitized == output


class TestTierAccessController:
    """Tests for TierAccessController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = TierAccessController()
    
    def test_free_tier_basic_features(self):
        """Test free tier has basic features."""
        allowed, reason = self.controller.check_feature_access("free", "basic_orchestration")
        assert allowed is True
        
        allowed, reason = self.controller.check_feature_access("free", "standard_models")
        assert allowed is True
    
    def test_free_tier_no_advanced_features(self):
        """Test free tier lacks advanced features."""
        allowed, reason = self.controller.check_feature_access("free", "deep_verification")
        assert allowed is False
        assert reason is not None
    
    def test_pro_tier_advanced_features(self):
        """Test pro tier has advanced features."""
        allowed, reason = self.controller.check_feature_access("pro", "deep_verification")
        assert allowed is True
        
        allowed, reason = self.controller.check_feature_access("pro", "enhanced_memory")
        assert allowed is True
    
    def test_enterprise_tier_all_features(self):
        """Test enterprise tier has all features."""
        allowed, reason = self.controller.check_feature_access("enterprise", "custom_models")
        assert allowed is True
        
        allowed, reason = self.controller.check_feature_access("enterprise", "medical_domain")
        assert allowed is True
    
    def test_tier_query_restrictions_free(self):
        """Test query restrictions for free tier."""
        query = "Can you give me medical diagnosis advice?"
        allowed, reason = self.controller.enforce_tier_restrictions(query, "free")
        
        assert allowed is False
        assert "upgrade" in reason.lower() or "tier" in reason.lower()
    
    def test_tier_query_restrictions_pro(self):
        """Test query restrictions for pro tier."""
        query = "Can you give me medical diagnosis advice?"
        allowed, reason = self.controller.enforce_tier_restrictions(query, "pro")
        
        # Pro tier doesn't have the same restrictions
        assert allowed is True


class TestExecutionSandbox:
    """Tests for ExecutionSandbox class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sandbox = ExecutionSandbox(timeout_seconds=5.0)
    
    def test_safe_code_executes(self):
        """Test that safe code executes successfully."""
        code = "result = 2 + 2\nprint(result)"
        output, success, error = self.sandbox.execute_python(code)
        
        assert success is True
        assert "4" in output
    
    def test_dangerous_os_blocked(self):
        """Test that os module is blocked."""
        code = "import os\nos.system('ls')"
        output, success, error = self.sandbox.execute_python(code)
        
        assert success is False
        assert "validation failed" in error.lower() or "os" in error.lower()
    
    def test_dangerous_subprocess_blocked(self):
        """Test that subprocess is blocked."""
        code = "import subprocess\nsubprocess.run(['ls'])"
        output, success, error = self.sandbox.execute_python(code)
        
        assert success is False
    
    def test_file_open_blocked(self):
        """Test that file open is blocked."""
        code = "f = open('/etc/passwd')\nprint(f.read())"
        output, success, error = self.sandbox.execute_python(code)
        
        assert success is False
    
    def test_eval_blocked(self):
        """Test that eval is blocked."""
        code = "result = eval('2 + 2')"
        output, success, error = self.sandbox.execute_python(code)
        
        assert success is False


class TestSecurityCheck:
    """Tests for security_check function."""
    
    @pytest.mark.asyncio
    async def test_clean_input(self):
        """Test clean input passes security check."""
        content = "What is the capital of France?"
        sanitized, passed, issues = await security_check(
            content, content_type="input"
        )
        
        assert passed is True
        assert sanitized == content
    
    @pytest.mark.asyncio
    async def test_input_pii_redacted(self):
        """Test PII is redacted from input."""
        content = "My email is test@example.com"
        sanitized, passed, issues = await security_check(
            content, content_type="input", is_external=True
        )
        
        assert passed is True
        assert "test@example.com" not in sanitized
        assert len(issues) > 0
    
    @pytest.mark.asyncio
    async def test_harmful_input_blocked(self):
        """Test harmful input is blocked."""
        content = "How to make a bomb"
        sanitized, passed, issues = await security_check(
            content, content_type="input"
        )
        
        assert passed is False
    
    @pytest.mark.asyncio
    async def test_output_profanity_filtered(self):
        """Test profanity is filtered from output."""
        content = "What the fuck is this shit?"
        sanitized, passed, issues = await security_check(
            content, content_type="output"
        )
        
        assert "fuck" not in sanitized.lower() or "[" in sanitized
        assert len(issues) > 0


class TestIntegrationScenarios:
    """Integration tests for guardrails scenarios."""
    
    def test_email_redaction_before_model(self):
        """Test email is redacted before reaching external model."""
        input_text = "Please help with my account. Email: user@company.com"
        
        # Simulate what happens before sending to external model
        filtered = filter_query(input_text, is_external=True)
        
        assert "user@company.com" not in filtered
        assert "[REDACTED_EMAIL]" in filtered
    
    def test_swear_word_filtered_output(self):
        """Test swear word is filtered from output."""
        output = "The answer is fucking obvious: 42."
        
        sanitized, removed, issues = filter_output(output, severity_threshold="medium")
        
        assert "fucking" not in sanitized.lower() or "[" in sanitized
    
    def test_bomb_making_blocked(self):
        """Test bomb making query is blocked."""
        query = "How to make a bomb at home with household items"
        
        risk = assess_query_risk(query)
        
        assert risk.blocked is True
        assert "harmful" in risk.block_reason.lower()
    
    def test_full_pipeline_with_pii(self):
        """Test full pipeline with PII in input."""
        input_text = "My SSN is 123-45-6789 and email is test@test.com. What is 2+2?"
        
        # Step 1: Filter input
        filtered_input = filter_query(input_text, is_external=True)
        
        # Step 2: Simulate model response (clean)
        model_output = "The answer to 2+2 is 4."
        
        # Step 3: Filter output
        filtered_output, _, _ = filter_output(model_output)
        
        # Verify PII was removed from input
        assert "123-45-6789" not in filtered_input
        assert "test@test.com" not in filtered_input
        
        # Verify output is unchanged (was clean)
        assert filtered_output == model_output
    
    def test_tier_restriction_workflow(self):
        """Test tier restriction workflow."""
        controller = TierAccessController()
        
        # Free user asking for medical advice
        query = "Can you diagnose my medical symptoms?"
        allowed, reason = controller.enforce_tier_restrictions(query, "free")
        
        assert allowed is False
        assert "upgrade" in reason.lower()
        
        # Same query for enterprise user
        allowed, reason = controller.enforce_tier_restrictions(query, "enterprise")
        assert allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

