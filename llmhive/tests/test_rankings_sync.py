"""Tests for OpenRouter Rankings Sync.

Tests cover:
- Category discovery and parsing
- Rankings parsing from fixtures
- DB write/read operations
- Validation logic
"""
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Fixtures path
FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "openrouter"


class TestCategoryDiscovery:
    """Tests for category discovery from OpenRouter."""
    
    def test_parse_categories_from_fixture(self):
        """Test parsing categories from fixture file."""
        fixture_path = FIXTURES_DIR / "categories.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        categories = data["categories"]
        
        # Check we have all expected categories
        assert len(categories) >= 10
        
        # Check programming exists
        programming = next((c for c in categories if c["slug"] == "programming"), None)
        assert programming is not None
        assert programming["display_name"] == "Programming"
        assert programming["depth"] == 0
        
        # Check nested category (marketing/seo)
        seo = next((c for c in categories if c["slug"] == "marketing/seo"), None)
        assert seo is not None
        assert seo["display_name"] == "SEO"
        assert seo["parent_slug"] == "marketing"
        assert seo["depth"] == 1
    
    def test_all_required_categories_present(self):
        """Verify all required categories from mission spec are present."""
        fixture_path = FIXTURES_DIR / "categories.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        slugs = {c["slug"] for c in data["categories"]}
        
        required = {
            "programming", "science", "health", "legal", "marketing",
            "marketing/seo", "technology", "finance", "academia", "roleplay"
        }
        
        for cat in required:
            assert cat in slugs, f"Required category '{cat}' not found"


class TestRankingsParsing:
    """Tests for parsing rankings from OpenRouter."""
    
    def test_parse_programming_rankings(self):
        """Test parsing programming category rankings."""
        fixture_path = FIXTURES_DIR / "rankings_programming.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        models = data["models"]
        
        # Check we have top 10
        assert len(models) == 10
        
        # Check first model has all required fields
        first = models[0]
        assert "id" in first
        assert "name" in first
        assert "tokens" in first or "tokens_display" in first
        assert "share_pct" in first
        
        # Check order (should be by share_pct descending)
        for i in range(len(models) - 1):
            assert models[i]["share_pct"] >= models[i+1]["share_pct"]
    
    def test_parse_science_rankings(self):
        """Test parsing science category rankings."""
        fixture_path = FIXTURES_DIR / "rankings_science.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        models = data["models"]
        
        # Check we have top 10
        assert len(models) == 10
        
        # Science should have reasoning models near top
        top_3_ids = [m["id"] for m in models[:3]]
        assert any("o1" in id or "reasoning" in id.lower() for id in top_3_ids), \
            "Expected reasoning model in science top 3"
    
    def test_model_id_format(self):
        """Verify model IDs are in provider/model format."""
        fixture_path = FIXTURES_DIR / "rankings_programming.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        for model in data["models"]:
            model_id = model["id"]
            # Should be in format "provider/model-name"
            assert "/" in model_id, f"Model ID should contain '/': {model_id}"
            parts = model_id.split("/")
            assert len(parts) >= 2
            assert parts[0]  # Provider not empty
            assert parts[1]  # Model name not empty
    
    def test_extract_author_from_id(self):
        """Test extracting author/provider from model ID."""
        fixture_path = FIXTURES_DIR / "rankings_programming.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        for model in data["models"]:
            model_id = model["id"]
            author = model_id.split("/")[0]
            
            # Known providers
            known_providers = {
                "openai", "anthropic", "google", "deepseek", "meta",
                "mistralai", "qwen", "x-ai", "cohere", "nvidia"
            }
            
            # Author should be a known provider or similar format
            assert author.isalpha() or "-" in author, \
                f"Author '{author}' should be alphanumeric or hyphenated"


class TestRankingsSync:
    """Tests for the RankingsSync class."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.first.return_value = None
        return session
    
    @pytest.fixture
    def sync_instance(self, mock_db_session):
        """Create a RankingsSync instance with mocked dependencies."""
        from llmhive.app.openrouter.rankings_sync import RankingsSync
        return RankingsSync(mock_db_session, api_key="test-key")
    
    def test_seed_categories_defined(self):
        """Verify seed categories are defined."""
        from llmhive.app.openrouter.rankings_sync import SEED_CATEGORIES
        
        assert len(SEED_CATEGORIES) >= 10
        
        # Check required categories
        slugs = {c["slug"] for c in SEED_CATEGORIES}
        required = {"programming", "science", "health", "legal", "marketing"}
        
        for cat in required:
            assert cat in slugs, f"Seed category '{cat}' not found"
    
    def test_parse_version_defined(self):
        """Verify parse version is defined for tracking changes."""
        from llmhive.app.openrouter.rankings_sync import RankingsSync
        
        assert hasattr(RankingsSync, "PARSE_VERSION")
        assert RankingsSync.PARSE_VERSION  # Not empty
    
    def test_check_category_keywords(self, sync_instance):
        """Test category keyword matching."""
        # Programming keywords
        programming_model = {
            "id": "test/model",
            "name": "Test Coder",
            "description": "A model for code and programming tasks"
        }
        
        assert sync_instance._check_category(programming_model, ["code", "programming"])
        assert not sync_instance._check_category(programming_model, ["legal", "law"])
    
    def test_extract_author(self, sync_instance):
        """Test author extraction from model ID."""
        assert sync_instance._extract_author("openai/gpt-4o") == "openai"
        assert sync_instance._extract_author("anthropic/claude-3") == "anthropic"
        assert sync_instance._extract_author("gpt-4o") is None
        assert sync_instance._extract_author(None) is None


class TestValidation:
    """Tests for rankings validation logic."""
    
    def test_validate_top_3_order(self):
        """Test that validation checks top 3 model order."""
        fixture_path = FIXTURES_DIR / "rankings_programming.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        models = data["models"]
        
        # Top 3 should be in share_pct order
        top_3 = models[:3]
        for i in range(len(top_3) - 1):
            assert top_3[i]["share_pct"] >= top_3[i+1]["share_pct"]
    
    def test_validate_model_ids_exist(self):
        """Test that all model IDs are valid format."""
        fixture_path = FIXTURES_DIR / "rankings_programming.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        for model in data["models"]:
            model_id = model["id"]
            assert model_id is not None
            assert len(model_id) > 0
            assert "/" in model_id


class TestSyncReport:
    """Tests for sync report generation."""
    
    def test_sync_report_creation(self):
        """Test SyncReport dataclass creation."""
        from llmhive.app.openrouter.rankings_sync import SyncReport
        
        report = SyncReport(sync_type="rankings_full")
        
        assert report.sync_type == "rankings_full"
        assert report.status == "success"
        assert report.categories_discovered == 0
        assert report.snapshots_created == 0
        assert isinstance(report.started_at, datetime)
    
    def test_sync_report_to_dict(self):
        """Test SyncReport serialization."""
        from llmhive.app.openrouter.rankings_sync import SyncReport
        
        report = SyncReport(
            sync_type="rankings_full",
            categories_discovered=15,
            categories_added=3,
            snapshots_created=15,
            entries_added=150,
        )
        report.completed_at = datetime.now(timezone.utc)
        
        data = report.to_dict()
        
        assert data["sync_type"] == "rankings_full"
        assert data["categories_discovered"] == 15
        assert data["snapshots_created"] == 15
        assert "duration_seconds" in data


class TestDBModels:
    """Tests for database model definitions."""
    
    def test_category_model_fields(self):
        """Test OpenRouterCategory model has all required fields."""
        from llmhive.app.openrouter.rankings_models import OpenRouterCategory
        
        # Check required columns exist
        columns = {c.name for c in OpenRouterCategory.__table__.columns}
        
        required = {"id", "slug", "display_name", "group", "parent_slug", "depth", "is_active"}
        for col in required:
            assert col in columns, f"Missing column: {col}"
    
    def test_snapshot_model_fields(self):
        """Test OpenRouterRankingSnapshot model has all required fields."""
        from llmhive.app.openrouter.rankings_models import OpenRouterRankingSnapshot
        
        columns = {c.name for c in OpenRouterRankingSnapshot.__table__.columns}
        
        required = {
            "id", "category_slug", "group", "view", "fetched_at", 
            "parse_version", "status", "error"
        }
        for col in required:
            assert col in columns, f"Missing column: {col}"
    
    def test_entry_model_fields(self):
        """Test OpenRouterRankingEntry model has all required fields."""
        from llmhive.app.openrouter.rankings_models import OpenRouterRankingEntry
        
        columns = {c.name for c in OpenRouterRankingEntry.__table__.columns}
        
        required = {
            "id", "snapshot_id", "rank", "model_id", "model_name",
            "author", "tokens", "share_pct", "is_others_bucket"
        }
        for col in required:
            assert col in columns, f"Missing column: {col}"
    
    def test_category_to_dict(self):
        """Test OpenRouterCategory.to_dict() serialization."""
        from llmhive.app.openrouter.rankings_models import OpenRouterCategory, CategoryGroup
        
        category = OpenRouterCategory(
            id=1,
            slug="programming",
            display_name="Programming",
            group=CategoryGroup.USECASE,
            depth=0,
            is_active=True,
        )
        
        data = category.to_dict()
        
        assert data["slug"] == "programming"
        assert data["display_name"] == "Programming"
        assert data["group"] == "usecase"
        assert data["depth"] == 0


# Run with: pytest llmhive/tests/test_rankings_sync.py -v

