"""GitHub integration connector for DevOps tool integration.

This module provides read-only access to GitHub repositories, allowing the orchestrator
to fetch code files, issues, and pull requests for context-aware responses.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import PyGithub, fall back to REST API if not available
try:
    from github import Github, GithubException
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False
    Github = None  # type: ignore
    GithubException = None  # type: ignore
    logger.debug("PyGithub not available, will use REST API fallback")

# Fallback to REST API if PyGithub is not available
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None  # type: ignore
    logger.warning("httpx not available, GitHub connector will not work")


@dataclass(slots=True)
class GitHubFile:
    """Represents a file from a GitHub repository."""

    path: str
    content: str
    size: int
    encoding: str = "utf-8"


@dataclass(slots=True)
class GitHubIssue:
    """Represents a GitHub issue or pull request."""

    number: int
    title: str
    body: str
    state: str  # "open", "closed"
    url: str
    is_pull_request: bool = False
    labels: List[str] = None  # type: ignore


class GitHubConnector:
    """Connector for interacting with GitHub repositories.
    
    Provides read-only operations to fetch repository data including:
    - File contents
    - Open issues and pull requests
    - Repository metadata
    
    Authentication is done via GitHub personal access token.
    """

    def __init__(self, token: str | None = None, *, timeout: float = 10.0) -> None:
        """Initialize GitHub connector.
        
        Args:
            token: GitHub personal access token. If None, loads from GITHUB_TOKEN env var.
            timeout: Request timeout in seconds.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.timeout = timeout
        self._github = None
        self._enabled = bool(self.token)
        
        if not self._enabled:
            logger.debug("GitHub connector disabled: GITHUB_TOKEN not configured")
            return
        
        # Initialize PyGithub if available
        if PYGITHUB_AVAILABLE and self.token:
            try:
                self._github = Github(self.token, timeout=int(timeout))
                logger.info("GitHub connector initialized with PyGithub")
            except Exception as exc:
                logger.warning("Failed to initialize PyGithub: %s", exc)
                self._github = None
        
        if not self._github and not HTTPX_AVAILABLE:
            logger.warning("GitHub connector requires either PyGithub or httpx")
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if GitHub connector is enabled and configured."""
        return self._enabled

    def _parse_repo(self, repo: str) -> tuple[str, str]:
        """Parse repository identifier into owner and repo name.
        
        Args:
            repo: Repository identifier in format "owner/repo" or just "repo" (uses default owner)
            
        Returns:
            Tuple of (owner, repo_name)
            
        Raises:
            ValueError: If repo format is invalid
        """
        if "/" in repo:
            parts = repo.split("/", 1)
            return parts[0].strip(), parts[1].strip()
        else:
            # Default to using repo name as both owner and repo (may need config)
            # For now, raise error to be explicit
            raise ValueError(
                f"Repository must be in format 'owner/repo', got: {repo}. "
                "Example: 'octocat/Hello-World'"
            )

    def get_file(
        self, repo: str, path: str, ref: str = "main"
    ) -> Optional[GitHubFile]:
        """Fetch the contents of a file from a GitHub repository.
        
        Args:
            repo: Repository identifier in format "owner/repo"
            path: File path within the repository
            ref: Git reference (branch, tag, or commit SHA). Defaults to "main".
            
        Returns:
            GitHubFile object with file contents, or None if file not found or error.
        """
        if not self.enabled:
            logger.debug("GitHub connector disabled, cannot fetch file")
            return None
        
        try:
            owner, repo_name = self._parse_repo(repo)
            
            # Use PyGithub if available
            if self._github:
                try:
                    repository = self._github.get_repo(f"{owner}/{repo_name}")
                    file_content = repository.get_contents(path, ref=ref)
                    
                    # Handle file content (may be base64 encoded)
                    content = file_content.content
                    if file_content.encoding == "base64":
                        import base64
                        content = base64.b64decode(content).decode("utf-8")
                    else:
                        content = content.decode("utf-8") if isinstance(content, bytes) else content
                    
                    return GitHubFile(
                        path=file_content.path,
                        content=content,
                        size=file_content.size,
                        encoding=file_content.encoding or "utf-8",
                    )
                except GithubException as exc:
                    if exc.status == 404:
                        logger.debug("File not found: %s/%s/%s", repo, path, ref)
                        return None
                    logger.warning("GitHub API error fetching file: %s", exc)
                    return None
            
            # Fallback to REST API
            elif HTTPX_AVAILABLE:
                url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                params = {"ref": ref} if ref else {}
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                async def _fetch():
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(url, headers=headers, params=params)
                        if response.status_code == 404:
                            logger.debug("File not found: %s/%s/%s", repo, path, ref)
                            return None
                        response.raise_for_status()
                        data = response.json()
                        
                        # Decode base64 content
                        import base64
                        content = base64.b64decode(data["content"]).decode("utf-8")
                        
                        return GitHubFile(
                            path=data["path"],
                            content=content,
                            size=data["size"],
                            encoding=data.get("encoding", "utf-8"),
                        )
                
                return loop.run_until_complete(_fetch())
            
        except ValueError as exc:
            logger.warning("Invalid repository format: %s", exc)
            return None
        except Exception as exc:
            logger.error("Error fetching file from GitHub: %s", exc, exc_info=True)
            return None
        
        return None

    def list_issues(
        self, repo: str, state: str = "open", limit: int = 10
    ) -> List[GitHubIssue]:
        """List issues (and optionally PRs) from a GitHub repository.
        
        Args:
            repo: Repository identifier in format "owner/repo"
            state: Issue state ("open", "closed", or "all"). Defaults to "open".
            limit: Maximum number of issues to return. Defaults to 10.
            
        Returns:
            List of GitHubIssue objects, or empty list if error.
        """
        if not self.enabled:
            logger.debug("GitHub connector disabled, cannot list issues")
            return []
        
        try:
            owner, repo_name = self._parse_repo(repo)
            issues: List[GitHubIssue] = []
            
            # Use PyGithub if available
            if self._github:
                try:
                    repository = self._github.get_repo(f"{owner}/{repo_name}")
                    github_issues = repository.get_issues(state=state)[:limit]
                    
                    for issue in github_issues:
                        labels = [label.name for label in issue.labels]
                        issues.append(
                            GitHubIssue(
                                number=issue.number,
                                title=issue.title,
                                body=issue.body or "",
                                state=issue.state,
                                url=issue.html_url,
                                is_pull_request=bool(issue.pull_request),
                                labels=labels,
                            )
                        )
                    
                    return issues
                except GithubException as exc:
                    logger.warning("GitHub API error listing issues: %s", exc)
                    return []
            
            # Fallback to REST API
            elif HTTPX_AVAILABLE:
                url = f"https://api.github.com/repos/{owner}/{repo_name}/issues"
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                params = {"state": state, "per_page": min(limit, 100)}
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                async def _fetch():
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(url, headers=headers, params=params)
                        response.raise_for_status()
                        data = response.json()
                        
                        for item in data[:limit]:
                            issues.append(
                                GitHubIssue(
                                    number=item["number"],
                                    title=item["title"],
                                    body=item.get("body", "") or "",
                                    state=item["state"],
                                    url=item["html_url"],
                                    is_pull_request="pull_request" in item,
                                    labels=[label["name"] for label in item.get("labels", [])],
                                )
                            )
                        return issues
                
                return loop.run_until_complete(_fetch())
            
        except ValueError as exc:
            logger.warning("Invalid repository format: %s", exc)
            return []
        except Exception as exc:
            logger.error("Error listing issues from GitHub: %s", exc, exc_info=True)
            return []
        
        return []

    def list_pull_requests(
        self, repo: str, state: str = "open", limit: int = 10
    ) -> List[GitHubIssue]:
        """List pull requests from a GitHub repository.
        
        Args:
            repo: Repository identifier in format "owner/repo"
            state: PR state ("open", "closed", or "all"). Defaults to "open".
            limit: Maximum number of PRs to return. Defaults to 10.
            
        Returns:
            List of GitHubIssue objects (with is_pull_request=True), or empty list if error.
        """
        if not self.enabled:
            logger.debug("GitHub connector disabled, cannot list PRs")
            return []
        
        try:
            owner, repo_name = self._parse_repo(repo)
            prs: List[GitHubIssue] = []
            
            # Use PyGithub if available
            if self._github:
                try:
                    repository = self._github.get_repo(f"{owner}/{repo_name}")
                    github_prs = repository.get_pulls(state=state)[:limit]
                    
                    for pr in github_prs:
                        labels = [label.name for label in pr.labels]
                        prs.append(
                            GitHubIssue(
                                number=pr.number,
                                title=pr.title,
                                body=pr.body or "",
                                state=pr.state,
                                url=pr.html_url,
                                is_pull_request=True,
                                labels=labels,
                            )
                        )
                    
                    return prs
                except GithubException as exc:
                    logger.warning("GitHub API error listing PRs: %s", exc)
                    return []
            
            # Fallback to REST API
            elif HTTPX_AVAILABLE:
                url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                params = {"state": state, "per_page": min(limit, 100)}
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                async def _fetch():
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(url, headers=headers, params=params)
                        response.raise_for_status()
                        data = response.json()
                        
                        for item in data[:limit]:
                            prs.append(
                                GitHubIssue(
                                    number=item["number"],
                                    title=item["title"],
                                    body=item.get("body", "") or "",
                                    state=item["state"],
                                    url=item["html_url"],
                                    is_pull_request=True,
                                    labels=[label["name"] for label in item.get("labels", [])],
                                )
                            )
                        return prs
                
                return loop.run_until_complete(_fetch())
            
        except ValueError as exc:
            logger.warning("Invalid repository format: %s", exc)
            return []
        except Exception as exc:
            logger.error("Error listing PRs from GitHub: %s", exc, exc_info=True)
            return []
        
        return []

