"""Tests for benchmark suite YAML schema validation.

Ensures all benchmark suite files are properly formatted with required fields.
"""
import os
import pytest
import yaml
from pathlib import Path


# Find benchmark suites directory
SUITES_DIR = Path(__file__).parent.parent.parent / "benchmarks" / "suites"


def get_suite_files():
    """Get all YAML suite files."""
    if not SUITES_DIR.exists():
        return []
    return list(SUITES_DIR.glob("*.yaml")) + list(SUITES_DIR.glob("*.yml"))


class TestSuiteSchema:
    """Test suite schema validation."""
    
    @pytest.fixture
    def complex_reasoning_suite(self):
        """Load the main complex reasoning suite."""
        suite_path = SUITES_DIR / "complex_reasoning_v1.yaml"
        if not suite_path.exists():
            pytest.skip("Complex reasoning suite not found")
        
        with open(suite_path, 'r') as f:
            return yaml.safe_load(f)
    
    def test_suite_has_metadata(self, complex_reasoning_suite):
        """Suite should have metadata section."""
        assert "metadata" in complex_reasoning_suite
        metadata = complex_reasoning_suite["metadata"]
        
        assert "suite_name" in metadata
        assert "version" in metadata
        assert "categories" in metadata
    
    def test_suite_has_prompts(self, complex_reasoning_suite):
        """Suite should have prompts list."""
        assert "prompts" in complex_reasoning_suite
        assert len(complex_reasoning_suite["prompts"]) > 0
    
    def test_all_prompts_have_required_fields(self, complex_reasoning_suite):
        """Each prompt should have required fields."""
        required_fields = ["id", "category", "prompt"]
        
        for prompt in complex_reasoning_suite["prompts"]:
            for field in required_fields:
                assert field in prompt, f"Prompt {prompt.get('id', 'UNKNOWN')} missing {field}"
    
    def test_all_prompts_have_scoring_config(self, complex_reasoning_suite):
        """Each prompt should have scoring configuration."""
        for prompt in complex_reasoning_suite["prompts"]:
            prompt_id = prompt.get("id", "UNKNOWN")
            
            # Should have scoring section
            assert "scoring" in prompt, f"Prompt {prompt_id} missing scoring config"
            scoring = prompt["scoring"]
            
            # Should have weights
            assert "objective_weight" in scoring or "rubric_weight" in scoring, \
                f"Prompt {prompt_id} missing scoring weights"
    
    def test_prompts_have_unique_ids(self, complex_reasoning_suite):
        """All prompt IDs should be unique."""
        ids = [p["id"] for p in complex_reasoning_suite["prompts"]]
        assert len(ids) == len(set(ids)), "Duplicate prompt IDs found"
    
    def test_expected_fields_are_valid(self, complex_reasoning_suite):
        """Expected fields should use valid types."""
        valid_expected_types = [
            "expected_contains",
            "expected_regex",
            "expected_not_contains",
            "expected_numeric",
            "expected_jsonschema",
        ]
        
        for prompt in complex_reasoning_suite["prompts"]:
            if "expected" in prompt:
                expected = prompt["expected"]
                for key in expected:
                    assert key in valid_expected_types, \
                        f"Prompt {prompt['id']} has invalid expected type: {key}"
    
    def test_numeric_expected_has_required_fields(self, complex_reasoning_suite):
        """Numeric expected configs should have value and tolerance."""
        for prompt in complex_reasoning_suite["prompts"]:
            expected = prompt.get("expected", {})
            numeric = expected.get("expected_numeric")
            
            if numeric:
                assert "value" in numeric, \
                    f"Prompt {prompt['id']} numeric expected missing 'value'"
    
    def test_categories_are_consistent(self, complex_reasoning_suite):
        """Prompt categories should match metadata categories."""
        metadata_categories = set(complex_reasoning_suite["metadata"]["categories"])
        prompt_categories = set(p["category"] for p in complex_reasoning_suite["prompts"])
        
        # All prompt categories should be in metadata
        for cat in prompt_categories:
            # Allow subcategories (e.g., "multi_hop_reasoning" matches "multi_hop")
            assert any(
                cat.startswith(mc) or mc.startswith(cat)
                for mc in metadata_categories
            ), f"Category '{cat}' not in metadata categories"
    
    def test_critical_prompts_exist(self, complex_reasoning_suite):
        """Suite should have some critical prompts marked."""
        critical_count = sum(
            1 for p in complex_reasoning_suite["prompts"]
            if p.get("scoring", {}).get("critical", False)
        )
        
        assert critical_count > 0, "Suite should have at least one critical prompt"
    
    def test_suite_has_minimum_prompts(self, complex_reasoning_suite):
        """Suite should have minimum number of prompts."""
        assert len(complex_reasoning_suite["prompts"]) >= 30, \
            "Suite should have at least 30 prompts"


@pytest.mark.parametrize("suite_file", get_suite_files())
def test_suite_file_is_valid_yaml(suite_file):
    """All suite files should be valid YAML."""
    with open(suite_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data is not None
    assert isinstance(data, dict)

