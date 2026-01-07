#!/usr/bin/env python3
"""Create GitHub issue on benchmark regression.

This script analyzes benchmark results and creates/updates a GitHub issue
when regressions are detected. Can be run locally or in CI.

Usage:
    # With GitHub token (for private repos or to avoid rate limits)
    export GITHUB_TOKEN="ghp_..."
    python scripts/create_regression_issue.py

    # For public repos (limited)
    python scripts/create_regression_issue.py --repo owner/repo

    # Dry run (just print, don't create)
    python scripts/create_regression_issue.py --dry-run
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def find_latest_report(artifacts_dir: str = "artifacts/benchmarks") -> Optional[Path]:
    """Find the most recent benchmark report."""
    artifacts_path = Path(artifacts_dir)
    if not artifacts_path.exists():
        return None
    
    reports = list(artifacts_path.glob("*/report.json"))
    if not reports:
        return None
    
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0]


def load_report(report_path: Path) -> Dict[str, Any]:
    """Load a benchmark report from JSON."""
    with open(report_path, 'r') as f:
        return json.load(f)


def format_issue_body(report: Dict[str, Any]) -> str:
    """Format the issue body from benchmark report."""
    critical_failures = report.get("critical_failures", [])
    aggregate = report.get("aggregate", {})
    systems = aggregate.get("systems", {})
    
    body = f"""## 🚨 Benchmark Regression Detected

**Run Date**: {datetime.now().isoformat()}
**Git Commit**: `{report.get('git_commit', 'unknown')}`
**Suite**: {report.get('suite_name', 'unknown')} v{report.get('suite_version', '?')}

### Critical Failures ({len(critical_failures)})

"""
    
    if critical_failures:
        for fail_id in critical_failures:
            body += f"- `{fail_id}`\n"
    else:
        body += "_None_\n"
    
    body += """
### System Scores

| System | Mean Score | Passed | Failed | Critical |
|--------|------------|--------|--------|----------|
"""
    
    for name, stats in systems.items():
        mean = stats.get("composite_mean", 0)
        passed = stats.get("passed_count", 0)
        failed = stats.get("failed_count", 0)
        critical = stats.get("critical_failures", 0)
        body += f"| {name} | {mean:.3f} | {passed} | {failed} | {critical} |\n"
    
    body += """
### Failure Details

"""
    
    # Add details for each failed prompt
    scores = report.get("scores", [])
    failed_scores = [s for s in scores if s.get("objective_score", {}).get("passed") == False]
    
    for score in failed_scores[:10]:  # Limit to 10 for readability
        prompt_id = score.get("prompt_id", "unknown")
        system = score.get("system_name", "unknown")
        composite = score.get("composite_score", 0)
        details = score.get("objective_score", {}).get("details", {})
        
        body += f"<details>\n<summary><code>{prompt_id}</code> ({system}): {composite:.3f}</summary>\n\n"
        body += f"**Checks**:\n"
        for check_name, check_result in score.get("objective_score", {}).get("checks", {}).items():
            status = "✓" if check_result else "✗"
            body += f"- {status} {check_name}\n"
        body += f"\n**Details**: {json.dumps(details, indent=2)}\n"
        body += "</details>\n\n"
    
    if len(failed_scores) > 10:
        body += f"_...and {len(failed_scores) - 10} more failures_\n"
    
    body += """
### Next Steps

1. Review the failed prompts in the benchmark artifacts
2. Identify root causes (factual error, tool failure, reasoning gap)
3. Implement fixes and re-run benchmarks
4. Close this issue when all critical failures are resolved

---
_This issue was automatically created by `scripts/create_regression_issue.py`_
"""
    
    return body


def create_github_issue(
    owner: str,
    repo: str,
    title: str,
    body: str,
    labels: List[str],
    token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create a GitHub issue via API."""
    if not HAS_HTTPX:
        print("Error: httpx not installed. Run: pip install httpx")
        return None
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    # Check for existing open issue with same label
    search_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"labels": ",".join(labels), "state": "open"}
    
    try:
        response = httpx.get(search_url, headers=headers, params=params, timeout=10)
        existing = response.json() if response.status_code == 200 else []
        
        if existing:
            # Update existing issue with comment
            issue_number = existing[0]["number"]
            comment_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
            
            comment_body = f"## New Benchmark Run\n\n{body}"
            response = httpx.post(
                comment_url,
                headers=headers,
                json={"body": comment_body},
                timeout=10,
            )
            
            if response.status_code == 201:
                print(f"✓ Updated existing issue #{issue_number}")
                return response.json()
            else:
                print(f"✗ Failed to update issue: {response.status_code}")
                print(response.text)
                return None
        
        else:
            # Create new issue
            create_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            response = httpx.post(
                create_url,
                headers=headers,
                json={
                    "title": title,
                    "body": body,
                    "labels": labels,
                },
                timeout=10,
            )
            
            if response.status_code == 201:
                issue = response.json()
                print(f"✓ Created issue #{issue['number']}: {issue['html_url']}")
                return issue
            else:
                print(f"✗ Failed to create issue: {response.status_code}")
                print(response.text)
                return None
    
    except Exception as e:
        print(f"✗ Error communicating with GitHub: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Create GitHub issue on benchmark regression")
    parser.add_argument("--report", help="Path to report.json (default: latest)")
    parser.add_argument("--repo", help="GitHub repo in owner/repo format")
    parser.add_argument("--dry-run", action="store_true", help="Print issue but don't create")
    parser.add_argument("--force", action="store_true", help="Create issue even if benchmarks passed")
    args = parser.parse_args()
    
    # Find report
    if args.report:
        report_path = Path(args.report)
    else:
        report_path = find_latest_report()
    
    if not report_path or not report_path.exists():
        print("❌ No benchmark report found. Run a benchmark first.")
        sys.exit(1)
    
    print(f"Loading report: {report_path}")
    report = load_report(report_path)
    
    # Check if we should create an issue
    passed = report.get("passed", True)
    critical_failures = report.get("critical_failures", [])
    
    if passed and not args.force:
        print("✅ Benchmarks passed, no issue needed.")
        sys.exit(0)
    
    # Format issue
    title = f"🚨 Benchmark Regression: {len(critical_failures)} critical failure(s)"
    body = format_issue_body(report)
    labels = ["benchmark-regression", "automated"]
    
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - Would create issue:")
        print("=" * 60)
        print(f"Title: {title}")
        print(f"Labels: {labels}")
        print("Body:")
        print(body)
        sys.exit(0)
    
    # Determine repo
    if args.repo:
        owner, repo_name = args.repo.split("/")
    else:
        # Try to detect from git
        import subprocess
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
            )
            url = result.stdout.strip()
            
            # Parse owner/repo from URL
            if "github.com" in url:
                if url.startswith("git@"):
                    # git@github.com:owner/repo.git
                    parts = url.split(":")[-1].replace(".git", "").split("/")
                else:
                    # https://github.com/owner/repo.git
                    parts = url.replace("https://github.com/", "").replace(".git", "").split("/")
                owner, repo_name = parts[0], parts[1]
            else:
                print("❌ Could not detect GitHub repo. Use --repo owner/repo")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Could not detect GitHub repo: {e}")
            sys.exit(1)
    
    print(f"Creating issue for {owner}/{repo_name}")
    
    # Get token
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("⚠️  No GITHUB_TOKEN found. Issue creation may fail for private repos.")
    
    # Create issue
    result = create_github_issue(owner, repo_name, title, body, labels, token)
    
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()

