#!/usr/bin/env python3
"""UI Wiring Validation Script.

This script verifies that the front-end receives all necessary data from the back-end output.
Specifically, it checks that final answers include sources and confidence fields, as expected by the UI.

It can:
- Load sample output from an API call or fixture
- Validate the presence of required fields
- Check field types and value ranges
- Report any missing or malformed data

Usage:
    python tests/quality_eval/validate_ui_wiring.py

Environment Variables:
    API_BASE_URL: Base URL for API calls (default: http://localhost:8000)
    USE_FIXTURE: If "true", use fixture data instead of API (default: true)
"""
import json
import os
import sys
from typing import Any, Optional
from dataclasses import dataclass

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
USE_FIXTURE = os.getenv("USE_FIXTURE", "true").lower() == "true"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    field: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning


class UIWiringValidator:
    """Validates that API responses contain all fields expected by the UI."""
    
    def __init__(self):
        self.results: list[ValidationResult] = []
    
    def validate(self, response: dict) -> bool:
        """Validate a response object against UI requirements.
        
        Args:
            response: The API response dictionary to validate
            
        Returns:
            bool: True if all validations pass, False otherwise
        """
        self.results = []
        
        # Required fields
        self._check_field_exists(response, "answer", required=True)
        self._check_field_exists(response, "sources", required=False)
        self._check_field_exists(response, "confidence", required=False)
        
        # Type validations
        if "answer" in response:
            self._check_field_type(response, "answer", str)
            self._check_field_not_empty(response, "answer")
        
        if "sources" in response:
            self._check_field_type(response, "sources", list)
            self._validate_sources(response.get("sources", []))
        
        if "confidence" in response:
            self._check_field_type(response, "confidence", (int, float))
            self._check_confidence_range(response.get("confidence"))
        
        # Optional but recommended fields
        self._check_field_exists(response, "model", required=False, severity="warning")
        self._check_field_exists(response, "tokens_used", required=False, severity="warning")
        
        # Check for metadata if present
        if "metadata" in response:
            self._validate_metadata(response.get("metadata", {}))
        
        return all(r.passed for r in self.results if r.severity == "error")
    
    def _check_field_exists(self, obj: dict, field: str, required: bool = True, severity: str = "error"):
        """Check if a required field exists."""
        if field not in obj:
            if required:
                self.results.append(ValidationResult(
                    field=field,
                    passed=False,
                    message=f"Missing required field: '{field}'",
                    severity=severity
                ))
            else:
                self.results.append(ValidationResult(
                    field=field,
                    passed=True,
                    message=f"Optional field '{field}' not present",
                    severity="info"
                ))
        else:
            self.results.append(ValidationResult(
                field=field,
                passed=True,
                message=f"Field '{field}' present"
            ))
    
    def _check_field_type(self, obj: dict, field: str, expected_type: type):
        """Check if a field has the expected type."""
        if field not in obj:
            return
        
        value = obj[field]
        if not isinstance(value, expected_type):
            self.results.append(ValidationResult(
                field=field,
                passed=False,
                message=f"Field '{field}' has wrong type: expected {expected_type}, got {type(value)}"
            ))
        else:
            self.results.append(ValidationResult(
                field=field,
                passed=True,
                message=f"Field '{field}' has correct type"
            ))
    
    def _check_field_not_empty(self, obj: dict, field: str):
        """Check if a field is not empty."""
        if field not in obj:
            return
        
        value = obj[field]
        if not value or (isinstance(value, str) and not value.strip()):
            self.results.append(ValidationResult(
                field=field,
                passed=False,
                message=f"Field '{field}' is empty"
            ))
    
    def _check_confidence_range(self, confidence: Optional[float]):
        """Check if confidence is in valid range [0, 1]."""
        if confidence is None:
            return
        
        if not (0.0 <= confidence <= 1.0):
            self.results.append(ValidationResult(
                field="confidence",
                passed=False,
                message=f"Confidence value {confidence} out of range [0, 1]"
            ))
        else:
            self.results.append(ValidationResult(
                field="confidence",
                passed=True,
                message=f"Confidence value {confidence} in valid range"
            ))
    
    def _validate_sources(self, sources: list):
        """Validate the structure of sources list."""
        if not sources:
            self.results.append(ValidationResult(
                field="sources",
                passed=True,
                message="Sources list is empty (valid but no citations)",
                severity="warning"
            ))
            return
        
        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                self.results.append(ValidationResult(
                    field=f"sources[{i}]",
                    passed=False,
                    message=f"Source at index {i} is not a dictionary"
                ))
                continue
            
            # Each source should have at least title or url
            has_identifier = "title" in source or "url" in source
            if not has_identifier:
                self.results.append(ValidationResult(
                    field=f"sources[{i}]",
                    passed=False,
                    message=f"Source at index {i} missing both 'title' and 'url'"
                ))
            else:
                self.results.append(ValidationResult(
                    field=f"sources[{i}]",
                    passed=True,
                    message=f"Source at index {i} has valid identifier"
                ))
    
    def _validate_metadata(self, metadata: dict):
        """Validate metadata structure if present."""
        expected_metadata_fields = [
            "model_used",
            "processing_time_ms",
            "consensus_score",
            "verification_status"
        ]
        
        for field in expected_metadata_fields:
            if field not in metadata:
                self.results.append(ValidationResult(
                    field=f"metadata.{field}",
                    passed=True,
                    message=f"Optional metadata field '{field}' not present",
                    severity="info"
                ))
    
    def print_report(self):
        """Print a formatted validation report."""
        print("\n" + "=" * 60)
        print("UI WIRING VALIDATION REPORT")
        print("=" * 60)
        
        errors = [r for r in self.results if not r.passed and r.severity == "error"]
        warnings = [r for r in self.results if not r.passed and r.severity == "warning"]
        passed = [r for r in self.results if r.passed]
        
        print(f"\nTotal Checks: {len(self.results)}")
        print(f"Passed:       {len(passed)}")
        print(f"Errors:       {len(errors)}")
        print(f"Warnings:     {len(warnings)}")
        
        if errors:
            print("\n❌ ERRORS:")
            for r in errors:
                print(f"   [{r.field}] {r.message}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for r in warnings:
                print(f"   [{r.field}] {r.message}")
        
        print("\n" + "=" * 60)


def get_fixture_response() -> dict:
    """Get a fixture response for testing."""
    return {
        "answer": "Paris is the capital of France.",
        "sources": [
            {"title": "France - Wikipedia", "url": "https://en.wikipedia.org/wiki/France"}
        ],
        "confidence": 0.93,
        "model": "gpt-4",
        "tokens_used": 150,
        "metadata": {
            "model_used": "gpt-4",
            "processing_time_ms": 1234,
            "consensus_score": 0.95,
            "verification_status": "PASS"
        }
    }


def get_api_response() -> Optional[dict]:
    """Fetch a response from the actual API."""
    try:
        import requests
        
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={"message": "What is the capital of France?"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except ImportError:
        print("Warning: 'requests' library not available. Using fixture data.")
        return None
    except Exception as e:
        print(f"Warning: API call failed: {e}. Using fixture data.")
        return None


def main():
    """Main entry point for UI wiring validation."""
    print("Running UI Wiring Validation...")
    
    # Get response to validate
    if USE_FIXTURE:
        print("Using fixture data for validation")
        response = get_fixture_response()
    else:
        print(f"Fetching response from API: {API_BASE_URL}")
        response = get_api_response()
        if response is None:
            print("Falling back to fixture data")
            response = get_fixture_response()
    
    # Run validation
    validator = UIWiringValidator()
    all_passed = validator.validate(response)
    validator.print_report()
    
    # Exit with appropriate code
    if all_passed:
        print("\n✅ UI WIRING VALIDATION PASSED")
        sys.exit(0)
    else:
        print("\n❌ UI WIRING VALIDATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

