"""Tests for DevOps tool integrations: GitHub and GCP connectors."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from llmhive.app.services.github_connector import (
    GitHubConnector,
    GitHubFile,
    GitHubIssue,
)
from llmhive.app.services.gcp_connector import (
    GCPConnector,
    BigQueryResult,
    CloudLogEntry,
)


class TestGitHubConnector:
    """Tests for GitHub connector."""
    
    def test_github_connector_disabled_no_token(self):
        """Test that connector is disabled when no token is provided."""
        connector = GitHubConnector(token=None)
        assert not connector.enabled, "Connector should be disabled without token"
    
    def test_github_connector_enabled_with_token(self):
        """Test that connector is enabled when token is provided."""
        with patch("llmhive.app.services.github_connector.PYGITHUB_AVAILABLE", True):
            with patch("llmhive.app.services.github_connector.Github") as mock_github:
                connector = GitHubConnector(token="test-token-123")
                assert connector.enabled, "Connector should be enabled with token"
                mock_github.assert_called_once()
    
    def test_parse_repo_valid(self):
        """Test parsing valid repository identifier."""
        connector = GitHubConnector(token="test-token")
        owner, repo = connector._parse_repo("owner/repo")
        assert owner == "owner"
        assert repo == "repo"
    
    def test_parse_repo_invalid(self):
        """Test parsing invalid repository identifier."""
        connector = GitHubConnector(token="test-token")
        with pytest.raises(ValueError, match="Repository must be in format"):
            connector._parse_repo("invalid-repo")
    
    @patch("llmhive.app.services.github_connector.PYGITHUB_AVAILABLE", True)
    def test_get_file_success(self):
        """Test successful file retrieval."""
        connector = GitHubConnector(token="test-token")
        connector._github = Mock()
        
        # Mock repository and file content
        mock_repo = Mock()
        mock_file = Mock()
        mock_file.path = "app.py"
        mock_file.content = "print('Hello')"
        mock_file.encoding = "utf-8"
        mock_file.size = 20
        
        connector._github.get_repo.return_value = mock_repo
        mock_repo.get_contents.return_value = mock_file
        
        result = connector.get_file("owner/repo", "app.py")
        
        assert result is not None
        assert isinstance(result, GitHubFile)
        assert result.path == "app.py"
        assert result.content == "print('Hello')"
    
    @patch("llmhive.app.services.github_connector.PYGITHUB_AVAILABLE", True)
    def test_get_file_not_found(self):
        """Test file retrieval when file doesn't exist."""
        try:
            from github import GithubException
        except ImportError:
            pytest.skip("PyGithub not installed")
        
        connector = GitHubConnector(token="test-token")
        connector._github = Mock()
        
        # Mock GitHubException for 404
        connector._github.get_repo.side_effect = GithubException(
            status=404, data={"message": "Not Found"}, headers={}
        )
        
        result = connector.get_file("owner/repo", "nonexistent.py")
        assert result is None
    
    @patch("llmhive.app.services.github_connector.PYGITHUB_AVAILABLE", True)
    def test_list_issues_success(self):
        """Test successful issue listing."""
        connector = GitHubConnector(token="test-token")
        connector._github = Mock()
        
        # Mock repository and issues
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 1
        mock_issue.title = "Test Issue"
        mock_issue.body = "Issue description"
        mock_issue.state = "open"
        mock_issue.html_url = "https://github.com/owner/repo/issues/1"
        mock_issue.pull_request = None
        mock_issue.labels = []
        
        connector._github.get_repo.return_value = mock_repo
        mock_repo.get_issues.return_value = [mock_issue]
        
        issues = connector.list_issues("owner/repo", state="open", limit=10)
        
        assert len(issues) == 1
        assert issues[0].number == 1
        assert issues[0].title == "Test Issue"
        assert not issues[0].is_pull_request
    
    def test_get_file_disabled(self):
        """Test that get_file returns None when connector is disabled."""
        connector = GitHubConnector(token=None)
        result = connector.get_file("owner/repo", "file.py")
        assert result is None


class TestGCPConnector:
    """Tests for GCP connector."""
    
    def test_gcp_connector_disabled_no_project(self):
        """Test that connector is disabled when no project ID is provided."""
        connector = GCPConnector(project_id=None)
        assert not connector.enabled, "Connector should be disabled without project ID"
    
    @patch("llmhive.app.services.gcp_connector.GCP_AVAILABLE", True)
    @patch("llmhive.app.services.gcp_connector.bigquery")
    @patch("llmhive.app.services.gcp_connector.default")
    def test_query_bigquery_success(self, mock_default, mock_bigquery):
        """Test successful BigQuery query execution."""
        # Mock credentials
        mock_creds = Mock()
        mock_default.return_value = (mock_creds, "project-id")
        
        # Mock BigQuery client and query job
        mock_client = Mock()
        mock_bigquery.Client.return_value = mock_client
        
        mock_job = Mock()
        mock_job.result.return_value = None
        mock_job.schema = [
            Mock(name="column1", field_type="STRING"),
            Mock(name="column2", field_type="INTEGER"),
        ]
        mock_job.total_bytes_processed = 1000
        mock_job.job_id = "job-123"
        
        mock_row = Mock()
        mock_row.items.return_value = [("column1", "value1"), ("column2", 42)]
        mock_job.fetch.return_value = [mock_row]
        
        mock_client.query.return_value = mock_job
        
        connector = GCPConnector(project_id="test-project")
        result = connector.query_bigquery("SELECT * FROM table LIMIT 10")
        
        assert result is not None
        assert isinstance(result, BigQueryResult)
        assert len(result.rows) == 1
        assert result.rows[0]["column1"] == "value1"
        assert result.rows[0]["column2"] == 42
    
    @patch("llmhive.app.services.gcp_connector.GCP_AVAILABLE", True)
    @patch("llmhive.app.services.gcp_connector.cloud_logging")
    @patch("llmhive.app.services.gcp_connector.default")
    def test_get_logs_success(self, mock_default, mock_logging):
        """Test successful Cloud Logging retrieval."""
        # Mock credentials
        mock_creds = Mock()
        mock_default.return_value = (mock_creds, "project-id")
        
        # Mock logging client and entries
        mock_client = Mock()
        mock_logging.Client.return_value = mock_client
        
        mock_entry = Mock()
        mock_entry.timestamp = None
        mock_entry.severity = "ERROR"
        mock_entry.payload = "Error message"
        mock_entry.resource = {}
        mock_entry.labels = {}
        
        mock_client.list_entries.return_value = [mock_entry]
        
        connector = GCPConnector(project_id="test-project")
        logs = connector.get_logs("resource.type=cloud_run_revision", max_results=10)
        
        assert len(logs) == 1
        assert logs[0].severity == "ERROR"
        assert logs[0].message == "Error message"
    
    @patch("llmhive.app.services.gcp_connector.GCP_AVAILABLE", True)
    @patch("llmhive.app.services.gcp_connector.storage")
    @patch("llmhive.app.services.gcp_connector.default")
    def test_list_buckets_success(self, mock_default, mock_storage):
        """Test successful bucket listing."""
        # Mock credentials
        mock_creds = Mock()
        mock_default.return_value = (mock_creds, "project-id")
        
        # Mock storage client and buckets
        mock_client = Mock()
        mock_storage.Client.return_value = mock_client
        
        mock_bucket = Mock()
        mock_bucket.name = "test-bucket"
        mock_client.list_buckets.return_value = [mock_bucket]
        
        connector = GCPConnector(project_id="test-project")
        buckets = connector.list_buckets()
        
        assert len(buckets) == 1
        assert buckets[0] == "test-bucket"
    
    def test_query_bigquery_disabled(self):
        """Test that query_bigquery returns None when connector is disabled."""
        connector = GCPConnector(project_id=None)
        result = connector.query_bigquery("SELECT * FROM table")
        assert result is None


class TestOrchestratorIntegration:
    """Tests for orchestrator integration with DevOps connectors.
    
    Note: These tests are for planned features that are not yet implemented.
    They are skipped until the corresponding Orchestrator methods are added.
    """
    
    @pytest.mark.skip(reason="Orchestrator._detect_code_reference not yet implemented")
    @pytest.mark.asyncio
    async def test_detect_code_reference(self):
        """Test code reference detection in orchestrator."""
        from llmhive.app.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        
        # Test with file reference
        has_ref, repo, file_path = orchestrator._detect_code_reference("What is the bug in app.py?")
        assert has_ref is True
        assert file_path == "app.py"
        
        # Test with repo reference
        has_ref, repo, file_path = orchestrator._detect_code_reference("In owner/repo, what is the issue?")
        assert has_ref is False or repo == "owner/repo"
        
        # Test with no code reference
        has_ref, repo, file_path = orchestrator._detect_code_reference("What is the weather?")
        assert has_ref is False
    
    @pytest.mark.skip(reason="Orchestrator._detect_gcp_query not yet implemented")
    @pytest.mark.asyncio
    async def test_detect_gcp_query(self):
        """Test GCP query detection in orchestrator."""
        from llmhive.app.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        
        # Test BigQuery detection
        needs_gcp, query_type = orchestrator._detect_gcp_query("Run a BigQuery query")
        assert needs_gcp is True
        assert query_type == "bigquery"
        
        # Test logs detection
        needs_gcp, query_type = orchestrator._detect_gcp_query("Show me the errors in logs")
        assert needs_gcp is True
        assert query_type == "logs"
        
        # Test storage detection
        needs_gcp, query_type = orchestrator._detect_gcp_query("List my buckets")
        assert needs_gcp is True
        assert query_type == "storage"
        
        # Test no GCP query
        needs_gcp, query_type = orchestrator._detect_gcp_query("What is the weather?")
        assert needs_gcp is False
    
    @pytest.mark.skip(reason="Orchestrator.github_connector not yet implemented")
    @pytest.mark.asyncio
    async def test_fetch_github_context_disabled(self):
        """Test GitHub context fetching when connector is disabled."""
        from llmhive.app.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        if not orchestrator.github_connector or not orchestrator.github_connector.enabled:
            context = await orchestrator._fetch_github_context("What is in app.py?")
            assert len(context) == 1
            assert "not configured" in context[0].lower()
    
    @pytest.mark.skip(reason="Orchestrator.gcp_connector not yet implemented")
    @pytest.mark.asyncio
    async def test_fetch_gcp_context_disabled(self):
        """Test GCP context fetching when connector is disabled."""
        from llmhive.app.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        if not orchestrator.gcp_connector or not orchestrator.gcp_connector.enabled:
            context = await orchestrator._fetch_gcp_context("Show me the logs")
            assert len(context) == 1
            assert "not configured" in context[0].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

