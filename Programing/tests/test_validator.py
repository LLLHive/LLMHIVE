import pytest
from app.validator import Validator


def test_validate_output_passes():
    """Test that valid output passes validation."""
    output = {"content": "Valid content"}
    assert Validator.validate_output(output) is True


def test_validate_output_fails():
    """Test that output with disallowed content fails validation."""
    output = {"disallowed_content": "Bad content"}
    assert Validator.validate_output(output) is False


def test_format_check_passes():
    """Test that output with format passes format check."""
    output = {"format": "json"}
    assert Validator.format_check(output) is True


def test_format_check_fails():
    """Test that output without format fails format check."""
    output = {"content": "some content"}
    assert Validator.format_check(output) is False
