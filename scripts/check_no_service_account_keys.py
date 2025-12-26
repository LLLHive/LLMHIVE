#!/usr/bin/env python3
"""
LLMHive Secret Scanner

Scans tracked files for accidentally committed secrets such as:
- Service account private keys
- GCP service account JSON files
- API keys and tokens

This script is designed to be run in CI to prevent secrets from being committed.

Usage:
    python scripts/check_no_service_account_keys.py
    python scripts/check_no_service_account_keys.py --verbose
    python scripts/check_no_service_account_keys.py --include-untracked

Exit codes:
    0 - No secrets found
    1 - Secrets detected (fail CI)
    2 - Script error
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# =============================================================================
# Configuration
# =============================================================================

# Patterns that indicate a secret/credential
SECRET_PATTERNS = [
    # Private keys (PEM format)
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private key detected"),
    (r"-----BEGIN ENCRYPTED PRIVATE KEY-----", "Encrypted private key detected"),
    
    # GCP Service Account indicators
    (r'"type"\s*:\s*"service_account"', "GCP service account JSON detected"),
    (r'"private_key_id"\s*:\s*"[a-f0-9]{40}"', "GCP private_key_id detected"),
    (r'"private_key"\s*:\s*"-----BEGIN', "GCP private_key field detected"),
    (r'"client_email"\s*:\s*"[^"]+@[^"]+\.iam\.gserviceaccount\.com"', "GCP service account email detected"),
    
    # AWS Credentials
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID detected"),
    (r'"aws_secret_access_key"\s*:', "AWS secret access key field detected"),
    
    # Generic API keys (with context to reduce false positives)
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API key pattern detected"),
    (r"sk-ant-[a-zA-Z0-9-]{90,}", "Anthropic API key pattern detected"),
    
    # Firebase/Google credentials
    (r'"project_id"\s*:\s*"[^"]+"\s*,\s*"private_key_id"', "Firebase/GCP credentials detected"),
]

# Files/patterns to skip (never scan these)
SKIP_PATTERNS = [
    r"node_modules/",
    r"\.venv/",
    r"venv/",
    r"\.git/",
    r"__pycache__/",
    r"\.pytest_cache/",
    r"\.next/",
    r"dist/",
    r"build/",
    r"\.cache/",
    r"coverage/",
    # Example/template files that may contain placeholders
    r"\.example$",
    r"\.template$",
    r"\.sample$",
]

# Files that are allowed to contain certain patterns (documentation, examples)
ALLOWED_FILES = [
    "scripts/check_no_service_account_keys.py",  # This file contains patterns for detection
    ".cursor/rules/pinecone.mdc",  # Documentation may contain example patterns
    "README.md",
    "CONTRIBUTING.md",
    ".env.example",
    "data/modeldb/.env.example",
]

# File extensions to scan (binary files are skipped)
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml",
    ".env", ".sh", ".bash", ".zsh", ".md", ".txt", ".toml", ".cfg",
    ".ini", ".conf", ".xml", ".html", ".css", ".sql", ".graphql",
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_repo_root() -> Path:
    """Get the repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Fallback to script location
        return Path(__file__).parent.parent


def get_tracked_files(include_untracked: bool = False) -> List[str]:
    """Get list of files tracked by git (or all files if include_untracked)."""
    try:
        if include_untracked:
            # Get all files except gitignored
            result = subprocess.run(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            # Only tracked files
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                check=True,
            )
        return [f for f in result.stdout.strip().split("\n") if f]
    except subprocess.CalledProcessError as e:
        print(f"Error getting tracked files: {e}", file=sys.stderr)
        return []


def should_skip_file(file_path: str) -> bool:
    """Check if a file should be skipped based on patterns."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, file_path):
            return True
    
    # Skip binary files by extension
    ext = Path(file_path).suffix.lower()
    if ext and ext not in SCANNABLE_EXTENSIONS:
        # Check if it's a known binary extension
        binary_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
            ".pdf", ".zip", ".tar", ".gz", ".bz2",
            ".exe", ".dll", ".so", ".dylib",
            ".woff", ".woff2", ".ttf", ".eot",
            ".mp3", ".mp4", ".wav", ".avi",
            ".xlsx", ".xls", ".doc", ".docx",
            ".parquet", ".pickle", ".pkl",
        }
        if ext in binary_extensions:
            return True
    
    return False


def is_allowed_file(file_path: str) -> bool:
    """Check if a file is in the allowed list."""
    for allowed in ALLOWED_FILES:
        if file_path.endswith(allowed) or file_path == allowed:
            return True
    return False


def scan_file(file_path: Path, verbose: bool = False) -> List[Tuple[int, str, str]]:
    """
    Scan a file for secret patterns.
    
    Returns list of (line_number, matched_text_snippet, reason).
    """
    findings = []
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception as e:
        if verbose:
            print(f"  Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return findings
    
    for pattern, reason in SECRET_PATTERNS:
        for line_num, line in enumerate(lines, start=1):
            if re.search(pattern, line, re.IGNORECASE):
                # Truncate the matched line for display
                snippet = line.strip()[:80]
                if len(line.strip()) > 80:
                    snippet += "..."
                findings.append((line_num, snippet, reason))
    
    return findings


# =============================================================================
# Main Scanner
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan repository for accidentally committed secrets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Also scan untracked files (not just git-tracked)",
    )
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Always exit 0 (for testing, not CI)",
    )
    
    args = parser.parse_args()
    
    repo_root = get_repo_root()
    os.chdir(repo_root)
    
    print("=" * 70)
    print("LLMHive Secret Scanner")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print(f"Include untracked: {args.include_untracked}")
    print("")
    
    # Get files to scan
    files = get_tracked_files(include_untracked=args.include_untracked)
    
    if not files:
        print("No files to scan.")
        return 0
    
    print(f"Scanning {len(files)} files...")
    if args.verbose:
        print("")
    
    # Scan files
    all_findings: Dict[str, List[Tuple[int, str, str]]] = {}
    scanned_count = 0
    skipped_count = 0
    
    for file_path in files:
        if should_skip_file(file_path):
            skipped_count += 1
            continue
        
        if is_allowed_file(file_path):
            if args.verbose:
                print(f"  Allowed (skip): {file_path}")
            continue
        
        full_path = repo_root / file_path
        if not full_path.exists() or not full_path.is_file():
            continue
        
        scanned_count += 1
        
        if args.verbose:
            print(f"  Scanning: {file_path}")
        
        findings = scan_file(full_path, verbose=args.verbose)
        
        if findings:
            all_findings[file_path] = findings
    
    print("")
    print(f"Scanned: {scanned_count} files")
    print(f"Skipped: {skipped_count} files (binary/excluded)")
    print("")
    
    # Report findings
    if all_findings:
        print("=" * 70)
        print("❌ SECRETS DETECTED!")
        print("=" * 70)
        print("")
        
        for file_path, findings in sorted(all_findings.items()):
            print(f"📄 {file_path}")
            for line_num, snippet, reason in findings:
                print(f"   Line {line_num}: {reason}")
                print(f"   > {snippet}")
            print("")
        
        print("=" * 70)
        print(f"Found {sum(len(f) for f in all_findings.values())} potential secret(s) in {len(all_findings)} file(s)")
        print("")
        print("Actions required:")
        print("  1. Remove the secret from the file")
        print("  2. Rotate/revoke the compromised credential")
        print("  3. If this is a false positive, add the file to ALLOWED_FILES in this script")
        print("")
        print("To prevent this in the future:")
        print("  - Use .env files for secrets (they are gitignored)")
        print("  - Never commit service account JSON files")
        print("  - Use git-secrets or pre-commit hooks")
        print("=" * 70)
        
        return 0 if args.exit_zero else 1
    
    print("=" * 70)
    print("✅ No secrets detected!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

