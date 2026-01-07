#!/usr/bin/env python3
"""Script to run LLMHive benchmarks.

This script provides a convenient entry point for running benchmarks
without needing to invoke the module directly.

Usage:
    python scripts/run_benchmarks.py --systems llmhive --mode local
    python scripts/run_benchmarks.py --systems llmhive,openai,anthropic
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "llmhive" / "src"))


def load_env_files():
    """Load environment variables from .env files."""
    env_files = [
        project_root / ".env.local",
        project_root / ".env",
        project_root / "llmhive" / ".env",
    ]
    
    loaded = False
    for env_file in env_files:
        if env_file.exists():
            print(f"Loading environment from: {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse KEY=value
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
            loaded = True
    
    # Check key API keys
    keys_status = []
    if os.environ.get("OPENROUTER_API_KEY"):
        keys_status.append("✅ OPENROUTER_API_KEY")
    if os.environ.get("OPENAI_API_KEY"):
        keys_status.append("✅ OPENAI_API_KEY")
    if os.environ.get("ANTHROPIC_API_KEY"):
        keys_status.append("✅ ANTHROPIC_API_KEY")
    
    if keys_status:
        print(f"API keys loaded: {', '.join(keys_status)}")
    elif loaded:
        print("⚠️  No API keys found in environment files")
    
    return loaded


# Load env files before importing LLMHive modules
load_env_files()

# Import and run the CLI
from llmhive.app.benchmarks.cli import main

if __name__ == "__main__":
    main()

