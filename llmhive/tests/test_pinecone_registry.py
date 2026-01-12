"""Tests for Pinecone Registry module.

These tests verify:
1. Registry initialization logic
2. Host-based connection handling
3. Fallback behavior in dev mode
4. Health status reporting
5. Region validation
6. Configuration validation
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llmhive.app.knowledge.pinecone_registry import (
    PineconeRegistry,
    PineconeRegistryError,
    IndexKind,
    INDEX_CONFIGS,
    EXPECTED_REGION,
    extract_region_from_host,
    get_pinecone_registry,
    reset_registry,
    is_pinecone_available,
)


class TestExtractRegionFromHost:
    """Tests for extract_region_from_host function."""
    
    def test_extract_region_us_east_1(self):
        """Should extract us-east-1 from AWS host."""
        host = "llmhive-memory-abc123.svc.us-east-1.pinecone.io"
        assert extract_region_from_host(host) == "us-east-1"
    
    def test_extract_region_us_central1_gcp(self):
        """Should extract us-central1-gcp from GCP host."""
        host = "index-name.svc.us-central1-gcp.pinecone.io"
        assert extract_region_from_host(host) == "us-central1-gcp"
    
    def test_extract_region_with_https(self):
        """Should handle https:// prefix."""
        host = "https://llmhive-kb-xyz.svc.eu-west-1.pinecone.io"
        assert extract_region_from_host(host) == "eu-west-1"
    
    def test_extract_region_empty_host(self):
        """Should return None for empty host."""
        assert extract_region_from_host("") is None
        assert extract_region_from_host(None) is None
    
    def test_extract_region_invalid_format(self):
        """Should return None for invalid format."""
        assert extract_region_from_host("not-a-valid-host") is None
        assert extract_region_from_host("example.com") is None
    
    def test_extract_region_serverless_aped(self):
        """Should return 'serverless' for Pinecone serverless URLs (aped-xxxx-xxxx)."""
        host = "llmhive-orchestrator-kb-aped-4627-b74a.svc.aped-4627-b74a.pinecone.io"
        assert extract_region_from_host(host) == "serverless"
    
    def test_extract_region_serverless_with_https(self):
        """Should handle https:// prefix for serverless URLs."""
        host = "https://llmhive-memory-aped-1234-abcd.svc.aped-1234-abcd.pinecone.io"
        assert extract_region_from_host(host) == "serverless"
    
    def test_extract_region_serverless_aws_project(self):
        """Should return 'serverless' for AWS serverless project IDs."""
        host = "index-name-aws-12ab-34cd.svc.aws-12ab-34cd.pinecone.io"
        assert extract_region_from_host(host) == "serverless"
    
    def test_extract_region_preserves_real_regions(self):
        """Should still correctly identify real region URLs."""
        # AWS regions
        assert extract_region_from_host("idx.svc.us-east-1.pinecone.io") == "us-east-1"
        assert extract_region_from_host("idx.svc.us-west-2.pinecone.io") == "us-west-2"
        assert extract_region_from_host("idx.svc.eu-west-1.pinecone.io") == "eu-west-1"
        assert extract_region_from_host("idx.svc.ap-southeast-1.pinecone.io") == "ap-southeast-1"
        # GCP regions
        assert extract_region_from_host("idx.svc.us-central1-gcp.pinecone.io") == "us-central1-gcp"
        assert extract_region_from_host("idx.svc.europe-west1-gcp.pinecone.io") == "europe-west1-gcp"


class TestIndexKind:
    """Tests for IndexKind enum."""
    
    def test_all_index_kinds_have_config(self):
        """Every IndexKind should have a corresponding config."""
        for kind in IndexKind:
            assert kind in INDEX_CONFIGS, f"Missing config for {kind}"
    
    def test_required_indexes(self):
        """Required indexes should be marked as such."""
        required = [
            IndexKind.ORCHESTRATOR_KB,
            IndexKind.MODEL_KNOWLEDGE,
            IndexKind.MEMORY,
            IndexKind.RLHF_FEEDBACK,
        ]
        for kind in required:
            assert INDEX_CONFIGS[kind].required, f"{kind} should be required"
    
    def test_optional_indexes(self):
        """Optional indexes should be marked as such."""
        optional = [IndexKind.AGENTIC_TEST]
        for kind in optional:
            assert not INDEX_CONFIGS[kind].required, f"{kind} should be optional"
    
    def test_answer_cache_reuses_orchestrator_kb(self):
        """ANSWER_CACHE should reuse ORCHESTRATOR_KB's host env var."""
        assert INDEX_CONFIGS[IndexKind.ANSWER_CACHE].host_env_var == \
               INDEX_CONFIGS[IndexKind.ORCHESTRATOR_KB].host_env_var


class TestPineconeRegistry:
    """Tests for PineconeRegistry class."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the global registry before each test."""
        reset_registry()
        yield
        reset_registry()
    
    def test_init_without_api_key(self):
        """Registry should initialize but not be available without API key."""
        with patch.dict(os.environ, {}, clear=True):
            registry = PineconeRegistry()
            assert not registry.is_available
    
    def test_init_without_pinecone_sdk(self):
        """Registry should handle missing Pinecone SDK gracefully."""
        with patch.dict(os.environ, {"PINECONE_API_KEY": "test-key"}):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', False):
                reset_registry()
                registry = PineconeRegistry()
                assert not registry.is_available
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_init_with_api_key(self, mock_pinecone):
        """Registry should initialize successfully with API key."""
        mock_pinecone.return_value = Mock()
        
        with patch.dict(os.environ, {"PINECONE_API_KEY": "test-key"}):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                assert registry.is_available
                mock_pinecone.assert_called_once_with(api_key="test-key")
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_get_index_with_host(self, mock_pinecone):
        """Should connect via host when host env var is set."""
        mock_client = Mock()
        mock_index = Mock()
        mock_client.Index.return_value = mock_index
        mock_pinecone.return_value = mock_client
        
        env = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_HOST_MEMORY": "https://memory-index.svc.us-east-1.pinecone.io",
        }
        
        with patch.dict(os.environ, env, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                index = registry.get_index(IndexKind.MEMORY)
                
                assert index is mock_index
                mock_client.Index.assert_called_with(
                    host="https://memory-index.svc.us-east-1.pinecone.io"
                )
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_get_index_fallback_dev_mode(self, mock_pinecone):
        """Should fallback to name-based connection in dev mode."""
        mock_client = Mock()
        mock_index = Mock()
        mock_client.Index.return_value = mock_index
        mock_client.has_index.return_value = True
        mock_pinecone.return_value = mock_client
        
        env = {
            "PINECONE_API_KEY": "test-key",
            "REQUIRE_PINECONE_HOSTS": "false",
        }
        
        with patch.dict(os.environ, env, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                index = registry.get_index(IndexKind.MEMORY)
                
                assert index is mock_index
                mock_client.has_index.assert_called_with("llmhive-memory")
                mock_client.Index.assert_called_with(name="llmhive-memory")
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_get_index_fail_fast_production(self, mock_pinecone):
        """Should fail fast in production when host is missing."""
        mock_pinecone.return_value = Mock()
        
        env = {
            "PINECONE_API_KEY": "test-key",
            "REQUIRE_PINECONE_HOSTS": "true",
        }
        
        with patch.dict(os.environ, env, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                
                with pytest.raises(PineconeRegistryError) as exc_info:
                    registry.get_index(IndexKind.MEMORY)
                
                assert "REQUIRE_PINECONE_HOSTS=true" in str(exc_info.value)
                assert "PINECONE_HOST_MEMORY" in str(exc_info.value)
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_get_index_caching(self, mock_pinecone):
        """Should cache index handles after first connection."""
        mock_client = Mock()
        mock_index = Mock()
        mock_client.Index.return_value = mock_index
        mock_pinecone.return_value = mock_client
        
        env = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_HOST_MEMORY": "https://memory.svc.us-east-1.pinecone.io",
        }
        
        with patch.dict(os.environ, env, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                
                # First call
                index1 = registry.get_index(IndexKind.MEMORY)
                # Second call
                index2 = registry.get_index(IndexKind.MEMORY)
                
                assert index1 is index2
                # Should only connect once
                assert mock_client.Index.call_count == 1


class TestHealthStatus:
    """Tests for health status reporting."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        reset_registry()
        yield
        reset_registry()
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_health_status_structure(self, mock_pinecone):
        """Health status should have expected structure."""
        mock_pinecone.return_value = Mock()
        
        with patch.dict(os.environ, {"PINECONE_API_KEY": "test-key"}):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                status = registry.get_health_status()
                
                assert "sdk_available" in status
                assert "api_key_set" in status
                assert "client_initialized" in status
                assert "require_hosts" in status
                assert "expected_region" in status
                assert "indexes" in status
                assert "region_warnings" in status
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_health_status_detects_region_mismatch(self, mock_pinecone):
        """Should detect region mismatch in hosts."""
        mock_pinecone.return_value = Mock()
        
        env = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_HOST_MEMORY": "https://mem.svc.us-central1-gcp.pinecone.io",
            "PINECONE_EXPECTED_REGION": "us-east-1",
        }
        
        with patch.dict(os.environ, env, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                # Need to re-import to get new EXPECTED_REGION
                import importlib
                import llmhive.app.knowledge.pinecone_registry as registry_module
                importlib.reload(registry_module)
                
                registry = registry_module.PineconeRegistry()
                status = registry.get_health_status()
                
                # Should have region warning
                memory_status = status["indexes"].get("memory", {})
                assert memory_status.get("detected_region") == "us-central1-gcp"


class TestConfigurationValidation:
    """Tests for configuration validation."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        reset_registry()
        yield
        reset_registry()
    
    def test_validation_without_api_key(self):
        """Validation should fail without API key."""
        with patch.dict(os.environ, {}, clear=True):
            registry = PineconeRegistry()
            is_valid, errors = registry.validate_configuration()
            
            assert not is_valid
            assert any("PINECONE_API_KEY" in e for e in errors)
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_validation_without_required_hosts(self, mock_pinecone):
        """Validation should report missing required hosts."""
        mock_pinecone.return_value = Mock()
        
        with patch.dict(os.environ, {"PINECONE_API_KEY": "test-key"}, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                is_valid, errors = registry.validate_configuration()
                
                # Should report missing required hosts
                assert not is_valid
                assert any("PINECONE_HOST_MEMORY" in e for e in errors)
                assert any("PINECONE_HOST_ORCHESTRATOR_KB" in e for e in errors)
    
    @patch('llmhive.app.knowledge.pinecone_registry.Pinecone')
    def test_validation_detects_multiple_regions(self, mock_pinecone):
        """Validation should warn about multiple regions."""
        mock_pinecone.return_value = Mock()
        
        env = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_HOST_ORCHESTRATOR_KB": "https://kb.svc.us-east-1.pinecone.io",
            "PINECONE_HOST_MODEL_KNOWLEDGE": "https://model.svc.us-east-1.pinecone.io",
            "PINECONE_HOST_MEMORY": "https://mem.svc.us-central1-gcp.pinecone.io",  # Different!
            "PINECONE_HOST_RLHF_FEEDBACK": "https://rlhf.svc.us-east-1.pinecone.io",
        }
        
        with patch.dict(os.environ, env, clear=True):
            with patch('llmhive.app.knowledge.pinecone_registry.PINECONE_SDK_AVAILABLE', True):
                reset_registry()
                registry = PineconeRegistry()
                is_valid, errors = registry.validate_configuration()
                
                # Should detect multiple regions
                assert not is_valid
                assert any("Multiple regions" in e for e in errors)


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        reset_registry()
        yield
        reset_registry()
    
    def test_get_pinecone_registry_singleton(self):
        """get_pinecone_registry should return same instance."""
        registry1 = get_pinecone_registry()
        registry2 = get_pinecone_registry()
        assert registry1 is registry2
    
    def test_reset_registry(self):
        """reset_registry should create new instance on next call."""
        registry1 = get_pinecone_registry()
        reset_registry()
        registry2 = get_pinecone_registry()
        assert registry1 is not registry2
    
    def test_is_pinecone_available_no_key(self):
        """is_pinecone_available should return False without API key."""
        with patch.dict(os.environ, {}, clear=True):
            reset_registry()
            assert not is_pinecone_available()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

